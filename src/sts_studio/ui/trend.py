"""Telemetry plot rendering without device I/O."""

import math
from collections import deque
from typing import Any

from PySide6 import QtCore as C
from PySide6 import QtGui as G
from PySide6 import QtWidgets as Q

SERIES = {
    56: ("Position", "#172b4d"),
    "goal": ("Goal", "#2563eb"),
    60: ("Torque", "#dc2626"),
    58: ("Speed", "#16803d"),
    69: ("Current", "#0891b2"),
    63: ("Temperature", "#b45309"),
    62: ("Voltage", "#7c3aed"),
}


class Trend(Q.QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(380, 210)
        self.rows: deque[dict[Any, Any]] = deque(maxlen=100000)
        self.visible = {56, 60, 58}
        self.window_seconds = 30
        self.offset = 0
        self.bounds = None
        self.position_max = 4096
        self.speed_multiplier = 0.2

    def ranges(self):
        if not self.rows:
            return (0, 1, 0, 4095)
        end = self.rows[-1]["timestamp"] - self.offset
        start = end - self.window_seconds
        if (
            self.bounds is not None
            and all((math.isfinite(x) for x in self.bounds))
            and (self.bounds[0] < self.bounds[1])
        ):
            lo, hi = self.bounds
        else:
            lo, hi = (0, self.position_max)
        return (start, end, lo, hi)

    def paintEvent(self, event):
        p = G.QPainter(self)
        p.setRenderHint(G.QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), G.QColor("white"))
        rect = C.QRectF(57, 10, max(1, self.width() - 115), max(1, self.height() - 37))
        start, end, lo, hi = self.ranges()
        for i in range(6):
            y = rect.top() + rect.height() * i / 5
            p.setPen(G.QColor("#d7dce5"))
            p.drawLine(C.QPointF(rect.left(), y), C.QPointF(rect.right(), y))
            p.setPen(G.QColor("#5c6472"))
            p.drawText(
                C.QRectF(0, y - 10, 52, 20),
                C.Qt.AlignmentFlag.AlignRight | C.Qt.AlignmentFlag.AlignVCenter,
                f"{hi - (hi - lo) * i / 5:.0f}",
            )
            p.drawText(
                C.QRectF(rect.right() + 4, y - 10, 50, 20),
                C.Qt.AlignmentFlag.AlignLeft | C.Qt.AlignmentFlag.AlignVCenter,
                f"{1000 - 2000 * i / 5:.0f}",
            )
        if not self.rows:
            p.drawText(rect, C.Qt.AlignmentFlag.AlignCenter, "サーボを選択してモニターを開始")
            return
        p.save()
        p.setClipRect(rect)
        for key in self.visible:
            path = G.QPainterPath()
            first = True
            for r in self.rows:
                t = r["timestamp"]
                if not start <= t <= end or r.get(key) is None:
                    continue
                value = r[key] * (self.speed_multiplier if key == 58 else 1)
                bottom, top = (lo, hi) if key in (56, "goal") else (-1000, 1000)
                x = rect.left() + (t - start) / (end - start) * rect.width()
                y = rect.bottom() - (value - bottom) / (top - bottom) * rect.height()
                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)
            p.setPen(G.QPen(G.QColor(SERIES[key][1]), 1.6))
            p.drawPath(path)
        p.restore()
        p.setPen(G.QColor("#5c6472"))
        p.drawText(
            C.QRectF(rect.left(), rect.bottom() + 5, rect.width(), 20),
            C.Qt.AlignmentFlag.AlignRight,
            f"横軸 {self.window_seconds:g}秒 / 過去 {self.offset:g}秒 / 左軸:位置 / 右軸:その他",
        )
