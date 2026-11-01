"""Pwm workflows and their local state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..automation import Pattern
from .state import PwmPulse

if TYPE_CHECKING:
    from .window import Window


class PwmController:
    def __init__(self, ui: Window) -> None:
        self.ui = ui

    def pwm_slide(self, value):
        self.ui.pulse.setValue(value)
        if self.ui.session.service and (not self.ui.motion.auto):
            self.ui.motion.pending_manual = PwmPulse(value)
            self.ui.tick()

    def pwm_command(self, kind, value):
        if self.ui.executor.defer_ui(lambda: self.pwm_command(kind, value)):
            return
        if not self.ui.session.service:
            return
        self.ui.diagnostics.test_active = False
        if kind == "pulse":
            self.ui.pulse.setValue(value)
            self.ui.pwm_slider.blockSignals(True)
            self.ui.pwm_slider.setValue(value)
            self.ui.pwm_slider.blockSignals(False)
        self.ui.executor.submit(
            "PWM送信",
            lambda cancel: self.ui.session.require_service().pwm(kind, value),
            self.ui.note,
        )

    def begin_pwm_auto(self, step):
        try:
            pattern = Pattern(
                self.ui.pwm_min.value(),
                self.ui.pwm_max.value(),
                self.ui.pwm_step.value() if step else None,
            )
        except ValueError as e:
            self.ui.note(str(e))
            return
        self.ui.diagnostics.test_active = False
        self.ui.motion.auto = {
            "pattern": pattern,
            "pwm": True,
            "delay": self.ui.pwm_delay.value() / 1000,
            "next": 0,
        }
        self.ui.update_controls()
