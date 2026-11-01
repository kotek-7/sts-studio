"""Extract the release archive and exercise its GUI/CLI outside the source tree."""

import json
import os
import platform
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def main():
    system = {"Linux": "linux", "Windows": "windows", "Darwin": "macos"}[platform.system()]
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
    name = f"sts-studio-{VERSION}-{system}-{arch}"
    archive = ROOT / "dist" / (name + (".tar.gz" if system == "linux" else ".zip"))
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONUTF8="1")
    env.pop("PYTHONPATH", None)
    env.pop("VIRTUAL_ENV", None)
    with tempfile.TemporaryDirectory() as directory:
        if system == "macos":
            subprocess.run(["ditto", "-x", "-k", str(archive), directory], check=True)
        else:
            shutil.unpack_archive(archive, directory)
        bundle = Path(directory) / name
        cwd = Path(directory) / "working-directory"
        cwd.mkdir()
        suffix = ".exe" if system == "windows" else ""
        cli = bundle / "cli" / f"sts-studio{suffix}"
        gui = bundle / "gui" / f"sts-studio-gui{suffix}"
        if system == "macos":
            gui = bundle / "STS Studio.app/Contents/MacOS/sts-studio-gui"

        def run(command):
            result = subprocess.run(
                command,
                cwd=cwd,
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
            and (
                any(n in p.name.lower() for n in ("qt6pdf", "qtpdf"))
                or p.name.lower().startswith(("libqpdf", "qpdf."))
            )
        ]
        assert not forbidden, f"Unexpected PDF libraries: {forbidden}"
        for name in (
            "README.md",
            "README.ja.md",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "LICENSE",
            "THIRD_PARTY_NOTICES.md",
        ):
            for reference in bundle.rglob("SPECIFICATION.md"):
                if reference.parent.name == "docs":
                    packaged = reference.parent.parent / name
                    assert packaged.read_bytes() == (ROOT / name).read_bytes(), packaged
        for source in (ROOT / "docs").rglob("*"):
            if source.is_file():
                relative = source.relative_to(ROOT)
                assert (bundle / relative).read_bytes() == source.read_bytes(), relative
        assert (bundle / "licenses/versions.json").is_file()
    print(f"Extracted GUI and CLI passed: {system}/{arch}")


if __name__ == "__main__":
    main()
