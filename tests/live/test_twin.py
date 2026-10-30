"""The MuJoCo twin follows the intents (pytest -m live, with `nestor-reachy twin --headless` running).

It reads the simulated robot back: these are the virtual motors moving, not our intents.
"""

import asyncio
import math
import time
from typing import Any, cast

import pytest
from nestor_satellite import Behavior, Expression

from nestor_reachy import Animator, connect_twin
from nestor_reachy.pose import EXPRESSION_S, REST_ANTENNAS

pytestmark = pytest.mark.live


async def sample(mini: Any, duration_s: float, animator: Animator, *, beat_every_s: float | None = None) -> list[Any]:
    import numpy as np

    samples, started, next_beat = [], time.monotonic(), 0.0
    while (t := time.monotonic() - started) < duration_s:
        animator.heartbeat()
        if beat_every_s and t >= next_beat:
            animator.beat()
            next_beat += beat_every_s
        head = await asyncio.to_thread(mini.get_current_head_pose)
        antennas = await asyncio.to_thread(mini.get_present_antenna_joint_positions)
        angle = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(head[:3, :3]) - 1) / 2))))
        samples.append((angle, abs(antennas[1] - antennas[0])))
        await asyncio.sleep(0.05)
    return samples


async def test_the_simulated_reachy_follows_the_intents() -> None:
    robot = await connect_twin()
    if robot is None:
        pytest.skip("no simulated Reachy Mini daemon: run `nestor-reachy twin --headless`")
    mini = cast(Any, robot)._robot._mini  # read the motors back, below the safety boundary
    animator = Animator(robot)
    animator.connected(True)
    await animator.start()
    try:
        await asyncio.sleep(1.0)
        idle = await sample(mini, 1.5, animator)
        animator.behavior(Behavior.SPEAKING)
        speaking = await sample(mini, 2.0, animator, beat_every_s=0.3)
        animator.expression(Expression.JOY, 1.0)
        laughing = await sample(mini, EXPRESSION_S, animator)
    finally:
        await animator.close()

    def spread(values: list[float]) -> float:
        return max(values) - min(values)

    assert spread([a for a, _ in idle]) < 1.5, "the head fidgets at rest"
    assert spread([a for a, _ in speaking]) > 2, "the head does not move while speaking"
    assert max(s for _, s in laughing) > REST_ANTENNAS[1] - REST_ANTENNAS[0] + 0.8, "the antennas ignore the laugh"
