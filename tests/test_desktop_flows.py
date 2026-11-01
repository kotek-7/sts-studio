"""Real Qt button events and pyserial on a PTY; no physical device access."""

import os
import sys

if sys.platform == "linux":
    import pty

import pytest
from PySide6 import QtWidgets as Q

from sts_studio.runtime.executor import JobKind
from sts_studio.ui import Window


@pytest.mark.skipif(sys.platform != "linux", reason="Linux PTY integration")
def test_real_serial_open_close_via_buttons(qtbot):
    master, slave = pty.openpty()
    w = Window(False)
    qtbot.addWidget(w)
    try:
        w.port.clear()
        w.port.addItem("Test PTY", os.ttyname(slave))
        w.connection.click()
        qtbot.waitUntil(lambda: w.session.service is not None and w.executor.busy is None)
        link = w.session.service.link
        assert link.port.is_open
        w.connection.click()
        qtbot.waitUntil(lambda: w.session.service is None)
        assert not link.port.is_open
    finally:
        w.close()
        os.close(master)
        os.close(slave)


def test_search_and_parameter_save_via_buttons(qtbot, monkeypatch):
    w = Window(False)
    qtbot.addWidget(w)
    try:
        w.demo.setChecked(True)
        w.connection.click()
        qtbot.waitUntil(lambda: w.session.service is not None and w.executor.busy is None)
        w.last.setValue(3)
        w.search.click()
        qtbot.waitUntil(lambda: w.executor.busy is None and w.servos.topLevelItemCount() == 2)
        w.identify_button.click()
        qtbot.waitUntil(lambda: w.session.current == 1 and w.executor.busy is None)
        w.tabs.setCurrentIndex(1)
        qtbot.waitUntil(lambda: w.session.snapshot is not None and w.executor.busy is None)
        w.monitor.setChecked(False)
        row = next(i for i in range(w.memory.rowCount()) if w.memory.item(i, 0).text() == "21")
        w.memory.selectRow(row)
        w.memory.item(row, 3).setText("44")
        monkeypatch.setattr(
            Q.QMessageBox, "question", lambda *args: Q.QMessageBox.StandardButton.Yes
        )
        button = next(
            b for b in w.findChildren(Q.QPushButton) if b.text() == "選択した行の編集値を保存"
        )
        button.click()
        qtbot.waitUntil(lambda: w.executor.busy is None and w.session.service.link.mem[1][21] == 44)
        w.off.click()
        qtbot.waitUntil(lambda: w.executor.busy is None and not w.motion.pending_off)
        w.connection.click()
        qtbot.waitUntil(lambda: w.session.service is None)
    finally:
        w.close()


def test_disconnect_drops_other_waiting_actions(qtbot):
    import threading

    w = Window(True)
    qtbot.addWidget(w)
    release = threading.Event()
    try:
        qtbot.waitUntil(lambda: w.session.service is not None and w.executor.busy is None)
        w.executor.submit(
            "monitor", lambda cancel: release.wait(1), quiet=True, kind=JobKind.MONITOR
        )
        w.connection.click()
        called = []
        w.executor.defer_ui(lambda: called.append("stale action"))
        release.set()
        qtbot.waitUntil(lambda: w.session.service is None)
        assert not w.executor.pending_ui
        assert not called
    finally:
        release.set()
        w.close()


def test_stop_requested_before_close_finishes_before_disconnect(qtbot):
    import threading

    w = Window(True)
    qtbot.addWidget(w)
    w.show()
    release = threading.Event()
    try:
        qtbot.waitUntil(lambda: w.session.service is not None and w.executor.busy is None)
        w.identify_button.click()
        qtbot.waitUntil(lambda: w.session.current == 1 and w.executor.busy is None)
        w.monitor.setChecked(False)
        link = w.session.service.link
        link.mem[1][40] = 1
        w.session.commanded.add(1)
        w.executor.submit(
            "monitor", lambda cancel: release.wait(1), quiet=True, kind=JobKind.MONITOR
        )
        w.off.click()
        w.close()
        release.set()
        qtbot.waitUntil(lambda: not w.isVisible())
        assert link.mem[1][40] == 0
        assert not w.session.commanded
    finally:
        release.set()
        w.close()


def test_click_failure_is_reported_without_crashing_qt(qtbot):
    from sts_studio.ui.signals import bind_click

    button = Q.QPushButton()
    qtbot.addWidget(button)
    errors = []

    def fail():
        raise ValueError("invalid input")

    bind_click(button, fail, errors.append)
    button.click()
    assert errors == ["操作に失敗しました: invalid input"]
