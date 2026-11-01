STS Studio 0.6.1 updates the guides included in the Linux, Windows, and macOS packages.

## Downloads

| System | Package | Launch after extraction |
| --- | --- | --- |
| Ubuntu 24.04 x86_64 | `sts-studio_0.6.1_amd64.deb` | Install with apt; open STS Studio from the app menu |
| Linux x86_64 | `sts-studio-0.6.1-linux-x86_64.tar.gz` | `gui/sts-studio-gui` |
| Windows 11 x86_64 | `sts-studio-0.6.1-windows-x86_64.zip` | `gui/sts-studio-gui.exe` |
| macOS 14+, Apple silicon | `sts-studio-0.6.1-macos-arm64.zip` | `STS Studio.app` |
| macOS 14+, Intel | `sts-studio-0.6.1-macos-x86_64.zip` | `STS Studio.app` |

Binary packages include Python and Qt. Keep the complete extracted folder. The CLI is in `cli/`; the Ubuntu package also installs it as `sts-studio`.

Windows builds are unsigned. macOS builds are not Developer ID signed or notarized. Read the [installation instructions](https://github.com/kotek-7/sts-studio/blob/v0.6.1/docs/INSTALL.md) if the OS blocks the first launch. `SHA256SUMS.txt` lists package hashes.

For a source build, download `sts-studio-0.6.1-source.tar.gz`. The `qt-everywhere-src` and `pyside-setup-everywhere-src` archives contain dependency sources and are not needed to run the app.

## Changes

- Correct the source CLI examples and native build instructions.
- Include the changelog, contribution guide, and security contact linked from the bundled documentation.
- Clarify the architecture reference and PWM mode changes when switching tabs.

Application behavior and CLI output are unchanged from 0.6.0.

Choose demo mode to explore the app without a servo. Live slider changes send commands when connected. STOP requests torque OFF but does not clear Reg Write commands stored on the servo.

## 日本語

同梱ガイドを更新しました。ソースからのCLI起動例とOS別のビルド手順を修正し、設計文書とPWMタブ切替時の説明を整理しています。アプリの動作・CLI出力は0.6.0と同じです。

上の表からOS・CPUに合うファイルを選び、フォルダー全体を展開してください。[日本語の導入手順](https://github.com/kotek-7/sts-studio/blob/v0.6.1/docs/INSTALL.ja.md)に起動方法と未署名アプリの注意点を記載しています。実機なしで試す場合はデモモードを使えます。
