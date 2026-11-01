"""Transport and result contracts shared by real and simulated connections."""

from collections.abc import Callable
from typing import Protocol, TypedDict

Trace = Callable[[str, bytes], None]


class Link(Protocol):
    baud: int
    tx_bytes: int
    rx_bytes: int

    def close(self) -> None: ...
    def exchange(
        self, sid: int, ins: int, params: bytes = b"", expected: int = 0, wait: bool = True
    ) -> tuple[bytes, int]: ...


class Feedback(TypedDict):
    id: int
    values: dict[int, int]
    goal: int | None
    error: int
    timestamp: float


class Snapshot(TypedDict):
    id: int
    raw: bytes
    values: dict[int, int]
    goal: int | None
    error: int


class RestoreResult(TypedDict):
    id: int
    completed: list[int]
    cancelled: bool
