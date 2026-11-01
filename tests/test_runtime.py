"""Admission, cancellation, and completion contracts independent of servo hardware."""

import threading

import pytest
from PyQt5.QtCore import QObject, pyqtSignal

from sts_studio.jobs import Worker
from sts_studio.runtime.executor import Executor, JobKind


class ControlledWorker(QObject):
    done = pyqtSignal(int, object)
    failed = pyqtSignal(int, object)

    def __init__(self):
        super().__init__()
        self.token = None
        self.cancelled = False
        self.closed = False

    def submit(self, token, function):
        self.token = token

    def cancel_current(self):
        self.cancelled = True

    def close(self):
        self.closed = True


@pytest.fixture
def execution(qapp):
    worker = ControlledWorker()
    executor = Executor(worker)
    yield executor, worker
    executor.close()


def test_monitor_keeps_interactive_state_and_serializes_actions(execution):
    executor, worker = execution
    values = []
    assert executor.submit("FB", lambda cancel: None, kind=JobKind.MONITOR)
    assert executor.interactive
    assert not executor.submit("write", lambda cancel: None)
    assert executor.defer_ui(lambda: values.append("clicked"))
    assert not executor.run_pending()
    worker.done.emit(worker.token, None)
    assert executor.run_pending()
    assert values == ["clicked"]


def test_foreground_operation_is_not_interactive(execution):
    executor, worker = execution
    executor.submit("save", lambda cancel: None)
    assert not executor.interactive
    worker.done.emit(worker.token, None)
    assert executor.interactive


def test_waiting_actions_have_a_limit_and_stop_discards_them(execution):
    executor, worker = execution
    notices = []
    executor.message.connect(notices.append)
    executor.submit("FB", lambda cancel: None, kind=JobKind.MONITOR)
    for _ in range(100):
        executor.defer_ui(lambda: None)
    assert len(executor.pending_ui) == 32
    assert notices
    executor.discard_pending()
    executor.cancel_current()
    worker.done.emit(worker.token, None)
    assert worker.cancelled
    assert not executor.run_pending()


def test_duplicate_old_completion_does_not_complete_new_job(execution):
    executor, worker = execution
    results = []
    executor.submit("first", lambda cancel: None, results.append)
    old = worker.token
    worker.done.emit(old, 1)
    executor.submit("second", lambda cancel: None, results.append)
    worker.done.emit(old, 2)
    assert executor.busy == "second"
    worker.done.emit(worker.token, 3)
    assert results == [1, 3]


def test_callback_failure_does_not_leave_executor_busy(execution):
    executor, worker = execution
    errors = []
    executor.failed.connect(lambda name, error: errors.append(str(error)))

    def fail(result):
        raise ValueError("render error")

    executor.submit("read", lambda cancel: None, fail)
    worker.done.emit(worker.token, None)
    assert errors == ["render error"]
    assert executor.submit("next", lambda cancel: None)


def test_close_rejects_new_actions(execution):
    executor, worker = execution
    executor.close()
    assert not executor.submit("write", lambda cancel: None)
    assert executor.defer_ui(lambda: pytest.fail("closed action ran"))
    assert not executor.run_pending()


def test_worker_rejects_parallel_submission_and_has_fresh_cancellation(qtbot):
    worker = Worker()
    entered = threading.Event()
    release = threading.Event()
    events = []
    worker.done.connect(lambda token, result: events.append((token, result)))

    def operation(cancel):
        entered.set()
        release.wait(2)
        return cancel.is_set()

    try:
        worker.submit(1, operation)
        assert entered.wait(1)
        with pytest.raises(RuntimeError, match="already executing"):
            worker.submit(2, operation)
        worker.cancel_current()
        release.set()
        qtbot.waitUntil(lambda: len(events) == 1)
        worker.submit(3, lambda cancel: cancel.is_set())
        qtbot.waitUntil(lambda: len(events) == 2)
        assert events == [(1, True), (3, False)]
    finally:
        release.set()
        worker.close()
