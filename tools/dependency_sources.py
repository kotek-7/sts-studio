"""Fetch pinned Qt sources and preserve their license/attribution files."""

import hashlib
import importlib.metadata
import shutil
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    (
        "https://download.qt.io/official_releases/qt/6.12/6.12.0/single/qt-everywhere-src-6.12.0.tar.xz",
        "98ff4f44bac6ec3e1e62ee2a4316ae0e3d15badb015d753cc0268a20db52f165",
    ),
    (
        "https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz",
        "099c1a597cf33c1b000e11cf68a0b82d216fb802bf81726efc720394f10c7751",
    ),
]


def prepare() -> tuple[Path, list[Path]]:
    if (
        importlib.metadata.version("PySide6-Essentials") != "6.12.0"
        or importlib.metadata.version("shiboken6") != "6.12.0"
    ):
        raise RuntimeError(
            "Update the corresponding Qt/PySide source pins for the installed version"
        )
    root = ROOT / "work/dependency-sources"
    root.mkdir(parents=True, exist_ok=True)
    notices = root / "notices"
    notices.mkdir(exist_ok=True)
    archives = []
    for url, digest in SOURCES:
        archive = root / url.rsplit("/", 1)[1]
        if not archive.exists():
            print(f"Downloading {archive.name}", flush=True)
            temporary = archive.with_suffix(".part")
            with (
                urllib.request.urlopen(url, timeout=120) as response,
                temporary.open("wb") as output,
            ):
                shutil.copyfileobj(response, output)
            temporary.replace(archive)
        with archive.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != digest:
            raise RuntimeError(f"Source checksum mismatch: {archive.name}")
        archives.append(archive)
        marker = notices / (archive.name + ".complete")
        if marker.exists():
            continue
        print(f"Collecting license texts from {archive.name}", flush=True)
        with tarfile.open(archive, "r|xz") as source:
            for member in source:
                path = Path(member.name)
                if not member.isfile() or path.is_absolute() or ".." in path.parts:
                    continue
                lower = path.name.lower()
                if (
                    lower.startswith(("license", "licence", "copying", "copyright"))
                    or lower == "qt_attribution.json"
                    or "LICENSES" in path.parts
                ):
                    stream = source.extractfile(member)
                    if stream is not None:
                        target = notices / path
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with target.open("wb") as output:
                            shutil.copyfileobj(stream, output)
        marker.write_text(digest + "\n", encoding="utf-8")
    serial = notices / "pyserial-LICENSE.txt"
    if not serial.exists():
        with urllib.request.urlopen(
            "https://raw.githubusercontent.com/pyserial/pyserial/v3.5/LICENSE.txt", timeout=30
        ) as response:
            serial.write_bytes(response.read())
    return notices, archives


if __name__ == "__main__":
    prepare()
