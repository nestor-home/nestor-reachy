"""The Reachy driver against the Nestor server's black-box conformance suite, robot mocked."""

from nestor.adapters.channels.voice.satellites.conformance import Launch, check_satellite
from nestor_satellite import (
    AUDIO_CAPTURE,
    EXPRESSION,
    HEAD_MOTION,
    IDENTIFY,
    PairingMethod,
    RecordingSink,
    SilenceSource,
)

from nestor_reachy import REST, ReachySatellite
from nestor_reachy.pose import REST_ANTENNAS

from .doubles import RecordingRobot


class Driver:
    """As the suite launches it: a fresh robot satellite per scenario, its token in the given folder."""

    def __init__(self, robot: RecordingRobot | None) -> None:
        self.robot = robot
        self.sink = RecordingSink()
        self.reachy: ReachySatellite | None = None

    async def __call__(self, launch: Launch) -> None:
        self.reachy = ReachySatellite(launch.url, "salon", robot=self.robot, tokens=launch.state / "token.json",
                                      source=SilenceSource(), sink=self.sink, enrollment=launch.pairing_uri,
                                      environ={}, poll_s=0.1)  # fmt: skip
        await self.reachy.run()


async def test_the_reachy_driver_conforms_and_its_head_follows_the_intents() -> None:
    robot = RecordingRobot()
    driver = Driver(robot)
    findings = await check_satellite(driver, deadline_s=10)

    assert findings.passed, findings.failures()
    checks = {f.check for f in findings.items}
    assert {
        "acknowledges intent.expression within 1 s",
        "acknowledges intent.beat within 1 s",
        "keeps polling after a pending identify (I1)",
        "acknowledges intent.identify within 1 s",
        "pairs with the enrollment code of NESTOR_PAIRING_URI, no code typed (P3, P4)",
    } <= checks
    assert driver.sink.played, "the core's voice reached the speaker"
    assert max(p.antennas[1] - p.antennas[0] for p in robot.targets) > 1.0, "the expression moved the antennas"
    at_rest = [p for p in robot.targets if (p.roll, p.pitch, p.yaw, p.z) == (0, 0, 0, 0)]
    assert any(abs(p.antennas[1] - REST_ANTENNAS[1]) > 0.4 for p in at_rest), "it wiggled while waiting to pair"
    assert robot.targets[-1] == REST and robot.closed, "stopped at rest"


async def test_without_a_robot_it_is_still_a_conforming_voice_satellite() -> None:
    driver = Driver(None)
    findings = await check_satellite(driver, deadline_s=10)
    assert findings.passed, findings.failures()
    assert driver.reachy is not None
    manifest = driver.reachy.satellite.manifest
    assert AUDIO_CAPTURE in manifest.names and not {EXPRESSION, HEAD_MOTION, IDENTIFY} & manifest.names
    assert manifest.pairing_methods == (PairingMethod.SPEECH, PairingMethod.PROVISIONING), "it says its code"
