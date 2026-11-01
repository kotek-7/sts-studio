# Release builds

Build on the target operating system with Python 3.12. Linux packages target Ubuntu 24.04. macOS builds use `MACOSX_DEPLOYMENT_TARGET=14.0` and separate arm64 and x86_64 runners. Windows builds target x86_64.

```sh
uv sync --locked
uv run --locked python tools/check.py
uv run --locked python tools/package.py --source
uv run --locked python tools/smoke_bundle.py
```

The source archive uses tracked files from `git ls-files`; stage new files before building it. Build output is under `dist/`, intermediate files under `work/package/`. Folder bundles keep shared libraries accessible for replacement. `pyproject.toml` is the application version source.

When updating PySide, also update the Qt/PySide source URLs and hashes in `tools/dependency_sources.py`. The package step checks that source and binary versions match. The Qt PDF image plugin is excluded; do not add GPL-only Qt modules to the MIT application bundle.

For a release, update the version, changelog, and `packaging/release-notes.md`; regenerate reference documents and screenshots when needed. Merge to main and wait for Checks to pass. Create and push the matching `v<version>` tag from that commit.

The tag workflow reruns the checks and native builds, downloads the corresponding dependency source archives, and uploads all assets to a draft GitHub Release. It publishes only after every required file and checksum is present. Existing releases are not overwritten. A failed upload leaves a draft for inspection; remove that incomplete draft before rerunning the release job. Do not move a published tag.

Windows executables are unsigned. macOS apps use ad-hoc signatures, without Developer ID or notarization. No signing secrets are required. Binary smoke tests run with a virtual bus and do not access physical devices.

## 日本語

対象OS上でビルドします。`pyproject.toml`のバージョン、変更履歴、Release本文を更新し、mainのCI成功後に対応する`v<version>`タグをpushします。全OSの検査・ビルドと依存ソースの取得が成功すると、成果物をdraftへ登録してから公開します。

ソースアーカイブはGitの追跡対象から作るため、新しいファイルは先にstageしてください。公開済みタグの移動・成果物の上書きはしません。失敗で残ったdraftは内容を確認して削除してから再実行します。
