#!/usr/bin/env python3
"""Build the Debian package and source distribution."""

import shutil
import subprocess
import tarfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
out = ROOT / "dist"
out.mkdir(exist_ok=True)
stage = out / "deb-stage"
if stage.exists():
    shutil.rmtree(stage)
app = stage / "opt/sts-studio"
app.mkdir(parents=True)
for name in ("src", "spec", "docs", "tools", "tests"):
    shutil.copytree(ROOT / name, app / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
for name in (
    "run.sh",
    "README.md",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "sts-studio.svg",
):
    shutil.copy2(ROOT / name, app / name)
control = stage / "DEBIAN"
control.mkdir()
(control / "control").write_text(
    f"Package: sts-studio\nVersion: {VERSION}\nSection: electronics\nPriority: optional\nArchitecture: all\nDepends: python3 (>= 3.12), python3-pyqt5, python3-serial\nMaintainer: STS Studio local project <local@localhost>\nDescription: STS servo configuration, control, and monitoring application\n"
)
launcher = stage / "usr/share/applications"
launcher.mkdir(parents=True)
(launcher / "sts-studio.desktop").write_text(
    "[Desktop Entry]\nType=Application\nName=STS Studio\nExec=/opt/sts-studio/run.sh\nIcon=/opt/sts-studio/sts-studio.svg\nTerminal=false\nCategories=Development;Electronics;\n"
)
subprocess.run(
    [
        "dpkg-deb",
        "--root-owner-group",
        "--build",
        str(stage),
        str(out / f"sts-studio_{VERSION}_all.deb"),
    ],
    check=True,
)
with tarfile.open(out / f"sts-studio-{VERSION}-source.tar.gz", "w:gz") as tar:
    for name in (
        "src",
        "spec",
        "docs",
        "tools",
        "tests",
        "run.sh",
        "README.md",
        "pyproject.toml",
        "uv.lock",
        ".python-version",
        ".editorconfig",
        ".gitattributes",
        ".githooks",
        ".github",
        "sts-studio.svg",
        ".gitignore",
    ):
        tar.add(
            ROOT / name,
            arcname="sts-studio/" + name,
            filter=lambda item: (
                None if "__pycache__" in item.name or item.name.endswith(".pyc") else item
            ),
        )
print(out)
