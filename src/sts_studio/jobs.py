"""Single-flight worker with bounded admission and per-operation cancellation."""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from PySide6.QtCore import QObject, Signal

Work = Callable[[threading.Event], Any]


class Worker(QObject):
    done = Signal(int, object)
    failed = Signal(int, object)
    progress = Signal(object)
    trace = Signal(str, bytes)

    def __init__(self) -> None:
        super().__init__()
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sts-serial")
        self._lock = threading.Lock()
        self._active = False
        self._closed = False
        self._cancel = threading.Event()

    def submit(self, token: int, function: Work) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("worker closed")
            if self._active:
                raise RuntimeError("worker already executing an operation")
            self._active = True
            self._cancel = threading.Event()
            cancel = self._cancel
        self._pool.submit(self._run, token, function, cancel)

    def _run(self, token: int, function: Work, cancel: threading.Event) -> None:
        try:
            result = function(cancel)
        except Exception as error:
            with self._lock:
                self._active = False
            self.failed.emit(token, error)
        else:
            with self._lock:
                self._active = False
            self.done.emit(token, result)

    def cancel_current(self) -> None:
        with self._lock:
            self._cancel.set()

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._cancel.set()
        self._pool.shutdown(wait=False, cancel_futures=True)
