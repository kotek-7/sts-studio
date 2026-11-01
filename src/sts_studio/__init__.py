"""STS Studio servo configuration and monitoring application."""

import tomllib
from pathlib import Path

with (Path(__file__).resolve().parents[2] / "pyproject.toml").open("rb") as metadata:
    __version__: str = tomllib.load(metadata)["project"]["version"]
