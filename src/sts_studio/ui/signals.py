"""Explicit Qt clicked(bool) boundary; no callable-signature inspection."""

import logging
from collections.abc import Callable

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QAbstractButton


class ClickAction(QObject):
    failed = pyqtSignal(str)

    def __init__(self, button: QAbstractButton, callback: Callable[[], object]) -> None:
        super().__init__(button)
        self._callback = callback
        button.clicked.connect(self.trigger)

    @pyqtSlot(bool)
    def trigger(self, checked: bool) -> None:
        try:
            self._callback()
        except Exception as error:
            logging.getLogger(__name__).exception("Button action failed")
            self.failed.emit(f"操作に失敗しました: {error}")


def bind_click(
    button: QAbstractButton,
    callback: Callable[[], object],
    on_error: Callable[[str], None] | None = None,
) -> ClickAction:
    action = ClickAction(button, callback)
    if on_error is not None:
        action.failed.connect(on_error)
    return action
