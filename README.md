# nestor-reachy

[Reachy Mini](https://www.pollen-robotics.com/reachy-mini/) as a satellite of
[Nestor](https://github.com/nestor-home/nestor): the assistant speaks and listens through it, and
its head and antennas follow the conversation: listening, thinking, speaking, nodding on each word,
laughing when the voice laughs. Built on [nestor-satellite](https://github.com/nestor-home/nestor-satellite-python).

> **Status:** the MuJoCo twin only. A physical robot is refused until its safety policy is
> validated on hardware; the robot's own microphone and speaker come later.

```bash
pip install "nestor-reachy[reachy,audio]"
nestor-reachy twin --headless &                               # the simulated robot
nestor-reachy run --room salon --pairing-uri "nestor+http://nestor.local:7860/?code=K7QF2M9X"
```

## Pairing

Reachy has a speaker and no screen. The simplest is an **enrollment code**: add a satellite in the
Nestor admin with the provisioning method (`enrollment.provisioning`), and give the robot the
pairing URI it returns, by flag or in its environment:

```bash
NESTOR_PAIRING_URI="nestor+http://nestor.local:7860/?code=K7QF2M9X" nestor-reachy run --room salon
nestor-reachy run --core http://nestor.local:7860 --room salon --pairing-code K7QF-2M9X
```

Without one, it says a six-digit device code on its speaker, twice, digit by digit, with the SDK's
recorded voice (`device_code.speech`, offline), and logs it: type it in the admin. The token is then kept in
`~/.config/nestor-reachy/reachy-<room>.json` and later runs reconnect with it
(`nestor-reachy run --core http://nestor.local:7860 --room salon`). To tell robots apart, the admin
can ask one to identify itself: it wiggles its antennas for two seconds, while it waits to be paired
or once connected.

Safety lives on the device: every target is clamped to the motion limits, and the robot returns to
rest when the link to the core drops or nothing is heard from it for two seconds.

## Development

The tests use the Nestor server's conformance suite and the SDK from sibling checkouts
(`../nestor`, `../nestor-satellite-python`).

```bash
uv sync
uv run pre-commit install
uv run ruff check && uv run ruff format --check && uv run ty check && uv run pytest
uv run --no-dev --group live --extra reachy pytest -m live   # with `nestor-reachy twin` running
```

## License

MIT
