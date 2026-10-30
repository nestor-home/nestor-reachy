import os
import sys
from types import SimpleNamespace
from typing import Any

import pytest
from nestor_satellite import PAIRING_CODE, PAIRING_URI, PairingFailed

from nestor_reachy import ReachySatellite, cli

from .doubles import RecordingRobot


@pytest.fixture(autouse=True)
def no_pairing_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PAIRING_URI, raising=False)
    monkeypatch.delenv(PAIRING_CODE, raising=False)


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


async def test_a_pairing_uri_is_all_a_headless_robot_needs(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[ReachySatellite] = []

    async def no_twin(url: str) -> None:
        return None

    async def run(self: ReachySatellite) -> None:
        ran.append(self)

    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace())
    monkeypatch.setattr(cli, "connect_twin", no_twin)
    monkeypatch.setattr(ReachySatellite, "run", run)
    uri = "nestor+https://nestor.example.org/?code=K7QF2M9X"
    await cli.serve(cli.parse(["run", "--room", "salon", "--pairing-uri", uri, "--lang", "fr"]))
    monkeypatch.setenv(PAIRING_URI, uri)
    await cli.serve(cli.parse(["run", "--room", "salon"]))

    assert [r.satellite.core for r in ran] == ["https://nestor.example.org"] * 2
    assert ran[0].satellite.messages.language == "fr"


def test_a_robot_that_cannot_be_configured_or_paired_exits_with_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace())

    async def no_twin(url: str) -> None:
        return None

    monkeypatch.setattr(cli, "connect_twin", no_twin)
    with pytest.raises(SystemExit, match="NESTOR_PAIRING_URI"):
        cli.main(["run", "--room", "salon", "--pairing-code", "K7QF2M9X", "--lang", "en"])

    async def refused(self: ReachySatellite) -> None:
        raise PairingFailed("update the device")

    monkeypatch.setattr(ReachySatellite, "run", refused)
    with pytest.raises(SystemExit) as exited:
        cli.main(["run", "--core", "http://h:7860", "--room", "salon"])
    assert exited.value.code == 1


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
