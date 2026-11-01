"""Capture the demo window for the README; never open a physical port."""

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6 import QtTest, QtWidgets

from sts_studio.ui.app import configure
from sts_studio.ui.window import Window

app = QtWidgets.QApplication([])
configure(app)
window = Window(True)
window.show()


def wait(predicate, seconds=5):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtTest.QTest.qWait(10)
        if predicate():
            return
    raise RuntimeError("Demo did not reach the requested state")


wait(lambda: window.session.service is not None and not window.executor.busy)
window.last.setValue(3)
window.search.click()
wait(lambda: window.servos.topLevelItemCount() == 2 and not window.executor.busy)
window.identify_button.click()
wait(lambda: window.session.current == 1 and not window.executor.busy)
window.window_s.setValue(10)
window.torque.click()
wait(lambda: not window.executor.busy)
window.start_value.setValue(1400)
window.end_value.setValue(2700)
window.sweep_delay.setValue(1600)
window.speed.setValue(700)
window.motion.begin_auto(False)
QtTest.QTest.qWait(9000)
window.motion.cancel_auto(silent=True)
window.off.click()
wait(lambda: not window.executor.busy and not window.motion.pending_off)
output = Path(__file__).resolve().parents[1] / "docs/images"
output.mkdir(exist_ok=True)
assert window.grab().save(str(output / "demo-monitor.png"))
window.tabs.setCurrentIndex(1)
wait(lambda: window.memory.rowCount() > 0 and not window.executor.busy)
QtTest.QTest.qWait(100)
assert window.grab().save(str(output / "demo-registers.png"))
window.monitor.setChecked(False)
wait(lambda: not window.executor.busy)
window.close()
