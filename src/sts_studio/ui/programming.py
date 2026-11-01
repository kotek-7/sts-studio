"""Programming workflows and their local state."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PySide6 import QtCore as C
from PySide6 import QtWidgets as Q

from ..files import ParameterImage
from .widgets import required

if TYPE_CHECKING:
    from .window import Window


class ProgrammingController:
    def __init__(self, ui: Window) -> None:
        self.ui = ui

    def read_memory(self):
        if self.ui.executor.defer_ui(lambda: self.read_memory()):
            return
        if self.ui.session.current is not None:
            self.ui.executor.submit(
                "メモリ読取",
                lambda cancel: self.ui.session.require_service().snapshot(
                    self.ui.session.require_id()
                ),
                self.show_memory,
            )

    def describe_register(self):
        i = self.ui.memory.currentRow()
        if i < 0 or self.ui.session.current is None:
            return
        r = (
            self.ui.session.require_service()
            .get(self.ui.session.require_id())
            .require_profile()
            .field(int(required(self.ui.memory.item(i, 0)).text()))
        )
        self.ui.parameter_description.setText(
            f"{r.name} / address {r.address} / {r.size} byte / {r.area} / {r.access} / 範囲 {r.limits[0]}..{r.limits[1]} / 符号bit {r.sign_bit}"
        )

    def show_memory(self, result):
        self.ui.session.snapshot = result
        sid = result["id"]
        p = self.ui.session.require_service().get(sid).require_profile()
        rows = p.registers
        rebuild = (
            self.ui.memory.rowCount() != len(rows) or self.ui.memory.property("profile") != p.name
        )
        if rebuild:
            self.ui.memory.setRowCount(len(rows))
            self.ui.memory.setProperty("profile", p.name)
        for i, r in enumerate(rows):
            lo, hi = r.limits
            texts = [
                str(r.address),
                r.name,
                str(result["values"].get(r.address, "—")),
                "",
                r.area,
                r.access,
                f"{lo}..{hi}" if r.writable else "read only",
            ]
            for j, text in enumerate(texts):
                if j == 3 and (not rebuild) and (required(self.ui.memory.item(i, j)) is not None):
                    continue
                item = self.ui.memory.item(i, j)
                if item is None:
                    item = Q.QTableWidgetItem()
                    self.ui.memory.setItem(i, j, item)
                if item.text() != text:
                    item.setText(text)
                if rebuild:
                    item.setData(C.Qt.ItemDataRole.UserRole, r.address)
                    if j != 3 or not r.writable:
                        item.setFlags(item.flags() & ~C.Qt.ItemFlag(C.Qt.ItemFlag.ItemIsEditable))
        self.ui.torque.blockSignals(True)
        self.ui.torque.setChecked(bool(result["values"].get(40, 0)))
        self.ui.torque.blockSignals(False)
        if result["values"].get(40) == 0:
            self.ui.session.commanded.discard(sid)
        self.ui.monitoring.show_feedback(
            dict(
                id=sid,
                values=result["values"],
                error=result["error"],
                timestamp=time.time(),
                goal=result.get("goal"),
            )
        )

    def save_parameter(self):
        if self.ui.executor.defer_ui(lambda: self.save_parameter()):
            return
        i = self.ui.memory.currentRow()
        if i < 0:
            return
        address = int(required(self.ui.memory.item(i, 0)).text())
        try:
            value = int(required(self.ui.memory.item(i, 3)).text())
            r = (
                self.ui.session.require_service()
                .get(self.ui.session.require_id())
                .require_profile()
                .field(address)
            )
            r.pack(
                value,
                self.ui.session.require_service()
                .get(self.ui.session.require_id())
                .require_profile()
                .order,
            )
        except Exception as e:
            self.ui.note(str(e))
            return
        if (
            Q.QMessageBox.question(
                self.ui,
                "設定保存",
                f"ID {self.ui.session.current} / {r.name}\n{required(self.ui.memory.item(i, 2)).text()} → {value}\n書き込みますか？",
                Q.QMessageBox.StandardButton.Yes | Q.QMessageBox.StandardButton.Cancel,
                Q.QMessageBox.StandardButton.Cancel,
            )
            != Q.QMessageBox.StandardButton.Yes
        ):
            return
        sid = self.ui.session.require_id()
        if address in (40, 41, 42, 44, 46) and (not (address == 40 and value == 0)):
            self.ui.session.commanded.add(sid)

        def write(cancel):
            new = self.ui.session.require_service().write_register(sid, address, value)
            return (new, self.ui.session.require_service().snapshot(new))

        def done(result):
            new, snapshot = result
            self.ui.session.current = new
            for j in range(self.ui.servos.topLevelItemCount()):
                item = required(self.ui.servos.topLevelItem(j))
                if int(item.text(0)) == sid:
                    item.setText(0, str(new))
            if address == 40 and value == 0:
                self.ui.motion.torque_done([new], False)
            self.show_memory(snapshot)

        self.ui.executor.submit("設定保存", write, done)

    def save_image(self):
        if self.ui.executor.defer_ui(lambda: self.save_image()):
            return
        if (
            self.ui.session.require_service()
            .get(self.ui.session.require_id())
            .require_profile()
            .family
            != "STS"
        ):
            self.ui.notice("xdat設定ファイルはSTSに対応しています")
            return
        path, _ = Q.QFileDialog.getSaveFileName(
            self.ui, "Save xdat", "servo.xdat", "STS parameters (*.xdat)"
        )
        if not path:
            return

        def done(result):
            ParameterImage(0, result["raw"][:40]).save(path)
            self.ui.note("xdat保存: " + path)

        self.ui.executor.submit(
            "設定ファイル保存",
            lambda cancel: self.ui.session.require_service().snapshot(self.ui.session.require_id()),
            done,
        )

    def load_image(self):
        if self.ui.executor.defer_ui(lambda: self.load_image()):
            return
        path, _ = Q.QFileDialog.getOpenFileName(self.ui, "Load xdat", "", "STS parameters (*.xdat)")
        if not path:
            return
        try:
            image = ParameterImage.load(path)
        except Exception as e:
            self.ui.note(str(e))
            return

        def preview(result):
            self.ui.session.snapshot = result
            try:
                changes = image.changes(
                    self.ui.session.require_service().get(self.ui.session.require_id()),
                    result["values"],
                )
            except Exception as e:
                self.ui.note(str(e))
                return
            dialog = Q.QDialog(self.ui)
            dialog.setWindowTitle("復元する差分を選択")
            dialog.resize(620, 440)
            layout = Q.QVBoxLayout(dialog)
            table = Q.QTableWidget(len(changes), 4)
            table.setHorizontalHeaderLabels(["適用", "項目", "現在", "復元値"])
            required(table.horizontalHeader()).setSectionResizeMode(
                1, Q.QHeaderView.ResizeMode.Stretch
            )
            for i, (a, v) in enumerate(changes):
                check = Q.QTableWidgetItem()
                check.setFlags(
                    C.Qt.ItemFlag(C.Qt.ItemFlag.ItemIsEnabled)
                    | C.Qt.ItemFlag(C.Qt.ItemFlag.ItemIsUserCheckable)
                )
                check.setCheckState(
                    C.Qt.CheckState.Unchecked if a in (5, 6) else C.Qt.CheckState.Checked
                )
                table.setItem(i, 0, check)
                for j, text in enumerate(
                    [
                        self.ui.session.require_service()
                        .get(self.ui.session.require_id())
                        .require_profile()
                        .field(a)
                        .name,
                        str(result["values"][a]),
                        str(v),
                    ],
                    1,
                ):
                    item = Q.QTableWidgetItem(text)
                    item.setFlags(C.Qt.ItemFlag.ItemIsEnabled)
                    table.setItem(i, j, item)
            layout.addWidget(table)
            layout.addWidget(
                Q.QLabel("EEPROM復元はトルクOFFで実行。ID/通信速度は初期選択から除外。")
            )
            buttons = Q.QDialogButtonBox(
                Q.QDialogButtonBox.StandardButton.Ok | Q.QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            if dialog.exec() == Q.QDialog.DialogCode.Accepted:
                selected = [
                    pair
                    for i, pair in enumerate(changes)
                    if required(table.item(i, 0)).checkState() == C.Qt.CheckState.Checked
                ]
                selected.sort(key=lambda pair: (pair[0] in (5, 6), pair[0]))
                sid = self.ui.session.require_id()

                def done(r):
                    self.ui.session.current = r["id"]
                    self.ui.servos.blockSignals(True)
                    self.ui.servos.clear()
                    for servo in self.ui.session.require_service().servos.values():
                        item = self.ui.connections.add_servo(servo)
                        if servo.sid == self.ui.session.current:
                            item.setSelected(True)
                    self.ui.servos.blockSignals(False)
                    self.ui.note(str(r))
                    C.QTimer.singleShot(0, self.read_memory)

                def restore_selected() -> None:
                    self.ui.executor.submit(
                        "設定復元",
                        lambda cancel: self.ui.session.require_service().restore(
                            sid, selected, cancel
                        ),
                        done,
                    )

                C.QTimer.singleShot(0, restore_selected)

        self.ui.executor.submit(
            "復元前読取",
            lambda cancel: self.ui.session.require_service().snapshot(self.ui.session.require_id()),
            preview,
        )

    def recovery(self):
        if self.ui.executor.defer_ui(lambda: self.recovery()):
            return
        sid = self.ui.session.require_id()
        if (
            Q.QMessageBox.warning(
                self.ui,
                "Recovery",
                f"ID {sid} に初期化指令を送信します。設定が失われる可能性があります。\n復帰先ID・通信速度と完了状態は保証できません。続けますか？",
                Q.QMessageBox.StandardButton.Yes | Q.QMessageBox.StandardButton.Cancel,
                Q.QMessageBox.StandardButton.Cancel,
            )
            != Q.QMessageBox.StandardButton.Yes
        ):
            return
        self.ui.monitor.setChecked(False)

        def done(message):
            self.ui.session.current = None
            self.ui.session.snapshot = None
            self.ui.servos.clear()
            self.ui.notice(message)

        self.ui.executor.submit(
            "Recovery送信", lambda cancel: self.ui.session.require_service().reset(sid), done
        )

    def calibrate(self):
        if self.ui.executor.defer_ui(lambda: self.calibrate()):
            return
        if (
            Q.QMessageBox.question(
                self.ui,
                "中点校正",
                "現在位置を2048に校正します。基準位置とトルクOFFを確認してください。",
                Q.QMessageBox.StandardButton.Yes | Q.QMessageBox.StandardButton.Cancel,
                Q.QMessageBox.StandardButton.Cancel,
            )
            == Q.QMessageBox.StandardButton.Yes
        ):
            self.ui.executor.submit(
                "中点校正",
                lambda cancel: self.ui.session.require_service().calibration(
                    self.ui.session.require_id()
                ),
                lambda _: C.QTimer.singleShot(0, self.read_memory),
            )
