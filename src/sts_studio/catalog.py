"""Register definitions, model identification, and value encoding."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from . import root as ROOT

CATALOG = json.loads((ROOT / "spec/catalog.json").read_text(encoding="utf-8"))
PROTOCOL = json.loads((ROOT / "spec/protocol.json").read_text(encoding="utf-8"))


def unsigned_word(
    value: int, order: Literal["little", "big"] = "little", sign_bit: int = -1
) -> bytes:
    if value < 0:
        if sign_bit < 0:
            raise ValueError("符号なし項目に負の値は指定できません")
        value = abs(value) | 1 << sign_bit
    return value.to_bytes(2, order)


def decode(
    data: bytes | bytearray, order: Literal["little", "big"] = "little", sign_bit: int = -1
) -> int:
    value = int.from_bytes(data, order)
    return -(value & (1 << sign_bit) - 1) if sign_bit >= 0 and value & 1 << sign_bit else value


@dataclass(frozen=True)
class Register:
    address: int
    name: str
    size: int
    default: object
    sign_bit: int
    area: str
    access: str
    minimum: int
    maximum: int

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Register:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @property
    def writable(self) -> bool:
        return self.access == "rw"

    @property
    def limits(self) -> tuple[int, int]:
        top = (1 << self.sign_bit) - 1 if self.sign_bit >= 0 else (1 << self.size * 8) - 1
        lo, hi = (-top if self.sign_bit >= 0 else 0, top)
        if (self.minimum, self.maximum) != (-1, -1):
            return (max(lo, self.minimum), min(hi, self.maximum))
        return (lo, hi)

    def pack(self, value: int, order: Literal["little", "big"]) -> bytes:
        lo, hi = self.limits
        if type(value) is not int or not lo <= value <= hi:
            raise ValueError(f"{self.name}: {lo}..{hi} の整数が必要です")
        raw = abs(value) | 1 << self.sign_bit if value < 0 else value
        return raw.to_bytes(self.size, order)

    def unpack(self, raw: bytes, order: Literal["little", "big"]) -> int:
        return decode(raw, order, self.sign_bit)


class Profile:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.name = data["name"]
        self.family = data["family"]
        self.order: Literal["little", "big"] = "big" if data["endian"] else "little"
        self.registers = [Register.from_dict(r) for r in data["registers"]]
        self.by_address = {r.address: r for r in self.registers}
        self.lock = data["lock_address"]
        self.end = max((r.address + r.size for r in self.registers))
        self.feedback_start = data["feedback_start"]
        self.feedback_size = data["feedback_end"] - self.feedback_start + 1
        self.motion_supported = data["motion_supported"]
        self.programmable = data.get("programmable", True)
        self.position_divisor = data.get("position_divisor", 1)
        self.speed_multiplier = data.get("speed_multiplier", 1)

    def decode_memory(self, data: bytes, base: int = 0) -> dict[int, int]:
        return {
            r.address: r.unpack(data[r.address - base : r.address - base + r.size], self.order)
            for r in self.registers
            if base <= r.address and r.address + r.size <= base + len(data)
        }

    def field(self, a: int) -> Register:
        if a not in self.by_address:
            raise ValueError(f"{self.name}: アドレス {a} は未定義です")
        return self.by_address[a]


def identify(header: bytes) -> tuple[str, Profile | None]:
    if len(header) < 9:
        raise ValueError("識別情報は9バイト必要です")

    def matches(p: dict[str, Any]) -> bool:
        return bool(
            p["firmware_major"] == header[0]
            and p["firmware_minor_min"] <= header[1] <= p["firmware_minor_max"]
        )

    raw = next((p for p in CATALOG["profiles"] if matches(p)), None)
    debug = next((p for p in CATALOG["debug_profiles"] if matches(p)), None)
    model = next(
        (
            m["name"]
            for m in CATALOG["models"]
            if m["major"] == header[3] and m["minor_min"] <= header[4] <= m["minor_max"]
        ),
        f"Unknown {header[3]}.{header[4]}",
    )
    if raw:
        return (model, Profile({**raw, **(debug or {})}))
    if debug:
        data = {
            **debug,
            "name": f"Debug {header[0]}.{header[1]}",
            "family": "SCS" if debug["endian"] else "SMS",
            "programmable": False,
            "lock_address": None,
            "motion_supported": debug["torque_address"] > 0,
            "registers": [],
        }
        a = debug["feedback_start"]
        for address, name, size, sign in [
            (a, "Position", 2, 15),
            (a + 2, "Speed", 2, 15),
            (a + 4, "Load", 2, 10),
            (a + 6, "Voltage", 1, -1),
            (a + 7, "Temperature", 1, -1),
            (a + 8, "Registered", 1, -1),
            (a + 9, "Status", 1, -1),
            (a + 10, "Moving", 1, -1),
            (a + 11, "Goal", 2, 15),
            (a + 13, "Current", 2, 15),
        ]:
            data["registers"].append(
                dict(
                    address=address,
                    name=name,
                    size=size,
                    default=0,
                    sign_bit=sign,
                    area="SRAM",
                    access="r",
                    minimum=-1,
                    maximum=-1,
                )
            )
        return (model, Profile(data))
    return (model, None)
