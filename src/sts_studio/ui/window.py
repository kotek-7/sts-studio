"""Desktop composition and cross-feature coordination."""

from __future__ import annotations

import time

from PyQt5 import QtCore as C
from PyQt5 import QtWidgets as Q

from ..jobs import Worker
from ..runtime.executor import Executor, JobKind
from ..runtime.session import Session
from .connection import ConnectionController
from .diagnostics import DiagnosticsController
from .monitoring import MonitoringController
from .motion import MotionController
from .programming import ProgrammingController
from .pwm import PwmController
from .state import ServoCommand
from .view import DesktopView
from .widgets import required


class Window(DesktopView):
    def __init__(self, demo: bool = False) -> None:
        super().__init__()
        self.setWindowTitle("STS Studio")
        self.resize(1240, 900)
        self.session = Session()
        self.worker = Worker()
        self.executor = Executor(self.worker, self)
        self.connections = ConnectionController(self)
        self.programming = ProgrammingController(self)
        self.motion = MotionController(self)
        self.monitoring = MonitoringController(self)
        self.diagnostics = DiagnosticsController(self)
        self.pwm = PwmController(self)
        self.motion_buttons: list[Q.QPushButton] = []
        self.device_buttons: list[Q.QPushButton] = []
        self.build_ui(demo)
        self.executor.changed.connect(self.update_controls)
        self.executor.settled.connect(self.finish_job)
        self.executor.failed.connect(self.job_failed)
        self.executor.message.connect(self.note)
        self.worker.progress.connect(self.connections.scan_progress)
        self.worker.trace.connect(self.trace)
        self.timer = C.QTimer(self)
        self.timer.setTimerType(C.Qt.TimerType.PreciseTimer)
        self.timer.setInterval(2)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.tabs.currentChanged.connect(self.tab_changed)
        self.connections.ports()
        self.update_controls()
        self.note("ポートを開いて検索してください。接続だけではサーボ指令を送りません。")
        if demo:
            C.QTimer.singleShot(0, self.connections.toggle_connection)

    def note(self, text):
        required(self.statusBar()).showMessage(text)
        if hasattr(self, "log"):
            self.log.appendPlainText(time.strftime("%H:%M:%S") + " " + text)

    def notice(self, text):
        Q.QMessageBox.information(self, "STS Studio", text)

    def trace(self, kind, raw):
        if self.packet_logging.isChecked():
            self.log.appendPlainText(kind + " " + raw.hex(" ").upper())

    def ids(self):
        return sorted((int(i.text(0)) for i in self.servos.selectedItems()))

    def update_controls(self):
        connected = self.session.service is not None
        idle = self.executor.interactive
        ready = (
            connected
            and self.session.current is not None
            and bool(self.session.require_service().servos.get(self.session.require_id()))
            and (self.session.require_service().servos[self.session.current].profile is not None)
        )
        for w in [self.port, self.refresh, self.baud, self.parity, self.timeout, self.demo]:
            w.setEnabled(not connected and idle)
        self.connection.setEnabled(idle and (not self.motion.auto))
        self.connection.setText("Close / 切断" if connected else "Open / 接続")
        self.search.setEnabled(
            connected and (idle or self.executor.busy == "検索") and (not self.motion.auto)
        )
        self.search.setText("Stop / 検索中止" if self.executor.busy == "検索" else "Search / 検索")
        for w in [self.servos, self.identify_button, self.direct_id, self.first, self.last]:
            w.setEnabled(connected and idle and (not self.motion.auto))
        for w in self.motion_buttons:
            w.setEnabled(
                ready
                and idle
                and (not self.motion.auto)
                and (not self.diagnostics.test_active)
                and self.session.require_service()
                .get(self.session.require_id())
                .require_profile()
                .motion_supported
                if ready
                else False
            )
        for w in self.device_buttons:
            w.setEnabled(
                ready
                and idle
                and (not self.motion.auto)
                and (not self.diagnostics.test_active)
                and self.session.require_service()
                .get(self.session.require_id())
                .require_profile()
                .programmable
                if ready
                else False
            )
        self.torque.setEnabled(
            ready
            and idle
            and (not self.motion.auto)
            and bool(
                self.session.require_service()
                .get(self.session.require_id())
                .require_profile()
                .data["torque_address"]
            )
            if ready
            else False
        )
        self.off.setEnabled(connected)
        self.monitor.setEnabled(ready)
        self.export_button.setEnabled(ready or self.monitoring.capture is not None)
        self.test_button.setEnabled(
            ready and (not self.motion.auto) and (idle or self.diagnostics.test_active)
        )
        for w in [self.pwm_mode, self.bus_mode] + self.pwm_buttons:
            w.setEnabled(connected and idle and (not self.motion.auto))
        state = (
            "DISCONNECTED"
            if not connected
            else "AUTO"
            if self.motion.auto
            else "TESTING"
            if self.diagnostics.test_active
            else "BUSY"
            if not idle
            else "READY"
            if ready
            else "CONNECTED"
        )
        self.state_label.setText(("DEMO / " if self.demo.isChecked() else "") + state)

    def job_failed(self, name, error):
        self.note(name + ": " + str(error))
        if name == "監視":
            self.monitoring.failures += 1
            self.health.setText("通信途絶 / 表示値は過去の値（再試行中）")
        else:
            self.monitoring.next_poll = time.monotonic() + self.period.value() / 1000
        self.motion.cancel_auto(silent=True)
        if name == "通信試験":
            self.diagnostics.test_active = False
            self.diagnostics.stats.add(0, 0, "error")
            self.test_button.setText("Test / 開始")
        if name == "モード切替":
            self.session.adapter_mode = None
            self.note("モード切替失敗。再度タブを選択してください")
        if name == "トルクOFF":
            self.health.setText("トルクOFF未確認 — 接続・電源を確認")
            self.session.uncertain.update(self.session.off_attempt)

    def finish_job(self):
        if self.session.service:
            self.baud.setCurrentText(str(self.session.require_service().link.baud))
        self.update_controls()
        if self.session.closing:
            if self.motion.pending_off or self.motion.pending_pwm_off:
                self.tick()
            else:
                self.close()
        else:
            C.QTimer.singleShot(0, self.tick)

    def tab_changed(self, index):
        self.motion.cancel_auto(silent=True)
        self.diagnostics.test_active = False
        self.test_button.setText("Test / 開始")
        self.motion.pending_manual = None
        if self.session.service:
            self.motion.pending_mode = 0 if index == 3 else 1
        self.monitoring.next_poll = 0
        self.update_controls()

    def tick(self):
        now = time.monotonic()
        if self.monitoring.capture and now >= self.monitoring.capture["flush_at"]:
            try:
                self.monitoring.capture["recorder"].flush()
                self.monitoring.capture["flush_at"] = now + self.monitoring.capture["interval"]
            except Exception as e:
                self.note("記録保存失敗（データ保持）: " + str(e))
                self.monitoring.capture = None
                self.export_button.setText("Export / 記録")
        if self.executor.busy or not self.session.service:
            return
        if self.motion.pending_pwm_off:
            self.motion.pending_pwm_off = False
            self.executor.submit(
                "PWM出力OFF",
                lambda cancel: self.session.require_service().pwm("enable", 0),
                self.note,
            )
            return
        if self.motion.pending_mode is not None:
            mode = self.motion.pending_mode
            self.motion.pending_mode = None

            def switched(_):
                self.session.adapter_mode = mode
                self.monitoring.next_poll = 0

            self.executor.submit(
                "モード切替",
                lambda cancel: self.session.require_service().pwm("mode", mode),
                switched,
            )
            return
        if self.motion.pending_off:
            if self.session.adapter_mode == 0:
                self.motion.pending_mode = 1
                return
            ids = self.motion.pending_off
            self.motion.pending_off = []
            self.motion.torque_off(ids)
            return
        if self.session.closing:
            self.close()
            return
        if self.executor.run_pending():
            return
        if self.session.adapter_mode is None:
            return
        if self.motion.pending_manual is not None:
            command = self.motion.pending_manual
            self.motion.pending_manual = None
            if isinstance(command, ServoCommand):
                self.motion.dispatch_control(command.args)
            else:
                self.executor.submit(
                    "PWM送信",
                    lambda cancel: self.session.require_service().pwm("pulse", command.value),
                    self.note,
                )
            return
        if self.motion.auto and now >= self.motion.auto["next"]:
            self.motion.auto_tick()
            return
        if self.diagnostics.test_active and now >= self.diagnostics.next_test:
            self.diagnostics.test_tick()
            return
        if self.session.adapter_mode != 1 or self.tabs.currentIndex() not in (0, 1):
            return
        if (
            self.monitor.isChecked()
            and self.session.current is not None
            and (now >= self.monitoring.next_poll)
        ):
            self.monitoring.next_poll = now + self.period.value() / 1000
            if (
                self.tabs.currentIndex() == 1
                and self.session.require_service()
                .get(self.session.require_id())
                .require_profile()
                .programmable
            ):
                self.executor.submit(
                    "監視",
                    lambda cancel: self.session.require_service().snapshot(
                        self.session.require_id()
                    ),
                    self.programming.show_memory,
                    True,
                    kind=JobKind.MONITOR,
                )
            else:
                self.executor.submit(
                    "監視",
                    lambda cancel: self.session.require_service().feedback(
                        self.session.require_id()
                    ),
                    self.monitoring.show_feedback,
                    True,
                    kind=JobKind.MONITOR,
                )

    def closeEvent(self, event):
        self.motion.cancel_auto(silent=True)
        self.diagnostics.test_active = False
        self.monitor.setChecked(False)
        self.executor.discard_pending()
        if self.executor.busy:
            self.session.closing = True
            self.executor.cancel_current()
            event.ignore()
            return
        if (
            self.session.commanded
            or self.session.uncertain
            or (self.session.service and self.session.require_service().pending)
        ):
            text = "トルクON・停止未確認・登録指令のいずれかが残っています。\nSTOPで確認してから終了することを推奨します。このまま終了しますか？"
            if (
                Q.QMessageBox.question(
                    self,
                    "終了",
                    text,
                    Q.QMessageBox.Yes | Q.QMessageBox.Cancel,
                    Q.QMessageBox.Cancel,
                )
                != Q.QMessageBox.Yes
            ):
                self.session.closing = False
                event.ignore()
                return
        self.monitoring.capture_finish()
        self.motion.pending_manual = None
        self.timer.stop()
        if self.session.service:
            self.session.require_service().link.close()
        self.executor.close()
        event.accept()
