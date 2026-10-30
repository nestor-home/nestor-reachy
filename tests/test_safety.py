"""On-device safety: limits on every target, the watchdog, and a lost robot."""

import asyncio

from nestor_satellite import Behavior, Expression

from nestor_reachy import REST, Animator, Limits, Pose, SafeRobot
from nestor_reachy.pose import IDENTIFY_S

from .doubles import Clock, RecordingRobot


async def test_every_target_is_clamped_whatever_computed_it() -> None:
    motors = RecordingRobot()
    robot = SafeRobot(motors, Limits(angle_deg=5, z_mm=2, antenna_rad=0.3))
    await robot.set_target(Pose(roll=40, z=-9, antennas=(1.0, -1.0)))
    await robot.close()
    assert motors.targets == [Pose(roll=5, z=-2, antennas=(0.3, -0.3))] and motors.closed


def linked(clock: Clock) -> Animator:
    animator = Animator(RecordingRobot(), clock=clock)
    animator.connected(True)
    animator.behavior(Behavior.SPEAKING)
    return animator


def test_without_a_link_the_robot_stays_at_rest() -> None:
    animator = Animator(RecordingRobot(), clock=Clock())
    animator.behavior(Behavior.SPEAKING)
    assert animator.resting and animator.target() == REST


def test_a_silent_core_puts_the_robot_back_to_rest_after_two_seconds() -> None:
    clock = Clock()
    animator = linked(clock)
    animator.expression(Expression.EXCITED, 1.0)
    clock.now += 1.9
    assert animator.target() != REST, "still within the watchdog's patience"
    clock.now += 0.2
    assert animator.target() == REST
    clock.now += 1.0
    animator.heartbeat()
    assert animator.target() == pose_now(clock), "back to the idle breathing, the gesture forgotten"


def pose_now(clock: Clock) -> Pose:
    from nestor_reachy import pose

    return pose(Behavior.IDLE, clock.now)


def test_a_dropped_link_rests_the_robot_at_once() -> None:
    clock = Clock()
    animator = linked(clock)
    animator.heartbeat()
    animator.connected(False)
    assert animator.target() == REST


def test_heartbeats_keep_the_gesture_going() -> None:
    clock = Clock()
    animator = linked(clock)
    for _ in range(10):
        clock.now += 0.5
        animator.heartbeat()
    animator.beat()
    clock.now += 0.1
    animator.heartbeat()
    from nestor_reachy import pose

    assert animator.target().pitch > pose(Behavior.SPEAKING, clock.now).pitch + 3, "nodding, five seconds on"


async def test_the_robot_is_animated_at_30_hz_and_rests_on_close() -> None:
    robot = RecordingRobot()
    animator = Animator(robot)
    animator.connected(True)
    animator.behavior(Behavior.SPEAKING)
    await animator.start()
    await asyncio.sleep(0.2)
    animator.expression(Expression.JOY, 1.0)
    await asyncio.sleep(0.6)
    await animator.close()

    assert len(robot.targets) > 15, "no stream of poses at about 30 Hz"
    assert max(p.antennas[1] - p.antennas[0] for p in robot.targets) > 1.0, "the laugh did not move the antennas"
    assert robot.targets[-1] == REST and robot.closed


async def test_losing_the_robot_does_not_break_anything() -> None:
    robot = RecordingRobot(fail=True)
    animator = Animator(robot)
    await animator.start()
    await asyncio.sleep(0.05)
    animator.behavior(Behavior.SPEAKING)
    animator.beat()
    await animator.close()
    assert animator.lost and robot.closed and not robot.targets


async def test_an_animator_closed_before_starting_still_rests_the_robot() -> None:
    robot = RecordingRobot()
    await Animator(robot).close()
    assert robot.targets == [REST] and robot.closed


def test_asked_to_identify_while_waiting_to_pair_it_wiggles_its_antennas_head_at_rest() -> None:
    clock = Clock()
    animator = Animator(RecordingRobot(), clock=clock)
    animator.identify()
    poses = []
    for _ in range(20):
        clock.now += IDENTIFY_S / 20 * 0.9
        poses.append(animator.target())
    assert animator.resting, "no link yet: the watchdog keeps the head at rest"
    assert all((p.roll, p.pitch, p.yaw, p.z) == (0, 0, 0, 0) for p in poses)
    assert max(abs(p.antennas[1] - REST.antennas[1]) for p in poses) > 0.4
    clock.now += IDENTIFY_S
    assert animator.target() == REST, "then still again"
