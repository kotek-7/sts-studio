"""Diagnostics workflows and their local state."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from PyQt5 import QtWidgets as Q

from ..automation import CommunicationStats
from ..files import inspect_firmware
from ..wire import Timeout

if TYPE_CHECKING:
    from .window import Window


class DiagnosticsController:
    def __init__(self, ui: Window) -> None:
        self.ui = ui
        self.test_active = False
        self.stats = CommunicationStats()
        self.next_test = 0.0

    def toggle_test(self):
        self.test_active = not self.test_active
        self.next_test = 0
        self.ui.test_button.setText("Stop / 停止" if self.test_active else "Test / 開始")
        self.ui.update_controls()

    def clear_test(self):
        self.stats = CommunicationStats()
        self.ui.test_output.clear()

    def test_tick(self):
        sid = self.ui.session.require_id()

        def work(cancel):
            before = (
                self.ui.session.require_service().link.tx_bytes
                + self.ui.session.require_service().link.rx_bytes
            )
            start = time.monotonic()
            try:
                self.ui.session.require_service().feedback(sid)
                kind = "success"
            except Timeout:
                kind = "timeout"
            elapsed = time.monotonic() - start
            return (
                elapsed,
                self.ui.session.require_service().link.tx_bytes
                + self.ui.session.require_service().link.rx_bytes
                - before,
                kind,
            )

        def done(result):
            self.next_test = time.monotonic() + (0.05 if result[2] != "success" else 0)
            self.stats.add(*result)
            r = self.stats.report()
            self.ui.test_output.setPlainText(
                f"ID {sid}\n試行 {r['attempts']} / 成功 {r['success']} / Timeout {r['timeouts']}\n応答 min {r['min_us']:.0f} / mean {r['mean_us']:.0f} / max {r['max_us']:.0f} µs\n実効速度 {r['kbps']:.2f} kb/s"
            )

        self.ui.executor.submit("通信試験", work, done, True)

    def open_firmware(self):
        path, _ = Q.QFileDialog.getOpenFileName(
            self.ui, "Firmware", "", "Firmware (*.hex *.bin *.fbin *.mbin *.xbin);;All (*)"
        )
        if path:
            try:
                self.ui.firmware_output.setPlainText(
                    json.dumps(inspect_firmware(path), ensure_ascii=False, indent=2)
                    + "\n\nUpgrade転送は未対応です。"
                )
            except Exception as e:
                self.ui.firmware_output.setPlainText(str(e))
