"""Reachy Mini as a satellite: the SDK's connection, with the animator as its body.

Without a robot (no twin running), it is still a voice satellite: it then declares only audio.
"""

from collections.abc import Callable
from pathlib import Path

from nestor_satellite import (
    AUDIO_CAPTURE,
    AUDIO_PLAYBACK,
    EXPRESSION,
    HEAD_MOTION,
    AudioSink,
    AudioSource,
    Device,
    Manifest,
    Satellite,
    TokenStore,
)
from nestor_satellite.pairing import show_code

from nestor_reachy.animator import Animator
from nestor_reachy.robot import Robot

MODEL = "reachy-mini"


def manifest(room: str, *, device_id: str | None = None, body: bool = True) -> Manifest:
    device = Device(device_id or f"reachy-{room}", MODEL, room)
    motion = (EXPRESSION, HEAD_MOTION) if body else ()
    return Manifest.of(device, AUDIO_CAPTURE, AUDIO_PLAYBACK, *motion)


class ReachySatellite:
    """`run` animates the robot and stays connected to the core until cancelled; the robot is back
    at rest when it returns."""

    def __init__(
        self,
        core: str,
        room: str,
        *,
        robot: Robot | None,
        tokens: TokenStore | Path | str,
        source: AudioSource | None = None,
        sink: AudioSink | None = None,
        device_id: str | None = None,
        on_code: Callable[[str], None] = show_code,
        poll_s: float = 1.0,
    ) -> None:
        self.animator = Animator(robot) if robot is not None else None
        self.satellite = Satellite(
            core,
            manifest(room, device_id=device_id, body=robot is not None),
            tokens=tokens if isinstance(tokens, TokenStore) else TokenStore(tokens),
            body=self.animator,
            source=source,
            sink=sink,
            on_code=on_code,
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
