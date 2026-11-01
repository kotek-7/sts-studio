"""Motion workflows and their local state."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PyQt5 import QtWidgets as Q

from ..automation import Pattern
from .state import AutoPlan, MotionArgs, PwmPulse, ServoCommand

if TYPE_CHECKING:
    from .window import Window


class MotionController:
    def __init__(self, ui: Window) -> None:
        self.ui = ui
        self.auto: AutoPlan | None = None
        self.pending_manual: ServoCommand | PwmPulse | None = None
        self.pending_off: list[int] = []
        self.pending_pwm_off = False
        self.pending_mode: int | None = None

    def goal_changed(self, value):
        self.ui.slider.blockSignals(True)
        self.ui.slider.setValue(max(0, min(4095, value)))
        self.ui.slider.blockSignals(False)

    def slider_changed(self, value):
        self.ui.goal.setValue(value)
        if self.ui.live.isChecked() and self.ui.session.current is not None and (not self.auto):
            self.send()

    def slider_release(self):
        pass

    def send(self):
        ids = self.ui.ids()
        if not ids or not self.ui.session.service or self.auto:
            return
        args = (
            ids,
            self.ui.goal.value(),
            self.ui.speed.value(),
            self.ui.acc.value(),
            self.ui.time_raw.value(),
            self.ui.method.currentData(),
        )
        self.pending_manual = ServoCommand(args)
        self.ui.tick()

    def dispatch_control(self, args: MotionArgs) -> None:
        ids = args[0]
        if self.ui.torque.isChecked():
            self.ui.session.commanded.update(ids)
        self.ui.executor.submit(
            "指令送信",
            lambda cancel: self.ui.session.require_service().control(*args, cancel=cancel),
        )

    def action(self):
        if self.ui.executor.defer_ui(lambda: self.action()):
            return
        if (
            Q.QMessageBox.question(
                self.ui,
                "Action",
                "バス全体の登録済み指令を実行します。続けますか？",
                Q.QMessageBox.Yes | Q.QMessageBox.Cancel,
                Q.QMessageBox.Cancel,
            )
            == Q.QMessageBox.Yes
        ):
            self.ui.executor.submit(
                "Action", lambda cancel: self.ui.session.require_service().action()
            )

    def torque_change(self, checked):
        if self.ui.executor.defer_ui(lambda: self.torque_change(checked)):
            return
        ids = self.ui.ids()
        if checked:
            self.ui.session.commanded.update(ids)
        self.ui.executor.submit(
            "トルクON" if checked else "トルクOFF",
            lambda cancel: self.ui.session.require_service().set_torque(ids, checked),
            lambda _: self.torque_done(ids, checked),
        )
        if not checked:
            self.ui.session.off_attempt = ids

    def torque_done(self, ids, enabled):
        if not enabled:
            self.ui.session.commanded.difference_update(ids)
            self.ui.session.uncertain.difference_update(ids)
        self.ui.torque.setChecked(enabled)

    def stop_all(self):
        self.cancel_auto(silent=True)
        self.ui.diagnostics.test_active = False
        self.ui.test_button.setText("Test / 開始")
        self.pending_manual = None
        self.ui.executor.discard_pending()
        self.ui.executor.cancel_current()
        if self.ui.session.adapter_mode == 0 or self.ui.tabs.currentIndex() == 3:
            self.pending_pwm_off = True
        ids = sorted(
            set(self.ui.ids())
            | self.ui.session.commanded
            | self.ui.session.uncertain
            | (self.ui.session.require_service().pending if self.ui.session.service else set())
        )
        if not ids:
            if self.pending_pwm_off:
                self.ui.tick()
            else:
                self.ui.note("停止対象がありません")
            return
        self.pending_off = ids
        self.ui.tick()

    def torque_off(self, ids):
        self.ui.session.off_attempt = ids

        def stopped(_):
            self.torque_done(ids, False)
            self.ui.health.setText("対象トルクOFF 確認済み")
            if self.ui.tabs.currentIndex() == 3:
                self.pending_mode = 0
            if self.ui.session.require_service().pending:
                self.ui.note("登録済み指令は残っています。トルクOFFを維持してください。")

        self.ui.executor.submit(
            "トルクOFF",
            lambda cancel: self.ui.session.require_service().set_torque(ids, False),
            stopped,
        )

    def begin_auto(self, step):
        if self.auto:
            self.cancel_auto()
            return
        if self.ui.method.currentData() == "registered":
            self.ui.note("自動動作はWriteまたはSync Writeを選んでください")
            return
        try:
            pattern = Pattern(
                self.ui.start_value.value(),
                self.ui.end_value.value(),
                self.ui.step_size.value() if step else None,
                clamp=False,
            )
        except ValueError as e:
            self.ui.note(str(e))
            return
        self.auto = {
            "pattern": pattern,
            "ids": self.ui.ids(),
            "speed": self.ui.speed.value(),
            "acc": self.ui.acc.value(),
            "time": self.ui.time_raw.value(),
            "method": self.ui.method.currentData(),
            "delay": (self.ui.step_delay.value() if step else self.ui.sweep_delay.value()) / 1000,
            "next": 0,
            "pwm": False,
        }
        self.ui.update_controls()
        self.ui.tick()

    def cancel_auto(self, silent=False):
        self.auto = None
        self.ui.update_controls()
        if not silent:
            self.ui.note("自動動作を停止しました（トルク状態は維持）")

    def auto_tick(self):
        a = self.auto
        if a is None:
            return
        value = a["pattern"].next()

        def done(_):
            if self.auto is a:
                a["next"] = time.monotonic() + a["delay"]

        if a["pwm"]:
            self.ui.executor.submit(
                "PWM自動",
                lambda cancel: self.ui.session.require_service().pwm("pulse", value),
                done,
                True,
            )
        else:
            self.ui.goal.setValue(value)
            self.ui.executor.submit(
                "自動動作",
                lambda cancel: self.ui.session.require_service().control(
                    a["ids"], value, a["speed"], a["acc"], a["time"], a["method"], cancel=cancel
                ),
                done,
                True,
            )
