STS Studio is a FEETECH servo configuration and monitoring tool, originally built for Linux. This release adds Windows and macOS packages and moves the desktop app to PySide6.

## Downloads

| System | Package | Launch after extraction |
| --- | --- | --- |
| Ubuntu 24.04 x86_64 | `sts-studio_0.6.0_amd64.deb` | Install with apt; open STS Studio from the app menu |
| Linux x86_64 | `sts-studio-0.6.0-linux-x86_64.tar.gz` | `gui/sts-studio-gui` |
| Windows 11 x86_64 | `sts-studio-0.6.0-windows-x86_64.zip` | `gui/sts-studio-gui.exe` |
| macOS 14+, Apple silicon | `sts-studio-0.6.0-macos-arm64.zip` | `STS Studio.app` |
| macOS 14+, Intel | `sts-studio-0.6.0-macos-x86_64.zip` | `STS Studio.app` |

Binary packages include Python and Qt. Keep the complete extracted folder. The CLI is in `cli/`; the Ubuntu package also installs it as `sts-studio`.

Windows builds are unsigned. macOS builds are not Developer ID signed or notarized. Read the [installation instructions](https://github.com/kotek-7/sts-studio/blob/v0.6.0/docs/INSTALL.md) if the OS blocks the first launch. `SHA256SUMS.txt` lists package hashes.

## Changes

- Add native packages for Windows and macOS and self-contained Ubuntu packages.
- Replace PyQt5 with PySide6.
- Add MIT licensing, dependency notices, and English/Japanese documentation.

CLI arguments, JSON output, and servo commands are unchanged. The interface still uses Japanese and English labels. Firmware flashing is not available.

Choose demo mode to explore the app without a servo. Live slider changes send commands when connected. STOP requests torque OFF but does not clear Reg Write commands stored on the servo.

## 日本語

Linux用のFEETECHデバッグツールとして開発したSTS Studioに、Windows・macOS向け配布を追加しました。GUIをPySide6へ移行し、自作部分をMITライセンスで公開しています。

上の表からOS・CPUに合うファイルを選び、フォルダー全体を展開してください。[日本語の導入手順](https://github.com/kotek-7/sts-studio/blob/v0.6.0/docs/INSTALL.ja.md)に起動方法と未署名アプリの注意点を記載しています。実機なしで試す場合はデモモードを使えます。
