"""STS Studio servo configuration and monitoring application."""

import sys
import tomllib
from pathlib import Path

root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
if not (root / "pyproject.toml").is_file():
    root = Path(__file__).resolve().parent / "resources"
with (root / "pyproject.toml").open("rb") as metadata:
    __version__: str = tomllib.load(metadata)["project"]["version"]
