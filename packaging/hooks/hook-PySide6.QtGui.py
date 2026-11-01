"""Keep Qt's PDF image plugin out of the desktop bundle."""

from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
binaries = [(source, target) for source, target in binaries if "qpdf" not in Path(source).name.lower()]
