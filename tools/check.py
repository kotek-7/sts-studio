#!/usr/bin/env python3
"""Run the same read-only quality gates locally, in Git hooks, and in CI."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--static", action="store_true", help="Skip integration tests")
    args = parser.parse_args()
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    checks = [
        ["-m", "ruff", "format", "--check", "src", "tests", "tools"],
        ["-m", "ruff", "check", "src", "tests", "tools"],
        ["-m", "mypy"],
        ["tools/render_spec.py", "--check"],
    ]
    if not args.static:
        checks.append(["-m", "pytest", "-q"])
    for command in checks:
        subprocess.run([sys.executable, *command], cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    main()
