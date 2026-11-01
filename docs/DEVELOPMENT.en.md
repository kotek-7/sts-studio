# Development

Use Python 3.12 and uv. Dependencies are locked in `uv.lock`.

```sh
uv sync --locked
uv run --locked python -m sts_studio --demo
uv run --locked python tools/check.py
```

`ui/window.py` composes the desktop. Feature controllers handle connection, programming, motion, monitoring, diagnostics, and PWM. `runtime/session.py` owns connection identity and unconfirmed actuator state. `runtime/executor.py` and `jobs.py` serialize GUI I/O through one worker. The CLI calls the same `service.py` operations synchronously. `wire.py` handles serial frames, while `simulator.py` provides a virtual bus.

Keep serial work off the GUI thread. STOP discards deferred UI actions and pending manual motion before scheduling torque OFF. A communication timeout does not prove that a write did not occur. Preserve those behaviors when changing execution or error handling.

`spec/features.json` defines feature contracts, `spec/catalog.json` defines models and registers, and `spec/protocol.json` defines packet details. Generate the reference documents after changing these files:

```sh
uv run --locked ruff format src tests tools
uv run --locked python tools/render_spec.py
uv run --locked python tools/check.py
```

Tests use VirtualLink, Qt interaction, and Linux PTYs. PTY tests run only on Linux; the remaining tests run on all supported CI operating systems. No physical servo is required. [Detailed design](DESIGN.md), [register tables](REGISTERS.md), and [feature contracts](SPECIFICATION.md) are in Japanese.

Use `uv add` / `uv remove` for dependency changes and commit `pyproject.toml` with `uv.lock`. To enable local static checks before commits, run `git config core.hooksPath .githooks`. The full test suite is run by CI.

See [release builds](RELEASING.md) for native bundles and [contributing](../CONTRIBUTING.md) for pull requests.
