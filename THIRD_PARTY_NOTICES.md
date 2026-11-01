# Third-party notices

STS Studio's own code is MIT licensed. The binary distributions also contain software under the licenses below. Exact versions and license texts are in the `licenses/` directory of each package.

| Component | License | Source |
| --- | --- | --- |
| Python | PSF license, with notices for bundled components | https://www.python.org/downloads/source/ |
| PySide6 Essentials and Shiboken6 | LGPL-3.0, used under that option | https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| Qt libraries | LGPL-3.0, plus component-specific notices | https://download.qt.io/official_releases/qt/ |
| pyserial | BSD-3-Clause | https://github.com/pyserial/pyserial/tree/v3.5 |
| PyInstaller bootloader | GPL with an exception permitting distribution of bundled applications | https://pyinstaller.org/en/stable/license.html |

Qt and PySide are unmodified, dynamically loaded libraries. Corresponding Qt and PySide source archives are attached to the same GitHub Release as the binary packages. The source archives include third-party copyright notices and build instructions. The application uses Qt Core, Gui and Widgets; deployment also includes the platform and image plugins needed by Qt.

You may replace these libraries with compatible modified versions and debug or reverse engineer the combined application for that purpose. In folder bundles, library files are under `gui/_internal` and `cli/_internal`; macOS uses the app's `Contents/Frameworks` and `Contents/Resources` directories. Preserve the directory structure and ABI. A changed macOS bundle may need ad-hoc signing again with `codesign --force --deep --sign - "STS Studio.app"`.

To rebuild the application with a modified PySide/Qt build, check out the release tag, install that build into the Python environment, install the other dependencies in `pyproject.toml`, and run `python tools/package.py`. Do not run `uv sync` afterward, as it would reinstall the locked wheels. See [release builds](docs/RELEASING.md).

FEETECH is the manufacturer's name. STS Studio is not affiliated with or endorsed by FEETECH. The linked Akizuki Denshi guide is reference material; it is not included in the distribution.
