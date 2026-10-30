# AGENTS.md

`nestor-reachy` drives a Reachy Mini as a Nestor satellite, on top of the `nestor-satellite` SDK.
This file is for coding agents: read it before changing anything.

## Commands

```bash
uv sync                      # dev group; needs ../nestor and ../nestor-satellite-python
uv run pre-commit install
uv run ruff check && uv run ruff format --check && uv run ty check && uv run pytest
uv run --no-dev --group live --extra reachy pytest -m live   # against the running MuJoCo twin
```

All four must pass; CI runs them on Python 3.12 to 3.14. `pytest` measures branch coverage and fails
under 95 %. The `reachy` extra (the Reachy Mini SDK) and the `dev` group cannot share an environment
(websockets pins), which is why the live test has its own group. Manage dependencies with `uv add`
/ `uv remove` only, and commit `uv.lock`.

## Layout

```text
src/nestor_reachy/
├── pose.py       pure body language: pose(behavior, t, expression, beat) → Pose, motion limits
├── animator.py   the satellite's Body: latest intents, 30 Hz loop, watchdog → rest
├── robot.py      Robot port, SafeRobot (clamps every target), the Reachy Mini adapter, connect_twin
├── driver.py     ReachySatellite: manifest + SDK Satellite + animator
└── cli.py        nestor-reachy run | twin
tests/            pose and safety units, conformance with the robot mocked, live/ against the twin
```

## Safety rules

1. **Every target goes through `SafeRobot`**, which clamps it to `Limits`, whatever computed it.
2. **The watchdog is local.** The animation loop rests the robot when the link is down or the core
   has been silent for 2 s; it never waits for the network to decide.
3. **Physical robots are refused** (`connect_twin` checks `simulation_enabled`) until a motor safety
   policy (limits, emergency stop, supervision) is validated on hardware. Do not relax this.
4. **Losing the robot never stops the satellite**: it keeps speaking and listening without a body.
5. An intent never becomes a movement of a different kind (joy is never a displacement).

## Code conventions

- Python 3.12+, fully typed (`ty`), `ruff` with line length 120, English only.
- `pose.py` stays pure (no I/O, no clock): it is the robot's vocabulary and is tested exhaustively.
- The `reachy_mini` SDK is imported only inside `robot.py`, lazily: everything else runs without it.
- Never import `nestor` (the server) from `src/`: it is a dev dependency for the conformance suite.
- Keep the repository lean: no new Markdown files.

## Tests

- Test behaviour, not implementation: one behaviour per test, named as a sentence.
- The robot is a recording double; the Reachy SDK is a fake module; time is an injected clock.
- Uncovered code is either tested for a real behaviour or deleted — never excluded.
