"""`nestor-reachy`: Reachy Mini as a satellite of a Nestor core.

    nestor-reachy twin --headless            # the simulated robot (MuJoCo), needs the `reachy` extra
    nestor-reachy run --room salon --pairing-uri "nestor+http://nestor.local:7860/?code=K7QF2M9X"
    nestor-reachy run --core http://nestor.local:7860 --room salon   # once paired, or to pair by its device code

Reachy has no screen: give it the pairing URI of an enrollment code made in Nestor (flag, or
`NESTOR_PAIRING_URI`), or type in Nestor the code it says on its speaker (and logs). On the twin,
the voice goes through this machine's microphone and speaker (`audio` extra).
"""

import argparse
import asyncio
import contextlib
import logging
import os
import shutil
import sys
from collections.abc import Sequence

from nestor_satellite import InvalidEnrollment, PairingFailed

from nestor_reachy.driver import ReachySatellite
from nestor_reachy.robot import DAEMON, connect_twin


def parse(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="nestor-reachy", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="connect the robot to a Nestor core")
    run.add_argument(
        "--core", help="the core's voice server, e.g. http://nestor.local:7860 (default: the pairing URI's)"
    )
    enrollment = run.add_mutually_exclusive_group()
    enrollment.add_argument("--pairing-uri", help="pair with this enrollment code's URI (default: $NESTOR_PAIRING_URI)")
    enrollment.add_argument("--pairing-code", help="pair with this enrollment code (default: $NESTOR_PAIRING_CODE)")
    run.add_argument("--lang", help="the language of what it says, en or fr (default: the environment's)")
    run.add_argument("--room", required=True, help="the room the robot is in (a slug: salon, cuisine…)")
    run.add_argument("--id", help="this robot's id (default: reachy-<room>)")
    run.add_argument("--daemon", default=DAEMON, help="the Reachy Mini daemon (simulated only, for now)")
    run.add_argument("--token-file", help="where the token is kept (default: ~/.config/nestor-reachy/<id>.json)")
    run.add_argument("-v", "--verbose", action="store_true")
    twin = commands.add_parser("twin", help="start the simulated Reachy Mini (MuJoCo daemon)")
    twin.add_argument("--headless", action="store_true", help="no window")
    return parser.parse_args(argv)


async def serve(args: argparse.Namespace) -> None:
    from nestor_satellite.devices import Microphone, Speaker

    robot = await connect_twin(args.daemon)
    device_id = args.id or f"reachy-{args.room}"
    satellite = ReachySatellite(
        args.core,
        args.room,
        robot=robot,
        tokens=args.token_file or f"~/.config/nestor-reachy/{device_id}.json",
        source=Microphone(),
        sink=Speaker(),
        device_id=device_id,
        enrollment=args.pairing_uri or args.pairing_code,
        locale=args.lang,
    )
    await satellite.run()


def twin(headless: bool) -> None:
    """Replace this process with the Reachy Mini daemon in simulation, on the default port. Its window
    needs MuJoCo's `mjpython` on macOS; headless, the plain interpreter is enough."""
    python = (
        sys.executable
        if headless
        else shutil.which("mjpython") or os.path.join(os.path.dirname(sys.executable), "mjpython")
    )
    args = [python, "-m", "reachy_mini.daemon.app.main", "--sim", "--no-media", "--scene", "minimal",
            "--fastapi-host", "127.0.0.1", "--fastapi-port", "8000", "--no-preload-datasets",
            "--dataset-update-interval", "0", *(["--headless"] if headless else [])]  # fmt: skip
    os.execve(python, args, {**os.environ, "REACHY_MINI_TELEMETRY": "0"})


def main(argv: Sequence[str] | None = None) -> None:
    args = parse(argv)
    if args.command == "twin":
        twin(args.headless)
        return
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")
    with contextlib.suppress(KeyboardInterrupt):
        try:
            asyncio.run(serve(args))
        except (InvalidEnrollment, ValueError) as error:
            sys.exit(f"nestor-reachy: {error}")
        except PairingFailed:
            sys.exit(1)  # already said why, in the log
