import os
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from nestor_reachy import ReachySatellite, cli

from .doubles import RecordingRobot


async def test_run_connects_the_twin_and_runs_the_satellite_in_its_room(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[ReachySatellite] = []

    async def twin(url: str) -> RecordingRobot:
        assert url == "http://127.0.0.1:8000"
        return RecordingRobot()

    async def run(self: ReachySatellite) -> None:
        ran.append(self)

    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace())
    monkeypatch.setattr(cli, "connect_twin", twin)
    monkeypatch.setattr(ReachySatellite, "run", run)
    await cli.serve(cli.parse(["run", "--core", "http://nestor.local:7860", "--room", "bureau"]))

    [satellite] = ran
    device = satellite.satellite.manifest.device
    assert (device.id, device.room, device.model) == ("reachy-bureau", "bureau", "reachy-mini")
    assert satellite.satellite.tokens.path.name == "reachy-bureau.json"


def test_main_runs_until_interrupted(monkeypatch: pytest.MonkeyPatch) -> None:
    async def serve(args: Any) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "serve", serve)
    cli.main(["run", "--core", "http://h:7860", "--room", "salon", "-v"])


def test_twin_starts_the_simulated_daemon(monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[list[str]] = []
    monkeypatch.setattr(
        os, "execve", lambda python, args, env: started.append([python, *args, env["REACHY_MINI_TELEMETRY"]])
    )
    cli.main(["twin", "--headless"])
    cli.main(["twin"])
    headless, windowed = started
    assert headless[0] == sys.executable, "no viewer: no need for mjpython"
    assert "--sim" in headless and "--headless" in headless and headless[-1] == "0"
    assert windowed[0].endswith("mjpython") and "--headless" not in windowed
