"""Single owner of connection identity and unconfirmed actuator state."""

from dataclasses import dataclass, field

from ..contracts import Snapshot
from ..service import Service


@dataclass
class Session:
    service: Service | None = None
    current: int | None = None
    snapshot: Snapshot | None = None
    closing: bool = False
    adapter_mode: int | None = 1
    commanded: set[int] = field(default_factory=set)
    uncertain: set[int] = field(default_factory=set)
    off_attempt: list[int] = field(default_factory=list)

    def require_service(self) -> Service:
        if self.service is None:
            raise RuntimeError("接続されていません")
        return self.service

    def require_id(self) -> int:
        if self.current is None:
            raise RuntimeError("サーボが選択されていません")
        return self.current
