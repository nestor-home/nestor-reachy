"""A recording robot and a manual clock."""

from nestor_reachy import Pose, Robot


class RecordingRobot(Robot):
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.targets: list[Pose] = []
        self.closed = False

    async def set_target(self, pose: Pose) -> None:
        if self.fail:
            raise ConnectionError("the daemon is gone")
        self.targets.append(pose)

    async def close(self) -> None:
        self.closed = True


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now
