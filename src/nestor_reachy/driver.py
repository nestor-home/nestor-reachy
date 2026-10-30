"""Reachy Mini as a satellite: the SDK's connection, with the animator as its body.

Without a robot (no twin running), it is still a voice satellite: it then declares only audio.

Reachy has a speaker and no screen: it is paired with an enrollment code (a pairing URI given in its
configuration, `NESTOR_PAIRING_URI` by default), or by typing in Nestor the device code it says on its
speaker with the SDK's recorded voice (`device_code.speech`) and logs. With a body, it wiggles its
antennas when asked to identify itself.
"""

from collections.abc import Mapping
from pathlib import Path

from nestor_satellite import (
    AUDIO_CAPTURE,
    AUDIO_PLAYBACK,
    EXPRESSION,
    HEAD_MOTION,
    IDENTIFY,
    AudioSink,
    AudioSource,
    Device,
    Manifest,
    Satellite,
    TokenStore,
)

from nestor_reachy.animator import Animator
from nestor_reachy.robot import Robot

MODEL = "reachy-mini"
BRAND = "pollen-robotics"


def manifest(room: str, *, device_id: str | None = None, body: bool = True) -> Manifest:
    device = Device(device_id or f"reachy-{room}", MODEL, room, BRAND)
    motion = (EXPRESSION, HEAD_MOTION, IDENTIFY) if body else ()
    return Manifest.of(device, AUDIO_CAPTURE, AUDIO_PLAYBACK, *motion)


class ReachySatellite:
    """`run` animates the robot and stays connected to the core until cancelled; the robot is back
    at rest when it returns."""

    def __init__(
        self,
        core: str | None,
        room: str,
        *,
        robot: Robot | None,
        tokens: TokenStore | Path | str,
        source: AudioSource | None = None,
        sink: AudioSink | None = None,
        device_id: str | None = None,
        enrollment: str | None = None,
        locale: str | None = None,
        environ: Mapping[str, str] | None = None,
        poll_s: float = 1.0,
    ) -> None:
        """`core` may be `None` when a pairing URI says where it is; `enrollment` is a pairing URI or an
        enrollment code (by default `NESTOR_PAIRING_URI`, else `NESTOR_PAIRING_CODE`, from `environ`)."""
        self.animator = Animator(robot) if robot is not None else None
        self.satellite = Satellite(
            core,
            manifest(room, device_id=device_id, body=robot is not None),
            tokens=tokens if isinstance(tokens, TokenStore) else TokenStore(tokens),
            body=self.animator,
            source=source,
            sink=sink,
            enrollment=enrollment,
            locale=locale,
            environ=environ,
            poll_s=poll_s,
        )

    async def run(self) -> None:
        if self.animator is not None:
            await self.animator.start()
        try:
            await self.satellite.run()
        finally:
            if self.animator is not None:
                await self.animator.close()
