# nestor-reachy

[Reachy Mini](https://www.pollen-robotics.com/reachy-mini/) as a satellite of
[Nestor](https://github.com/nestor-home/nestor): the assistant speaks and listens through it, and
its head and antennas follow the conversation — listening, thinking, speaking, nodding on each word,
laughing when the voice laughs. Built on [nestor-satellite](https://github.com/nestor-home/nestor-satellite-python).

> **Status:** the MuJoCo twin only. A physical robot is refused until its safety policy is
> validated on hardware; the robot's own microphone and speaker come later.

```bash
pip install "nestor-reachy[reachy,audio]"
nestor-reachy twin --headless &                               # the simulated robot
nestor-reachy run --core http://nestor.local:7860 --room salon # shows a pairing code the first time
```

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
