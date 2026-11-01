"""GUI-thread execution state, completion routing, and bounded UI admission."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from ..jobs import Work, Worker


class JobKind(Enum):
    FOREGROUND = auto()
    MONITOR = auto()


@dataclass(frozen=True)
class Job:
    token: int
    name: str
    kind: JobKind
    done: Callable[[Any], None] | None
    quiet: bool


class Executor(QObject):
    changed = pyqtSignal()
    settled = pyqtSignal()
    failed = pyqtSignal(str, object)
    message = pyqtSignal(str)

    def __init__(self, worker: Worker, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.worker = worker
        self._active: Job | None = None
        self._sequence = 0
        self._closed = False
        self.pending_ui: deque[Callable[[], None]] = deque()
        worker.done.connect(self._done)
        worker.failed.connect(self._failed)

    @property
    def busy(self) -> str | None:
        return self._active.name if self._active else None

    @property
    def monitoring(self) -> bool:
        return self._active is not None and self._active.kind is JobKind.MONITOR

    @property
    def interactive(self) -> bool:
        return not self._closed and (self._active is None or self.monitoring)

    def submit(
        self,
        name: str,
        fn: Work,
        done: Callable[[Any], None] | None = None,
        quiet: bool = False,
        *,
        kind: JobKind = JobKind.FOREGROUND,
    ) -> bool:
        if self._closed or self._active is not None:
            return False
        self._sequence += 1
        job = Job(self._sequence, name, kind, done, quiet)
        self._active = job
        self.changed.emit()
        try:
            self.worker.submit(job.token, fn)
        except Exception as error:
            self._failed(job.token, error)
            return False
        return True

    def defer_ui(self, action: Callable[[], None]) -> bool:
        if self._closed:
            return True
        if not self.monitoring:
            return False
        if len(self.pending_ui) >= 32:
            self.message.emit("処理待ちです。完了後にもう一度操作してください。")
        else:
            self.pending_ui.append(action)
        return True

    def run_pending(self) -> bool:
        if self._active or not self.pending_ui or self._closed:
            return False
        action = self.pending_ui.popleft()
        try:
            action()
        except Exception as error:
            self.failed.emit("操作", error)
        return True

    def discard_pending(self) -> None:
        self.pending_ui.clear()

    def cancel_current(self) -> None:
        self.worker.cancel_current()

    @pyqtSlot(int, object)
    def _done(self, token: int, result: Any) -> None:
        job = self._active
        if job is None or job.token != token:
            return
        self._active = None
        try:
            if job.done is not None:
                job.done(result)
            if not job.quiet:
                self.message.emit(job.name + " 完了")
        except Exception as error:
            self.failed.emit(job.name, error)
        finally:
            self.changed.emit()
            self.settled.emit()

    @pyqtSlot(int, object)
    def _failed(self, token: int, error: Exception) -> None:
        job = self._active
        if job is None or job.token != token:
            return
        self._active = None
        self.failed.emit(job.name, error)
        self.changed.emit()
        self.settled.emit()

    def close(self) -> None:
        self._closed = True
        self.discard_pending()
        self.worker.close()
