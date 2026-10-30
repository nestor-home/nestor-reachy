"""The motors behind a small port, and the only way to reach them: `SafeRobot` clamps every target.

`connect_twin` talks to a local Reachy Mini daemon and refuses a physical robot for now: until the
physical safety policy is validated on hardware, only the MuJoCo twin is driven. The `reachy-mini`
SDK (extra `reachy`) is imported only when connecting.
"""

import asyncio
import contextlib
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from nestor_reachy.pose import LIMITS, REST, Limits, Pose

logger = logging.getLogger(__name__)

DAEMON = "http://127.0.0.1:8000"


class Robot(ABC):
    @abstractmethod
    async def set_target(self, pose: Pose) -> None:
        """Send a head and antennas target; raises when the robot is lost."""

    @abstractmethod
    async def close(self) -> None:
        """Release the robot (it is already at rest)."""


class SafeRobot(Robot):
    """Whatever computed the pose, the motors never get a target beyond `limits`."""

    def __init__(self, robot: Robot, limits: Limits = LIMITS) -> None:
        self._robot, self._limits = robot, limits

    async def set_target(self, pose: Pose) -> None:
        await self._robot.set_target(pose.clamped(self._limits))

    async def close(self) -> None:
        await self._robot.close()


class ReachyMiniRobot(Robot):
    """A `reachy_mini.ReachyMini` connection; calls block, so they run in a thread."""

    def __init__(self, mini: Any) -> None:
        self._mini = mini

    async def set_target(self, pose: Pose) -> None:
        from reachy_mini.utils import create_head_pose

        head = create_head_pose(z=pose.z, roll=pose.roll, pitch=pose.pitch, yaw=pose.yaw, mm=True, degrees=True)
        await asyncio.to_thread(self._mini.set_target, head=head, antennas=list(pose.antennas))

    async def close(self) -> None:
        with contextlib.suppress(Exception):
            await self.set_target(REST)
        with contextlib.suppress(Exception):
            await asyncio.to_thread(self._mini.__exit__, None, None, None)


async def connect_twin(url: str = DAEMON, *, transport: httpx.AsyncBaseTransport | None = None) -> Robot | None:
    """The simulated Reachy Mini behind a local daemon, or `None` (logged): no daemon, a physical
    robot, or the SDK missing. Without a body, the satellite still speaks and listens."""
    try:
        async with httpx.AsyncClient(timeout=2, transport=transport) as http:
            status = (await http.get(f"{url}/api/daemon/status")).json()
    except (httpx.HTTPError, ValueError):
        logger.warning("no Reachy Mini daemon at %s: running without a body (start one with `nestor-reachy twin`)", url)
        return None
    if status.get("simulation_enabled") is not True:
        logger.error("the daemon at %s drives a physical robot: refused, only the simulated twin is supported", url)
        return None
    try:
        from reachy_mini import ReachyMini
    except ImportError:
        logger.warning("the reachy-mini SDK is missing (`pip install nestor-reachy[reachy]`): running without a body")
        return None
    host, _, port = url.removeprefix("http://").partition(":")
    try:
        mini = await asyncio.to_thread(
            ReachyMini, host=host, port=int(port or 8000), connection_mode="localhost_only", spawn_daemon=False,
            media_backend="no_media", automatic_body_yaw=False, timeout=5,
        )  # fmt: skip
    except Exception as error:
        logger.warning("could not connect to the Reachy Mini twin (%s): running without a body", error)
        return None
    return SafeRobot(ReachyMiniRobot(mini))
