"""Reachy Mini as a Nestor satellite: its voice, attitude and expressions, with on-device safety."""

from nestor_reachy.animator import Animator
from nestor_reachy.driver import ReachySatellite, manifest
from nestor_reachy.pose import LIMITS, REST, Limits, Pose, pose
from nestor_reachy.robot import ReachyMiniRobot, Robot, SafeRobot, connect_twin

__all__ = [
    "LIMITS",
    "REST",
    "Animator",
    "Limits",
    "Pose",
    "ReachyMiniRobot",
    "ReachySatellite",
    "Robot",
    "SafeRobot",
    "connect_twin",
    "manifest",
    "pose",
]
