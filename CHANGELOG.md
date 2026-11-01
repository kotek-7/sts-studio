# Changelog

## 0.6.1

- Correct source CLI and native packaging instructions.
- Clarify the architecture reference and PWM tab-switching behavior.
- Include the changelog, contribution guide, and security contact in all platform packages so bundled documentation links resolve.

## 0.6.0

- Add Windows and macOS bundles alongside the Ubuntu package. Bundles include Python and Qt, with separate GUI and CLI launchers.
- Move the desktop interface from PyQt5 to PySide6.
- Publish STS Studio under the MIT license, with separate dependency notices.
- Add English and Japanese installation guides and demo screenshots.

The CLI arguments, JSON output, register formats, and servo commands are unchanged.

## 0.5.0

- Add a headless JSON CLI for discovery, feedback, register access, motion, backup, and restore.

## 0.4.0

- Separate desktop workflows from communication and execution state.
- Add uv dependency locking, type checks, and GUI interaction tests.
