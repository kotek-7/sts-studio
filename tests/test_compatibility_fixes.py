import os
import threading
import time
import unittest

from sts_studio.runtime.executor import JobKind

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6 import QtTest
from PySide6 import QtWidgets as Q

from sts_studio.catalog import identify
from sts_studio.files import Recorder
from sts_studio.service import Service
from sts_studio.simulator import VirtualLink
from sts_studio.ui import Window

app = Q.QApplication.instance() or Q.QApplication([])


class CompatibilityFixes(unittest.TestCase):
    def wait(self, p, timeout=2):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            app.processEvents()
            QtTest.QTest.qWait(2)
            if p():
                return
        self.fail("timeout")

    def setUp(self):
        self.w = Window(True)
        self.w.show()
        self.wait(lambda: self.w.session.service is not None and (not self.w.executor.busy))
        self.w.connections.identify()
        self.wait(lambda: self.w.session.current == 1 and self.w.values[56].text() != "—")
        # Pause polling before waiting for an idle worker; READY can include a monitor job.
        self.w.monitor.setChecked(False)
        self.wait(lambda: not self.w.executor.busy)
        self.w.monitor.setChecked(True)

    def tearDown(self):
        w = self.w
        w.monitor.setChecked(False)
        w.diagnostics.test_active = False
        w.motion.cancel_auto(silent=True)
        w.motion.pending_manual = None
        self.wait(lambda: not w.executor.busy)
        w.session.commanded.clear()
        w.session.uncertain.clear()
        w.session.require_service().pending.clear()
        w.close()
        app.processEvents()

    def settle(self):
        self.wait(
            lambda: (
                not self.w.executor.busy
                and (not self.w.motion.pending_off)
                and (not self.w.motion.pending_pwm_off)
                and (self.w.motion.pending_mode is None)
                and (self.w.motion.pending_manual is None)
            )
        )

    def test_stop_keeps_feedback_and_recording(self):
        w = self.w
        with TemporaryDirectory() as folder:
            rec = Recorder(Path(folder) / "capture.txt", True)
            w.monitoring.capture_rows = []
            w.monitoring.capture = {
                "recorder": rec,
                "interval": 30,
                "flush_at": time.monotonic() + 30,
            }
            w.motion.stop_all()
            self.settle()
            self.assertTrue(w.monitor.isChecked())
            n = len(w.monitoring.capture_rows)
            self.wait(lambda: len(w.monitoring.capture_rows) > n)
            self.assertEqual(w.session.require_service().link.mem[1][40], 0)
            w.monitoring.capture_finish()

    def test_goal_is_feedback_word_not_target(self):
        w = self.w
        w.monitor.setChecked(False)
        self.settle()
        w.session.require_service().link.mem[1][67:69] = b"\x01\x80"
        w.session.require_service().link.history.clear()
        result = w.session.require_service().feedback(1)
        w.monitoring.show_feedback(result)
        self.assertEqual(result["goal"], -1)
        self.assertEqual(w.values["goal"].text(), "-1")
        self.assertEqual(len(w.session.require_service().link.history), 1)
        self.assertEqual(w.session.require_service().link.history[0][5:7], b"8\x11")

    def test_selection_does_not_read_whole_memory(self):
        w = self.w
        self.assertIsNone(w.session.snapshot)
        reads = [p for p in w.session.require_service().link.history if p[4] == 2]
        self.assertFalse(any((p[5:7] in (b"\x00(", b"(\x1f") for p in reads)))

    def test_programming_refresh_preserves_edit(self):
        w = self.w
        w.tabs.setCurrentIndex(1)
        self.wait(lambda: w.session.snapshot is not None and (not w.executor.busy))
        row = next((i for i in range(w.memory.rowCount()) if w.memory.item(i, 0).text() == "21"))
        w.memory.item(row, 3).setText("55")
        w.session.require_service().link.mem[1][21] = 44
        self.wait(lambda: w.memory.item(row, 2).text() == "44")
        self.assertEqual(w.memory.item(row, 3).text(), "55")

    def test_live_slider_and_stop_discards_waiting_target(self):
        w = self.w
        self.assertTrue(w.live.isChecked())
        w.slider.setValue(1200)
        self.wait(
            lambda: int.from_bytes(w.session.require_service().link.mem[1][42:44], "little") == 1200
        )
        w.executor.submit("待機", lambda cancel: time.sleep(0.03))
        w.slider.setValue(1600)
        w.motion.stop_all()
        self.settle()
        self.assertEqual(
            int.from_bytes(w.session.require_service().link.mem[1][42:44], "little"), 1200
        )
        self.assertIsNone(w.motion.pending_manual)

    def test_step_timer_is_independent(self):
        w = self.w
        w.period.setValue(1000)
        w.monitor.setChecked(False)
        self.settle()
        stamps = []
        w.session.require_service().link.trace = lambda direction, p: (
            stamps.append(time.monotonic()) if direction == "TX" and p[4:6] == b"\x03)" else None
        )
        w.start_value.setValue(1000)
        w.end_value.setValue(1100)
        w.step_delay.setValue(10)
        w.motion.begin_auto(True)
        self.wait(lambda: len(stamps) >= 6)
        w.motion.cancel_auto(silent=True)
        self.assertLess(stamps[5] - stamps[0], 0.3)

    def test_tab_mode_switch_and_pwm_stop(self):
        w = self.w
        w.tabs.setCurrentIndex(3)
        self.settle()
        self.assertEqual(w.session.require_service().link.adapter[9], 0)
        w.session.require_service().pwm("enable", 1)
        w.motion.stop_all()
        self.settle()
        self.assertEqual(w.session.require_service().link.adapter[35], 0)
        self.assertEqual(w.session.require_service().link.adapter[9], 0)
        w.tabs.setCurrentIndex(0)
        self.settle()
        self.assertEqual(w.session.require_service().link.adapter[9], 1)
        n = len(w.trend.rows)
        self.wait(lambda: len(w.trend.rows) > n)

    def test_fast_test_ignores_monitor_period(self):
        w = self.w
        w.period.setValue(5000)
        w.tabs.setCurrentIndex(2)
        self.settle()
        w.diagnostics.toggle_test()
        self.wait(lambda: w.diagnostics.stats.success >= 20)
        w.diagnostics.toggle_test()
        self.settle()

    def test_failed_operation_keeps_monitor(self):
        w = self.w

        def fail(cancel):
            raise ValueError("test failure")

        self.settle()
        w.executor.submit("設定保存", fail)
        self.settle()
        self.assertTrue(w.monitor.isChecked())

    def test_target_write_does_not_claim_torque_on(self):
        w = self.w
        w.motion.send()
        self.settle()
        self.assertEqual(w.session.require_service().link.mem[1][40], 0)
        self.assertFalse(w.session.commanded)

    def test_default_baud_and_search_order(self):
        self.assertEqual(self.w.baud.currentText(), "1000000")
        plain = Window(False)
        try:
            self.assertEqual(plain.baud.currentText(), "115200")
        finally:
            plain.close()
        link = VirtualLink()
        service = Service(link)
        service.scan(252, 253, threading.Event(), lambda *a: None)
        self.assertEqual([p[2] for p in link.history], [253, 252])

    def test_debug_profiles_without_memory_table(self):
        for major, minor, start in [
            (0, 25, 56),
            (0, 240, 86),
            (2, 10, 56),
            (2, 30, 56),
            (20, 0, 64),
        ]:
            model, p = identify(bytes([major, minor, 0, 9, 3, 1, 0, 0, 1]))
            self.assertIsNotNone(p)
            self.assertFalse(p.programmable)
            self.assertEqual(p.feedback_start, start)

    def test_motion_sends_no_extra_read(self):
        w = self.w
        w.monitor.setChecked(False)
        self.settle()
        for method in ["write", "sync", "registered"]:
            w.session.require_service().link.history.clear()
            w.session.require_service().control([1], 1234, 321, 17, 456, method)
            self.assertEqual(len(w.session.require_service().link.history), 1)
        w.session.require_service().link.history.clear()
        w.session.require_service().action()
        self.assertEqual(len(w.session.require_service().link.history), 1)

    def test_step_observed_sequence(self):
        from sts_studio.automation import Pattern

        pattern = Pattern(1000, 1100, 30, clamp=False)
        self.assertEqual(
            [pattern.next() for _ in range(9)],
            [1030, 1060, 1090, 1120, 1090, 1060, 1030, 1000, 1030],
        )

    def test_profile_selection_never_sends_motion(self):
        w = self.w
        w.monitor.setChecked(False)
        self.settle()
        w.goal.setValue(3000)
        w.session.require_service().link.mem[2][0:2] = bytes([0, 1])
        w.session.require_service().discover(2)
        w.session.require_service().link.history.clear()
        w.session.current = 2
        w.connections.activate_selection()
        self.settle()
        self.assertFalse(
            any(
                (
                    p[4] in (3, 4, 131) and p[2] != 253
                    for p in w.session.require_service().link.history
                )
            )
        )

    def test_hardware_status_is_not_packet_status(self):
        w = self.w
        w.monitor.setChecked(False)
        self.settle()
        w.session.require_service().link.mem[1][65] = 1
        result = w.session.require_service().feedback(1)
        self.assertEqual(result["values"][65], 1)
        self.assertEqual(result["error"], 0)

    def test_monitor_keeps_controls_and_status_stable(self):
        from PySide6 import QtCore as C

        w = self.w
        w.monitor.setChecked(False)
        self.settle()
        events = []

        class Watch(C.QObject):
            def eventFilter(self, obj, event):
                if event.type() == C.QEvent.EnabledChange:
                    events.append(obj)
                return False

        watch = Watch()
        widgets = [w.connection, w.search, w.servos, w.torque] + w.motion_buttons + w.device_buttons
        for widget in widgets:
            widget.installEventFilter(watch)
        before = w.state_label.text()
        for _ in range(3):
            w.executor.submit(
                "監視",
                lambda cancel: (time.sleep(0.02), w.session.require_service().feedback(1))[1],
                w.monitoring.show_feedback,
                True,
                kind=JobKind.MONITOR,
            )
            self.assertEqual(w.state_label.text(), before)
            self.settle()
        self.assertEqual(events, [])
        for widget in widgets:
            widget.removeEventFilter(watch)

    def test_unchanged_memory_does_not_emit_cell_changes(self):
        w = self.w
        w.monitor.setChecked(False)
        self.settle()
        snapshot = w.session.require_service().snapshot(1)
        w.programming.show_memory(snapshot)
        changes = []
        w.memory.itemChanged.connect(lambda item: changes.append((item.row(), item.column())))
        w.programming.show_memory(snapshot)
        self.assertEqual(changes, [])
        updated = dict(snapshot, values=dict(snapshot["values"]))
        updated["values"][21] += 1
        w.programming.show_memory(updated)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0][1], 2)

    def test_user_action_waits_for_monitor_and_stop_discards_it(self):
        w = self.w
        w.monitor.setChecked(False)
        self.settle()
        w.session.require_service().link.history.clear()
        w.executor.submit(
            "監視",
            lambda cancel: (time.sleep(0.03), w.session.require_service().feedback(1))[1],
            w.monitoring.show_feedback,
            True,
            kind=JobKind.MONITOR,
        )
        w.motion.torque_change(True)
        self.assertEqual(len(w.executor.pending_ui), 1)
        self.wait(lambda: not w.executor.pending_ui and (not w.executor.busy))
        self.assertEqual(w.session.require_service().link.mem[1][40], 1)
        w.executor.submit(
            "監視",
            lambda cancel: (time.sleep(0.03), w.session.require_service().feedback(1))[1],
            w.monitoring.show_feedback,
            True,
            kind=JobKind.MONITOR,
        )
        w.motion.torque_change(True)
        w.motion.stop_all()
        self.assertFalse(w.executor.pending_ui)
        self.settle()
        self.assertEqual(w.session.require_service().link.mem[1][40], 0)

    def test_open_close_via_actual_button_click(self):
        import sys

        errors = []
        previous = sys.excepthook
        sys.excepthook = lambda kind, value, tb: errors.append(str(value))
        w = Window(False)
        w.demo.setChecked(True)
        try:
            w.connection.click()
            self.assertEqual(errors, [])
            self.wait(lambda: w.session.service is not None and (not w.executor.busy))
            w.identify_button.click()
            self.assertEqual(errors, [])
            self.wait(lambda: w.session.current == 1 and (not w.executor.busy))
            w.monitor.setChecked(False)
            w.connection.click()
            self.assertEqual(errors, [])
            self.wait(lambda: w.session.service is None)
        finally:
            w.close()
            sys.excepthook = previous

    def test_decorated_qt_buttons_discard_only_unused_argument(self):
        from sts_studio.ui.signals import bind_click

        calls = []
        button = Q.QPushButton()
        button.setCheckable(True)
        bind_click(button, lambda: calls.append("clicked"))
        button.clicked.connect(lambda checked: calls.append(checked))
        button.click()
        button.click()
        self.assertEqual(calls, ["clicked", True, "clicked", False])
