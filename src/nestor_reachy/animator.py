"""The Reachy body: keeps the latest intents and animates the robot at 30 Hz, on the device.

Safety never depends on the network: the animation loop runs locally and rests the robot when the
link to the core is down, or when nothing has been heard from it (intent or audio) for
`watchdog_s`: a frozen core cannot leave the head mid-gesture. Asked to identify itself, it wiggles
its antennas for a moment, even at rest (while it waits to be paired, the link is not up yet).
"""

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable

from nestor_satellite import Behavior, Body, Expression

from nestor_reachy.pose import RATE_HZ, REST, Pose, identify, pose
from nestor_reachy.robot import Robot

logger = logging.getLogger(__name__)


class Animator(Body):
    def __init__(self, robot: Robot, *, watchdog_s: float = 2.0, clock: Callable[[], float] = time.monotonic) -> None:
        self._robot = robot
        self._watchdog_s = watchdog_s
        self._clock = clock
        self._behavior = Behavior.IDLE
        self._expression: Expression | None = None
        self._expression_at = 0.0
        self._beat_at: float | None = None
        self._heard_at: float | None = None
        self._identify_at: float | None = None
        self._linked = False
        self._loop: asyncio.Task[None] | None = None
        self.lost = False

    # Intents, from the network loop: they only update the state.

    def behavior(self, behavior: Behavior) -> None:
        self._behavior = behavior

    def expression(self, expression: Expression, intensity: float) -> None:
        self._expression, self._expression_at = expression, self._clock()

    def beat(self) -> None:
        self._beat_at = self._clock()

    def identify(self) -> None:
        self._identify_at = self._clock()

    def heartbeat(self) -> None:
        self._heard_at = self._clock()

    def connected(self, up: bool) -> None:
        self._linked = up
        if up:
            self._heard_at = self._clock()

    # The animation, on the device.

    @property
    def resting(self) -> bool:
        """The watchdog holds the robot at rest: no link, or a silent core."""
        silent = self._heard_at is None or self._clock() - self._heard_at > self._watchdog_s
        return not self._linked or silent

    def target(self) -> Pose:
        now = self._clock()
        if self.resting:
            self._behavior, self._expression, self._beat_at = Behavior.IDLE, None, None
            current = REST
        else:
            current = pose(
                self._behavior,
                now,
                expression=self._expression,
                expression_age=now - self._expression_at,
                beat_age=None if self._beat_at is None else now - self._beat_at,
            )
        return current if self._identify_at is None else identify(current, now - self._identify_at)

    async def start(self) -> None:
        self._loop = asyncio.create_task(self._animate(), name="reachy animation")

    async def close(self) -> None:
        if self._loop is not None:
            self._loop.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._loop
        if not self.lost:
            with contextlib.suppress(Exception):
                await self._robot.set_target(REST)
        await self._robot.close()

    async def _animate(self) -> None:
        while True:
            try:
                await self._robot.set_target(self.target())
            except Exception as error:  # the body is optional: lose it, not the conversation
                logger.warning("Reachy Mini lost (%s): the satellite goes on without a body", error)
                self.lost = True
                return
            await asyncio.sleep(1 / RATE_HZ)
