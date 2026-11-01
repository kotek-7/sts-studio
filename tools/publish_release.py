"""Publish a complete, checked set of release assets; never replace a release."""

import hashlib
import os
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    tag = os.environ["RELEASE_TAG"]
    if tag != f"v{version}":
        raise RuntimeError("Tag and pyproject version differ")
    assets = ROOT / "release-assets"
    required = {
        f"sts-studio-{version}-{target}.{ext}"
        for target, ext in [
            ("linux-x86_64", "tar.gz"),
            ("windows-x86_64", "zip"),
            ("macos-arm64", "zip"),
            ("macos-x86_64", "zip"),
            ("source", "tar.gz"),
        ]
    }
    required.add(f"sts-studio_{version}_amd64.deb")
    required.update(
        {"qt-everywhere-src-6.12.0.tar.xz", "pyside-setup-everywhere-src-6.12.0.tar.xz"}
    )
    sums = {}
    for target in ("linux-x86_64", "windows-x86_64", "macos-arm64", "macos-x86_64"):
        for line in (assets / f"SHA256SUMS-{target}.txt").read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            if name in sums:
                raise RuntimeError(f"Duplicate asset: {name}")
            sums[name] = digest
    if set(sums) != required:
        raise RuntimeError(f"Unexpected asset set: {set(sums) ^ required}")
    for name, digest in sums.items():
        with (assets / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                raise RuntimeError(f"Checksum mismatch: {name}")
    checksum = assets / "SHA256SUMS.txt"
    checksum.write_text(
        "".join(f"{sums[name]}  {name}\n" for name in sorted(sums)), encoding="utf-8"
    )
    # gh release create refuses an existing release, including an incomplete draft.
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            tag,
            "--verify-tag",
            "--draft",
            "--title",
            f"STS Studio {version}",
            "--notes-file",
            str(ROOT / "packaging/release-notes.md"),
            *[str(assets / name) for name in sorted(sums)],
            str(checksum),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["gh", "release", "edit", tag, "--draft=false", "--latest"], cwd=ROOT, check=True
    )


if __name__ == "__main__":
    main()
