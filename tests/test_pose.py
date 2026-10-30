from nestor_satellite import Behavior, Expression

from nestor_reachy import LIMITS, REST, Limits, Pose, pose
from nestor_reachy.pose import BEAT_S, EXPRESSION_S, IDENTIFY_S, identify


def spread(p: Pose) -> float:
    return p.antennas[1] - p.antennas[0]


def test_idle_is_calm_and_speaking_nods_on_each_word() -> None:
    idle = [pose(Behavior.IDLE, t / 10) for t in range(100)]
    assert max(abs(p.pitch) + abs(p.roll) for p in idle) < 1

    calm = pose(Behavior.SPEAKING, 1.0)
    nod = pose(Behavior.SPEAKING, 1.0, beat_age=BEAT_S / 2)
    assert nod.pitch - calm.pitch > 3
    assert pose(Behavior.SPEAKING, 1.0, beat_age=BEAT_S * 2) == calm


def test_listening_leans_in_and_thinking_looks_away() -> None:
    listening, thinking = pose(Behavior.LISTENING, 1.0), pose(Behavior.THINKING, 1.0)
    assert listening.pitch < 0 and spread(listening) > spread(pose(Behavior.IDLE, 1.0))
    assert thinking.roll > 5


def test_a_laugh_lifts_the_antennas_then_fades_back() -> None:
    base = pose(Behavior.SPEAKING, 2.0)
    laughing = pose(Behavior.SPEAKING, 2.0, expression=Expression.JOY, expression_age=EXPRESSION_S / 2)
    done = pose(Behavior.SPEAKING, 2.0, expression=Expression.JOY, expression_age=EXPRESSION_S + 0.1)
    assert spread(laughing) > spread(base) + 0.6
    assert done == base


def test_each_expression_has_its_own_gesture() -> None:
    gestures = {pose(Behavior.IDLE, 0.0, expression=e, expression_age=EXPRESSION_S / 2) for e in Expression}
    assert len(gestures) == len(Expression)


def test_no_combination_leaves_the_motion_limits() -> None:
    for behavior in Behavior:
        for expression in [None, *Expression]:
            for i in range(40):
                p = pose(behavior, i * 0.37, expression=expression, expression_age=i * 0.04, beat_age=(i % 10) * 0.03)
                assert max(abs(p.roll), abs(p.pitch), abs(p.yaw)) <= LIMITS.angle_deg
                assert abs(p.z) <= LIMITS.z_mm and all(abs(a) <= LIMITS.antenna_rad for a in p.antennas)


def test_clamping_holds_any_pose_within_limits_and_drops_nonsense() -> None:
    wild = Pose(roll=90, pitch=-90, yaw=float("nan"), z=50, antennas=(-3.0, float("inf")))
    assert wild.clamped(Limits(angle_deg=10, z_mm=5, antenna_rad=0.5)) == Pose(10, -10, 0.0, 5, (-0.5, 0.0))


def test_identifying_wiggles_only_the_antennas_widely_then_stops() -> None:
    base = pose(Behavior.LISTENING, 1.0)
    wiggle = [identify(base, i * IDENTIFY_S / 40) for i in range(40)]
    assert all((p.roll, p.pitch, p.yaw, p.z) == (base.roll, base.pitch, base.yaw, base.z) for p in wiggle), "head still"
    assert max(spread(p) for p in wiggle) - min(spread(p) for p in wiggle) > 1.5, "visible from across the room"
    assert identify(base, IDENTIFY_S) == base and identify(base, -0.1) == base


def test_identifying_never_leaves_the_motion_limits() -> None:
    for start in (REST, *(pose(b, 0.3, expression=e, expression_age=0.5) for b in Behavior for e in Expression)):
        for i in range(60):
            assert all(abs(a) <= LIMITS.antenna_rad for a in identify(start, i * 0.033).antennas)
