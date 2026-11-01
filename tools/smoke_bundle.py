"""Exercise packaged launchers from an unrelated working directory."""

import json
import os
import platform
import subprocess
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def main():
    system = {"Linux": "linux", "Windows": "windows", "Darwin": "macos"}[platform.system()]
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
    bundle = ROOT / "dist" / f"sts-studio-{VERSION}-{system}-{arch}"
    suffix = ".exe" if system == "windows" else ""
    cli = bundle / "cli" / f"sts-studio{suffix}"
    gui = bundle / "gui" / f"sts-studio-gui{suffix}"
    if system == "macos":
        gui = bundle / "STS Studio.app/Contents/MacOS/sts-studio-gui"
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONUTF8="1")
    env.pop("PYTHONPATH", None)
    env.pop("VIRTUAL_ENV", None)
    with tempfile.TemporaryDirectory() as directory:

        def run(command):
            result = subprocess.run(
                command,
                cwd=directory,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=45,
            )
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return result

        assert run([str(cli), "--version"]).stdout.strip() == VERSION
        scan = json.loads(run([str(cli), "--demo", "scan", "--first", "1", "--last", "3"]).stdout)
        assert [servo["id"] for servo in scan["servos"]] == [1, 2]
        assert run([str(cli), "--demo", "feedback", "--id", "1"]).stdout
        run([str(gui), "--demo", "--smoke"])
    forbidden = [
        p
        for p in bundle.rglob("*")
        if p.is_file()
        and ("qt6pdf" in p.name.lower() or p.name.lower().startswith(("libqpdf", "qpdf.")))
    ]
    assert not forbidden, f"Unexpected PDF libraries: {forbidden}"
    assert (bundle / "LICENSE").is_file()
    assert (bundle / "licenses/versions.json").is_file()
    print(f"Packaged GUI and CLI passed: {system}/{arch}")


if __name__ == "__main__":
    main()
