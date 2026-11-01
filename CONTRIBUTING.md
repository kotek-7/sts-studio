# Contributing

Report a bug in [Issues](https://github.com/kotek-7/sts-studio/issues) with the version, OS, reproduction steps, and relevant log output. For serial communication problems, include the servo model, firmware version, adapter, baud rate, and whether the problem occurs in demo mode. Remove personal paths or identifiers from logs before posting.

For code changes, start with the [development guide](docs/DEVELOPMENT.en.md). Keep each pull request focused on one behavior and explain how it was checked. Communication changes should include a packet or simulator regression test; UI changes should include a screenshot when the layout changes.

```sh
uv sync --locked
uv run --locked python tools/check.py
```

Edit `spec/` before regenerating its documentation. Do not hand-edit generated tables. Run `uv run --locked python tools/render_spec.py`, then commit the definitions and generated files together.

Contributions are accepted under the project's MIT license. Report security issues using the instructions in [SECURITY.md](SECURITY.md).

日本語でのIssue・Pull Requestも歓迎します。[日本語の開発ガイド](docs/DEVELOPMENT.md)を参照してください。
