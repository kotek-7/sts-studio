"""Monitoring workflows and their local state."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from PyQt5 import QtWidgets as Q

from ..files import Recorder, write_csv
from ..wire import StatusError
from .state import CaptureState

if TYPE_CHECKING:
    from .window import Window


class MonitoringController:
    def __init__(self, ui: Window) -> None:
        self.ui = ui
        self.capture: CaptureState | None = None
        self.capture_rows: list[dict[Any, Any]] = []
        self.failures = 0
        self.next_poll = 0.0

    def show_feedback(self, result):
        self.failures = 0
        row = {
            **result["values"],
            "id": result["id"],
            "timestamp": result["timestamp"],
            "error": result["error"],
            "goal": result.get("goal"),
        }
        for key, label in self.ui.values.items():
            v = row.get(key)
            label.setText("—" if v is None else f"{v / 10:.1f}" if key == 62 else str(v))
        self.ui.health.setText(
            ("トルクOFF未確認 / " if row["id"] in self.ui.session.uncertain else "")
            + ("Normal" if not row["error"] else str(StatusError(row["error"])))
            + f" / ID {row['id']} / "
            + time.strftime("%H:%M:%S")
        )
        self.ui.trend.rows.append(row)
        self.ui.trend.update()
        if self.capture:
            self.capture_rows.append(row)
            self.capture["recorder"].append(row)
            self.ui.capture_count.setText(f"{len(self.capture_rows)} rows")
            if len(self.capture_rows) >= 100000:
                self.capture_finish()

    def series_toggle(self, key, checked):
        if checked:
            self.ui.trend.visible.add(key)
        else:
            self.ui.trend.visible.discard(key)
        self.ui.trend.update()

    def plot_config(self):
        self.ui.trend.window_seconds = self.ui.window_s.value()
        self.ui.trend.offset = self.ui.offset_s.value()
        self.ui.trend.bounds = (self.ui.plot_lower.value(), self.ui.upper.value())
        self.ui.trend.update()

    def capture_toggle(self):
        if self.capture:
            self.capture_finish()
            return
        path, kind = Q.QFileDialog.getSaveFileName(
            self.ui, "記録先", "record.txt", "テキスト (*.txt);;CSV (*.csv)"
        )
        if not path:
            return
        try:
            recorder = Recorder(path, kind.startswith("テキスト"))
        except Exception as e:
            self.ui.note("記録先を開けません: " + str(e))
            return
        self.capture_rows = []
        self.capture = {
            "recorder": recorder,
            "path": path,
            "interval": self.ui.capture_seconds.value(),
            "flush_at": time.monotonic() + self.ui.capture_seconds.value(),
        }
        self.ui.capture_count.setText("0 rows")
        self.ui.export_button.setText("記録停止")
        self.ui.monitor.setChecked(True)

    def capture_finish(self):
        if not self.capture:
            return
        info = self.capture
        self.capture = None
        self.ui.export_button.setText("Export / 記録")
        try:
            info["recorder"].flush()
            self.ui.note(f"{len(self.capture_rows)}行を保存: {info['path']}")
        except Exception as e:
            self.ui.note("保存失敗（記録保持）: " + str(e))

    def save_capture(self):
        path, _ = Q.QFileDialog.getSaveFileName(
            self.ui, "現在の記録を保存", "record.csv", "CSV (*.csv)"
        )
        if path:
            try:
                write_csv(path, self.capture_rows)
                self.ui.note("保存: " + path)
            except Exception as e:
                self.ui.note(str(e))

    def clear_data(self):
        if self.capture:
            self.ui.notice("記録を停止してからEmptyを実行してください")
            return
        self.capture_rows = []
        self.ui.capture_count.setText("0 rows")
        self.ui.trend.rows.clear()
        self.ui.trend.update()
