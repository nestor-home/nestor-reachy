"""The Reachy driver against the Nestor server's black-box conformance suite, robot mocked."""

from pathlib import Path

from nestor.adapters.channels.voice.satellites.conformance import check_satellite
from nestor_satellite import AUDIO_CAPTURE, EXPRESSION, HEAD_MOTION, RecordingSink, SilenceSource

from nestor_reachy import REST, ReachySatellite

from .doubles import RecordingRobot


class Driver:
    def __init__(self, tokens: Path, robot: RecordingRobot | None) -> None:
        self.tokens, self.robot = tokens, robot
        self.sink = RecordingSink()
        self.reachy: ReachySatellite | None = None

    async def __call__(self, url: str) -> None:
        self.reachy = ReachySatellite(url, "salon", robot=self.robot, tokens=self.tokens, source=SilenceSource(),
                                      sink=self.sink, on_code=lambda _code: None, poll_s=0.1)  # fmt: skip
        await self.reachy.run()


async def test_the_reachy_driver_conforms_and_its_head_follows_the_intents(tmp_path: Path) -> None:
    robot = RecordingRobot()
    driver = Driver(tmp_path / "token.json", robot)
    findings = await check_satellite(driver, deadline_s=10)

    assert findings.passed, findings.failures()
    checks = {f.check for f in findings.items}
    assert {"acknowledges intent.expression within 1 s", "acknowledges intent.beat within 1 s"} <= checks
    assert driver.sink.played, "the core's voice reached the speaker"
    assert max(p.antennas[1] - p.antennas[0] for p in robot.targets) > 1.0, "the expression moved the antennas"
    assert robot.targets[-1] == REST and robot.closed, "stopped at rest"


async def test_without_a_robot_it_is_still_a_conforming_voice_satellite(tmp_path: Path) -> None:
    driver = Driver(tmp_path / "token.json", None)
    findings = await check_satellite(driver, deadline_s=10)
    assert findings.passed, findings.failures()
    assert driver.reachy is not None
    names = driver.reachy.satellite.manifest.names
    assert AUDIO_CAPTURE in names and not {EXPRESSION, HEAD_MOTION} & names
