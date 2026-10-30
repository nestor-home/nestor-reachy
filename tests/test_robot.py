"""Connecting to the Reachy Mini twin, with the daemon and the SDK replaced."""

import sys
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from nestor_reachy import REST, Pose, ReachyMiniRobot, SafeRobot, connect_twin


def daemon(status: Any) -> httpx.MockTransport:
    return httpx.MockTransport(lambda _request: httpx.Response(200, json=status))


class FakeMini:
    def __init__(self, **options: Any) -> None:
        self.options = options
        self.targets: list[tuple[dict[str, Any], list[float]]] = []
        self.exited = False

    def set_target(self, *, head: dict[str, Any], antennas: list[float]) -> None:
        self.targets.append((head, antennas))

    def __exit__(self, *exc: object) -> None:
        self.exited = True


@pytest.fixture
def sdk(monkeypatch: pytest.MonkeyPatch) -> list[FakeMini]:
    made: list[FakeMini] = []

    def mini(**options: Any) -> FakeMini:
        if options.get("port") == 9999:
            raise ConnectionError("refused")
        made.append(FakeMini(**options))
        return made[-1]

    monkeypatch.setitem(sys.modules, "reachy_mini", SimpleNamespace(ReachyMini=mini))
    monkeypatch.setitem(sys.modules, "reachy_mini.utils", SimpleNamespace(create_head_pose=lambda **pose: pose))
    return made


async def test_the_simulated_twin_is_driven_through_the_safety_boundary(sdk: list[FakeMini]) -> None:
    robot = await connect_twin("http://127.0.0.1:8000", transport=daemon({"simulation_enabled": True}))
    assert isinstance(robot, SafeRobot)
    [mini] = sdk
    assert (mini.options["port"], mini.options["spawn_daemon"]) == (8000, False)

    await robot.set_target(Pose(roll=99, antennas=(0.1, 0.2)))
    await robot.close()
    (head, antennas), (rest_head, rest_antennas) = mini.targets
    assert (head["roll"], head["degrees"], head["mm"], antennas) == (20.0, True, True, [0.1, 0.2])
    assert rest_antennas == list(REST.antennas) and rest_head["pitch"] == 0 and mini.exited


async def test_a_physical_robot_is_refused(sdk: list[FakeMini]) -> None:
    assert await connect_twin(transport=daemon({"simulation_enabled": False})) is None
    assert not sdk


async def test_without_a_daemon_there_is_no_body() -> None:
    assert await connect_twin("http://127.0.0.1:9") is None
    assert await connect_twin(transport=httpx.MockTransport(lambda _r: httpx.Response(200, text="<html>"))) is None


async def test_without_the_sdk_there_is_no_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "reachy_mini", None)
    assert await connect_twin(transport=daemon({"simulation_enabled": True})) is None


async def test_a_twin_that_refuses_the_connection_gives_no_body(sdk: list[FakeMini]) -> None:
    assert await connect_twin("http://127.0.0.1:9999", transport=daemon({"simulation_enabled": True})) is None


async def test_closing_a_lost_robot_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    class Gone:
        def set_target(self, **_: Any) -> None:
            raise ConnectionError("gone")

        def __exit__(self, *exc: object) -> None:
            raise ConnectionError("gone")

    monkeypatch.setitem(sys.modules, "reachy_mini.utils", SimpleNamespace(create_head_pose=lambda **pose: pose))
    await ReachyMiniRobot(Gone()).close()
