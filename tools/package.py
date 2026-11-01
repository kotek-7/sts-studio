#!/usr/bin/env python3
"""Build native, folder-based GUI/CLI bundles and a source archive."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import plistlib
import shutil
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

from dependency_sources import prepare

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
OUT = ROOT / "dist"


def licenses(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    packages = {}
    for name in ("PySide6-Essentials", "shiboken6", "pyserial", "pyinstaller"):
        dist = importlib.metadata.distribution(name)
        packages[name] = dist.version
        for file in dist.files or []:
            if any(
                part.lower() in ("licenses", "license") for part in file.parts
            ) or file.name.lower().startswith(("license", "copying", "copyright")):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    target = destination / name / str(file).replace("../", "")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    # CPython's license includes notices for its bundled components.
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.exists():
        import sysconfig

        python_license = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
    if not python_license.exists():
        raise RuntimeError("Python LICENSE.txt was not found")
    shutil.copy2(python_license, destination / "Python-LICENSE.txt")
    packages["Python"] = platform.python_version()
    (destination / "versions.json").write_text(
        json.dumps(packages, indent=2) + "\n", encoding="utf-8"
    )


def build() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="store_true", help="Also create a source archive")
    args = parser.parse_args()
    system = {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}[platform.system()]
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
    OUT.mkdir(exist_ok=True)
    work = ROOT / "work" / "package"
    work.mkdir(parents=True, exist_ok=True)
    notices = work / "licenses"
    if notices.exists():
        shutil.rmtree(notices)
    licenses(notices)
    source_notices, source_archives = prepare()
    shutil.copytree(source_notices, notices / "Qt-and-PySide", dirs_exist_ok=True)
    data = [(ROOT / name, name) for name in ("spec", "docs")]
    data += [
        (ROOT / name, ".")
        for name in ("pyproject.toml", "LICENSE", "THIRD_PARTY_NOTICES.md", "sts-studio.svg")
    ]
    data.append((notices, "licenses"))
    for entry, name in (("cli", "sts-studio"), ("gui", "sts-studio-gui")):
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--additional-hooks-dir",
            str(ROOT / "packaging/hooks"),
            "--name",
            name,
            "--paths",
            str(ROOT / "src"),
            "--distpath",
            str(work / "native"),
            "--workpath",
            str(work / "build" / entry),
            "--specpath",
            str(work),
        ]
        for source, dest in data:
            command += ["--add-data", f"{source}:{dest}"]
        if system == "windows":
            version_file = work / f"{name}-version.txt"
            numbers = tuple(int(part) for part in VERSION.split(".")) + (0,)
            version_file.write_text(
                f"VSVersionInfo(ffi=FixedFileInfo(filevers={numbers!r}, prodvers={numbers!r}, mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)), kids=[StringFileInfo([StringTable('040904B0', [StringStruct('CompanyName', 'kotek'), StringStruct('FileDescription', 'STS Studio - FEETECH Debug Tool'), StringStruct('FileVersion', '{VERSION}'), StringStruct('ProductName', 'STS Studio'), StringStruct('ProductVersion', '{VERSION}'), StringStruct('OriginalFilename', '{name}.exe'), StringStruct('LegalCopyright', 'Copyright (c) 2026 kotek')])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])",
                encoding="utf-8",
            )
            command += ["--version-file", str(version_file)]
        if entry == "gui" and system in ("windows", "macos"):
            command.append("--windowed")
            command += [
                "--icon",
                str(
                    ROOT
                    / "packaging"
                    / ("sts-studio.ico" if system == "windows" else "sts-studio.icns")
                ),
            ]
        if system == "macos":
            command += [
                "--osx-bundle-identifier",
                "io.github.kotek-7.sts-studio",
                "--codesign-identity",
                "-",
            ]
        command.append(str(ROOT / "packaging" / f"{entry}.py"))
        subprocess.run(command, cwd=ROOT, check=True)
    bundle = OUT / f"sts-studio-{VERSION}-{system}-{arch}"
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir()
    shutil.copytree(work / "native/sts-studio", bundle / "cli", symlinks=True)
    if system == "macos":
        shutil.copytree(
            work / "native/sts-studio-gui.app", bundle / "STS Studio.app", symlinks=True
        )
        app_bundle = bundle / "STS Studio.app"
        info_path = app_bundle / "Contents/Info.plist"
        with info_path.open("rb") as stream:
            info = plistlib.load(stream)
        info.update(
            CFBundleName="STS Studio",
            CFBundleDisplayName="STS Studio",
            CFBundleShortVersionString=VERSION,
            CFBundleVersion=VERSION,
            LSMinimumSystemVersion="14.0",
        )
        with info_path.open("wb") as stream:
            plistlib.dump(info, stream)
        subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", str(app_bundle)], check=True
        )
    else:
        shutil.copytree(work / "native/sts-studio-gui", bundle / "gui", symlinks=True)
    for name in (
        "README.md",
        "README.ja.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
    ):
        shutil.copy2(ROOT / name, bundle / name)
    shutil.copytree(ROOT / "docs", bundle / "docs")
    shutil.copytree(notices, bundle / "licenses")
    if system == "macos":
        subprocess.run(
            [
                "ditto",
                "-c",
                "-k",
                "--sequesterRsrc",
                "--keepParent",
                str(bundle),
                str(bundle) + ".zip",
            ],
            check=True,
        )
    else:
        shutil.make_archive(
            str(bundle), "zip" if system == "windows" else "gztar", OUT, bundle.name
        )
    if system == "linux":
        stage = work / "deb"
        if stage.exists():
            shutil.rmtree(stage)
        shutil.copytree(bundle, stage / "opt/sts-studio", symlinks=True)
        control = stage / "DEBIAN"
        control.mkdir()
        (control / "control").write_text(
            f"Package: sts-studio\nVersion: {VERSION}\nSection: electronics\nPriority: optional\nArchitecture: {'arm64' if arch == 'arm64' else 'amd64'}\n"
            "Depends: libc6 (>= 2.39), libgl1, libegl1, libxkbcommon0, libdbus-1-3, libfontconfig1, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-xkb1, libxkbcommon-x11-0\n"
            "Maintainer: kotek <scpktk@gmail.com>\nHomepage: https://github.com/kotek-7/sts-studio\nDescription: FEETECH servo configuration and monitoring tool\n",
            encoding="utf-8",
        )
        binaries = stage / "usr/bin"
        binaries.mkdir(parents=True)
        for name, subdir in (("sts-studio", "cli"), ("sts-studio-gui", "gui")):
            script = binaries / name
            script.write_text(
                f'#!/bin/sh\nexec /opt/sts-studio/{subdir}/{name} "$@"\n', encoding="utf-8"
            )
            script.chmod(0o755)
        desktop = stage / "usr/share/applications"
        desktop.mkdir(parents=True)
        icon = stage / "usr/share/icons/hicolor/scalable/apps"
        icon.mkdir(parents=True)
        shutil.copy2(ROOT / "sts-studio.svg", icon / "sts-studio.svg")
        (desktop / "sts-studio.desktop").write_text(
            "[Desktop Entry]\nType=Application\nName=STS Studio\nComment=FEETECH Debug Tool\nExec=sts-studio-gui\nIcon=sts-studio\nTerminal=false\nCategories=Development;Electronics;\n",
            encoding="utf-8",
        )
        copyright_dir = stage / "usr/share/doc/sts-studio"
        copyright_dir.mkdir(parents=True)
        shutil.copy2(ROOT / "LICENSE", copyright_dir / "copyright")
        subprocess.run(
            [
                "dpkg-deb",
                "--root-owner-group",
                "--build",
                str(stage),
                str(OUT / f"sts-studio_{VERSION}_{'arm64' if arch == 'arm64' else 'amd64'}.deb"),
            ],
            check=True,
        )
    if args.source:
        for archive in source_archives:
            shutil.copy2(archive, OUT / archive.name)
        files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
        with tarfile.open(OUT / f"sts-studio-{VERSION}-source.tar.gz", "w:gz") as archive:
            for name in sorted(filter(None, files)):
                archive.add(ROOT / name, arcname=f"sts-studio-{VERSION}/{name}", recursive=False)
    assets = sorted(
        p
        for p in OUT.iterdir()
        if p.is_file()
        and (
            p.name.startswith((f"sts-studio-{VERSION}-", f"sts-studio_{VERSION}_"))
            or (args.source and p.name in {a.name for a in source_archives})
        )
        and p.name.endswith((".zip", ".tar.gz", ".tar.xz", ".deb"))
    )
    (OUT / f"SHA256SUMS-{system}-{arch}.txt").write_text(
        "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in assets),
        encoding="utf-8",
    )
    print(bundle)


if __name__ == "__main__":
    build()
