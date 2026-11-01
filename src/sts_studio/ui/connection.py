"""Connection workflows and their local state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6 import QtCore as C
from PySide6 import QtWidgets as Q
from serial.tools import list_ports

from ..runtime.executor import JobKind
from ..service import Service
from ..simulator import VirtualLink
from ..wire import SerialLink
from .widgets import required

if TYPE_CHECKING:
    from .window import Window


class ConnectionController:
    def __init__(self, ui: Window) -> None:
        self.ui = ui

    def ports(self):
        previous = self.ui.port.currentData()
        self.ui.port.clear()
        for p in sorted(list_ports.comports(), key=lambda x: x.device):
            self.ui.port.addItem(f"{p.device} · {p.description}", p.device)
        idx = self.ui.port.findData(previous)
        if idx >= 0:
            self.ui.port.setCurrentIndex(idx)

    def toggle_connection(self):
        if self.ui.executor.defer_ui(lambda: self.toggle_connection()):
            return
        if self.ui.session.service:
            if (
                self.ui.session.commanded
                or self.ui.session.uncertain
                or self.ui.session.require_service().pending
            ):
                self.ui.notice(
                    "切断前にSTOPでトルクOFFを確認してください。登録済み指令は外部Actionで実行される可能性があります。"
                )
                return
            self.ui.monitor.setChecked(False)
            self.ui.diagnostics.test_active = False
            self.ui.monitoring.capture_finish()
            self.ui.motion.pending_manual = None
            self.ui.motion.pending_mode = None
            self.ui.motion.pending_pwm_off = False
            self.ui.session.require_service().link.close()
            self.ui.executor.discard_pending()
            self.ui.session.service = None
            self.ui.session.current = None
            self.ui.session.snapshot = None
            self.ui.servos.clear()
            self.ui.update_controls()
            return
        path = self.ui.port.currentData()
        demo = self.ui.demo.isChecked()
        baud = int(self.ui.baud.currentText())
        parity = self.ui.parity.currentText()
        timeout = self.ui.timeout.value()
        if not demo and (not path):
            self.ui.note("USBシリアルがありません。更新またはデモを選んでください")
            return

        def opened(link):
            self.ui.session.service = Service(link)
            self.ui.session.adapter_mode = 1
            self.ui.motion.pending_mode = 0 if self.ui.tabs.currentIndex() == 3 else None
            self.ui.note("接続しました。検索してください。")

        self.ui.executor.submit(
            "接続",
            lambda cancel: (
                VirtualLink(self.ui.worker.trace.emit)
                if demo
                else SerialLink(path, baud, parity, timeout, self.ui.worker.trace.emit)
            ),
            opened,
        )

    def scan(self):
        if self.ui.executor.defer_ui(lambda: self.scan()):
            return
        if self.ui.executor.busy == "検索":
            self.ui.executor.cancel_current()
            return
        if self.ui.session.commanded or self.ui.session.uncertain:
            self.ui.notice("検索前にSTOPでトルクOFFを確認してください")
            return
        first, last = (self.ui.first.value(), self.ui.last.value())
        if first > last:
            self.ui.note("開始IDは終了ID以下にしてください")
            return
        self.ui.monitor.setChecked(False)
        self.ui.session.current = None
        self.ui.session.snapshot = None
        self.ui.servos.clear()
        self.ui.session.require_service().servos.clear()
        self.ui.executor.submit(
            "検索",
            lambda cancel: self.ui.session.require_service().scan(
                first, last, cancel, lambda sid, s: self.ui.worker.progress.emit((sid, s))
            ),
            lambda found: self.ui.scan_status.setText(f"{len(found)} 台検出"),
        )

    def add_servo(self, s):
        existing = next(
            (
                required(self.ui.servos.topLevelItem(i))
                for i in range(self.ui.servos.topLevelItemCount())
                if int(required(self.ui.servos.topLevelItem(i)).text(0)) == s.sid
            ),
            None,
        )
        if not existing:
            existing = Q.QTreeWidgetItem(self.ui.servos)
        existing.setText(0, str(s.sid))
        existing.setText(1, s.model)
        existing.setText(2, s.firmware)
        if s.profile is None:
            existing.setToolTip(1, "未対応ファームウェア: 書き込み禁止")
        return existing

    def scan_progress(self, payload):
        sid, servo = payload
        self.ui.scan_status.setText(f"ID {sid} を確認")
        if servo:
            self.add_servo(servo)

    def identify(self):
        if self.ui.executor.defer_ui(lambda: self.identify()):
            return
        sid = self.ui.direct_id.value()
        self.ui.motion.pending_manual = None

        def selected(result):
            s, b = result
            self.ui.servos.blockSignals(True)
            self.ui.servos.clearSelection()
            item = self.add_servo(s)
            item.setSelected(True)
            self.ui.servos.setCurrentItem(item)
            self.ui.servos.blockSignals(False)
            self.ui.session.current = s.sid
            C.QTimer.singleShot(0, self.activate_selection)

        self.ui.executor.submit(
            "ID識別", lambda cancel: self.ui.session.require_service().discover(sid), selected
        )

    def selection_changed(self):
        if self.ui.executor.defer_ui(lambda: self.selection_changed()):
            return
        if self.ui.executor.busy:
            return
        ids = self.ui.ids()
        self.ui.session.current = ids[0] if ids else None
        self.ui.motion.pending_manual = None
        self.ui.session.snapshot = None
        self.ui.monitor.setChecked(False)
        self.ui.trend.rows.clear()
        self.ui.trend.update()
        self.ui.memory.setRowCount(0)
        if (
            self.ui.session.current is not None
            and self.ui.session.require_service().servos[self.ui.session.current].profile
        ):
            self.activate_selection()
        self.ui.update_controls()

    def activate_selection(self):
        if self.ui.session.current is None:
            return
        p = self.ui.session.require_service().servos[self.ui.session.current].profile
        if not p:
            return
        self.ui.slider.blockSignals(True)
        self.ui.slider.setRange(0, 4095 if p.family != "SCS" else 1023)
        self.ui.slider.blockSignals(False)
        self.ui.end_value.setValue(self.ui.slider.maximum())
        self.ui.monitor.setChecked(True)
        self.ui.monitoring.next_poll = 0
        self.ui.trend.position_max = 4096 / p.position_divisor
        self.ui.trend.speed_multiplier = p.speed_multiplier
        if self.ui.tabs.currentIndex() == 1 and p.programmable:
            self.ui.programming.read_memory()
        else:
            self.ui.executor.submit(
                "監視",
                lambda cancel: self.ui.session.require_service().feedback(
                    self.ui.session.require_id()
                ),
                self.ui.monitoring.show_feedback,
                True,
                kind=JobKind.MONITOR,
            )
