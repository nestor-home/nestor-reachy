"""Reachy Mini's body language: where the head and antennas are at time `t`, as a pure function.

Each attitude has its own motion (breathing at rest, leaning in to listen, a wandering gaze while
thinking, a sway while speaking); a speech beat is a short nod; an expression rises then fades back
over `EXPRESSION_S`; identifying itself, it wiggles its antennas for `IDENTIFY_S`. Every pose is
clamped to `LIMITS`.
"""

import math
from dataclasses import dataclass

from nestor_satellite import Behavior, Expression

RATE_HZ = 30
EXPRESSION_S = 1.6  # how long an expression lasts before the attitude takes over again
BEAT_S = 0.25  # how long a speech accent lasts
IDENTIFY_S = 2.0  # how long it wiggles its antennas when asked to make itself noticed
REST_ANTENNAS = (-0.17, 0.17)  # rad, [right, left]


@dataclass(frozen=True, slots=True)
class Limits:
    """The widest target ever sent to the motors."""

    angle_deg: float = 20.0  # roll, pitch, yaw
    z_mm: float = 10.0
    antenna_rad: float = 1.0


LIMITS = Limits()


@dataclass(frozen=True, slots=True)
class Pose:
    roll: float = 0.0  # degrees
    pitch: float = 0.0  # degrees, positive: head down
    yaw: float = 0.0  # degrees
    z: float = 0.0  # mm
    antennas: tuple[float, float] = REST_ANTENNAS  # rad

    def clamped(self, limits: Limits = LIMITS) -> "Pose":
        def clamp(value: float, limit: float) -> float:
            return max(-limit, min(limit, value)) if math.isfinite(value) else 0.0

        angle, z, antenna = limits.angle_deg, limits.z_mm, limits.antenna_rad
        return Pose(
            clamp(self.roll, angle),
            clamp(self.pitch, angle),
            clamp(self.yaw, angle),
            clamp(self.z, z),
            (clamp(self.antennas[0], antenna), clamp(self.antennas[1], antenna)),
        )


REST = Pose()


def pose(
    behavior: Behavior,
    t: float,
    *,
    expression: Expression | None = None,
    expression_age: float = 0.0,
    beat_age: float | None = None,
) -> Pose:
    breath = math.sin(2 * math.pi * 0.25 * t)
    if behavior is Behavior.LISTENING:
        current = Pose(roll=4, pitch=-5, z=2 + breath, antennas=(-0.4, 0.4))
    elif behavior is Behavior.THINKING:
        current = Pose(roll=8, pitch=-3, yaw=6 * math.sin(2 * math.pi * 0.3 * t), antennas=(-0.6, 0.1))
    elif behavior is Behavior.SPEAKING:
        sway = math.sin(2 * math.pi * 0.6 * t)
        current = Pose(roll=2 * sway, yaw=3 * sway, z=1, antennas=(-0.25 - 0.08 * sway, 0.25 - 0.08 * sway))
    else:
        current = Pose(z=1.5 * breath, antennas=(REST_ANTENNAS[0] + 0.03 * breath, REST_ANTENNAS[1] - 0.03 * breath))

    if beat_age is not None and beat_age < BEAT_S:
        nod = math.sin(math.pi * beat_age / BEAT_S)
        current = Pose(current.roll, current.pitch + 4 * nod, current.yaw, current.z, current.antennas)

    if expression is not None and expression_age < EXPRESSION_S:
        weight = math.sin(math.pi * expression_age / EXPRESSION_S)  # rises, then fades back
        current = _blend(current, _expression(expression, expression_age), weight)
    return current.clamped()


def identify(current: Pose, age: float) -> Pose:
    """The antennas wiggling fast and wide over `current` for `IDENTIFY_S`, then `current` again. Only
    the antennas move: it is safe even while the head rests, and readable from across the room."""
    if not 0 <= age < IDENTIFY_S:
        return current
    swing = 0.6 * math.sin(2 * math.pi * 3 * age)
    antennas = (current.antennas[0] - swing, current.antennas[1] + swing)
    return Pose(current.roll, current.pitch, current.yaw, current.z, antennas).clamped()


def _expression(expression: Expression, age: float) -> Pose:
    fast = math.sin(2 * math.pi * 6 * age)
    match expression:
        case Expression.JOY:
            return Pose(roll=6 * fast, pitch=-6, z=6, antennas=(-0.8 + 0.3 * fast, 0.8 + 0.3 * fast))
        case Expression.SIGH:
            return Pose(pitch=10, z=-5, antennas=(0.4, -0.4))
        case Expression.THOUGHTFUL:
            return Pose(roll=12, yaw=10, pitch=-4, antennas=(-0.7, 0.0))
        case Expression.WHISPER:
            return Pose(pitch=6, yaw=-8, z=-3, antennas=(-0.05, 0.05))
        case Expression.EXCITED:
            return Pose(pitch=-8, z=7, antennas=(-0.9 + 0.4 * fast, 0.9 - 0.4 * fast))
        case _:  # Expression.AHEM, clearing the throat
            return Pose(pitch=6 * abs(fast), antennas=REST_ANTENNAS)


def _blend(a: Pose, b: Pose, weight: float) -> Pose:
    def mix(x: float, y: float) -> float:
        return x + (y - x) * weight

    return Pose(
        mix(a.roll, b.roll),
        mix(a.pitch, b.pitch),
        mix(a.yaw, b.yaw),
        mix(a.z, b.z),
        (mix(a.antennas[0], b.antennas[0]), mix(a.antennas[1], b.antennas[1])),
    )
