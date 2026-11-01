"""A release cannot publish incomplete or corrupted multi-platform assets."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "publish_release", Path(__file__).resolve().parents[1] / "tools/publish_release.py"
)
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)


@pytest.fixture
def release(tmp_path, monkeypatch):
    monkeypatch.setattr(publish, "ROOT", tmp_path)
    monkeypatch.setenv("RELEASE_TAG", "v0.6.0")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.6.0"\n')
    assets = tmp_path / "release-assets"
    assets.mkdir()
    names = {
        "linux-x86_64": [
            "sts-studio-0.6.0-linux-x86_64.tar.gz",
            "sts-studio_0.6.0_amd64.deb",
            "sts-studio-0.6.0-source.tar.gz",
            "qt-everywhere-src-6.12.0.tar.xz",
            "pyside-setup-everywhere-src-6.12.0.tar.xz",
        ],
        "windows-x86_64": ["sts-studio-0.6.0-windows-x86_64.zip"],
        "macos-arm64": ["sts-studio-0.6.0-macos-arm64.zip"],
        "macos-x86_64": ["sts-studio-0.6.0-macos-x86_64.zip"],
    }
    for target, files in names.items():
        rows = []
        for name in files:
            content = name.encode()
            (assets / name).write_bytes(content)
            rows.append(f"{hashlib.sha256(content).hexdigest()}  {name}\n")
        (assets / f"SHA256SUMS-{target}.txt").write_text("".join(rows))
    calls = []
    monkeypatch.setattr(publish.subprocess, "run", lambda command, **kwargs: calls.append(command))
    return assets, calls


def test_release_publishes_only_after_upload(release):
    assets, calls = release
    publish.main()
    assert calls[0][:3] == ["gh", "release", "create"]
    assert "--draft" in calls[0]
    assert calls[1] == ["gh", "release", "edit", "v0.6.0", "--draft=false", "--latest"]
    assert len((assets / "SHA256SUMS.txt").read_text().splitlines()) == 8


def test_release_rejects_missing_platform(release):
    assets, calls = release
    (assets / "SHA256SUMS-macos-arm64.txt").unlink()
    with pytest.raises(FileNotFoundError):
        publish.main()
    assert not calls


def test_release_rejects_corruption(release):
    assets, calls = release
    (assets / "sts-studio-0.6.0-windows-x86_64.zip").write_bytes(b"damaged")
    with pytest.raises(RuntimeError, match="Checksum"):
        publish.main()
    assert not calls


def test_release_rejects_version_mismatch(release, monkeypatch):
    _, calls = release
    monkeypatch.setenv("RELEASE_TAG", "v0.7.0")
    with pytest.raises(RuntimeError, match="Tag"):
        publish.main()
    assert not calls
