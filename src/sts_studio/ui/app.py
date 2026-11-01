"""Application bootstrap."""

from PySide6 import QtCore as C
from PySide6 import QtGui as G
from PySide6 import QtWidgets as Q

from .. import __version__, root
from .window import Window


def configure(app: Q.QApplication) -> None:
    app.setApplicationName("STS Studio")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(G.QIcon(str(root / "sts-studio.svg")))
    app.setStyle("Fusion")
    app.setFont(G.QFont("Noto Sans CJK JP", 9))
    app.setStyleSheet(
        "QGroupBox {font-weight:600;margin-top:8px;border:1px solid #cdd5df;border-radius:4px;padding:10px 6px 6px;} QGroupBox::title {subcontrol-origin:margin;left:8px;} QPushButton {padding:5px 8px;} QTabBar::tab {padding:8px 12px;} QMainWindow {background:#f4f6f9;}"
    )


def main(argv=None):
    import sys

    args = sys.argv if argv is None else argv
    app = Q.QApplication(args)
    configure(app)
    window = Window("--demo" in args)
    window.show()
    if "--smoke" in args:

        def close_smoke() -> None:
            window.close()

        C.QTimer.singleShot(600, close_smoke)
    return app.exec()
