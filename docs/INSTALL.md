# Installation

Download a binary package from [Releases](https://github.com/kotek-7/sts-studio/releases/latest). Choose x86_64 for Intel/AMD PCs, arm64 for Apple silicon Macs. Keep the whole extracted folder: the executable needs the libraries beside it. The source archive is for building the app yourself.

## Ubuntu

```sh
sudo apt install ./sts-studio_<version>_amd64.deb
sts-studio-gui --demo
sts-studio --demo scan
```

The deb installs to `/opt/sts-studio` and adds an app-menu entry. Remove it with `sudo apt remove sts-studio`.

For the tar.gz, extract it and run `./gui/sts-studio-gui`. It uses system graphics libraries. On Ubuntu 24.04, install missing libraries with:

```sh
sudo apt install libgl1 libegl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xkb1 libxkbcommon-x11-0
```

If the serial port reports permission denied, inspect its permissions with `ls -l /dev/ttyUSB0` and your groups with `id`. On Ubuntu, access usually comes through the `dialout` group. Add your user with `sudo usermod -aG dialout "$USER"`, then sign out and in. Do not run the desktop app as root.

## Windows

Extract the ZIP, then open `gui\sts-studio-gui.exe`. For the CLI, open PowerShell in the extracted folder:

```powershell
.\cli\sts-studio.exe --demo scan
```

The executable is unsigned. Windows may show an unknown-publisher or SmartScreen prompt. Confirm that the file came from this project's Release and matches its checksum before choosing to run it. Some managed PCs block unsigned programs; follow your administrator's policy. A USB serial adapter may need its manufacturer's driver.

## macOS

Extract the ZIP and open `STS Studio.app`. You can move the entire extracted folder into Applications to keep the CLI and documentation alongside the app.

The app is ad-hoc signed, without Developer ID signing or notarization. If macOS blocks it, open System Settings, Privacy & Security, and use Open Anyway for this app after checking the download source and checksum. Do not disable Gatekeeper globally. Managed Macs may prohibit this override.

Run the CLI from Terminal with `./cli/sts-studio --demo scan`. Serial adapters usually appear as `/dev/cu.*`; check the adapter manufacturer's driver instructions if no port appears.

## Checksums

Download the Release's `SHA256SUMS.txt` alongside your package. On Linux, use `sha256sum <file>`; on macOS, `shasum -a 256 <file>`; on PowerShell, `Get-FileHash <file> -Algorithm SHA256`. Compare the full digest with the matching filename in the checksum list. A checksum detects a damaged or mismatched download; it is not a publisher signature.

## Updating

For a deb, install the new file with apt. For ZIP or tar.gz packages, extract to a new folder and use its launchers. Do not mix libraries from different releases. Keep exported measurements and `.xdat` backups outside the application folder.
