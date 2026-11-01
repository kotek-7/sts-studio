"""Strict, non-executing file formats. Xdat support is limited to STS parameter blocks."""

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParameterImage:
    start: int
    data: bytes
    trailer: bytes = b"\0\0"

    @classmethod
    def load(cls, path):
        raw = Path(path).read_bytes()
        if len(raw) < 4:
            raise ValueError("設定ファイルが短すぎます")
        start, n = raw[:2]
        if n == 0 or len(raw) != n + 4 or start + n > 256:
            raise ValueError("xdatの長さ・アドレスが不正です")
        return cls(start, raw[2 : 2 + n], raw[-2:])

    def save(self, path):
        if not 0 < len(self.data) <= 255 or len(self.trailer) != 2:
            raise ValueError("xdatのデータ長が不正です")
        Path(path).write_bytes(bytes((self.start, len(self.data))) + self.data + self.trailer)

    def changes(self, servo, current):
        if servo.profile.family != "STS" or self.start != 0 or len(self.data) != 40:
            raise ValueError("xdat設定ファイルはSTSのアドレス0..39 (40 bytes) に対応しています")
        if self.data[3:5] != servo.header[3:5] or self.data[:2] != servo.header[:2]:
            raise ValueError("モデル番号・ファームウェアが一致しません")
        result = []
        for r in servo.profile.registers:
            if r.writable and r.area == "EPROM" and r.address + r.size <= len(self.data):
                value = r.unpack(self.data[r.address : r.address + r.size], servo.profile.order)
                if current.get(r.address) != value:
                    r.pack(value, servo.profile.order)
                    result.append((r.address, value))
        return result


CSV_HEADER = [
    "timestamp",
    "id",
    "position_steps",
    "goal_steps",
    "load_raw",
    "speed_steps_s",
    "current_raw",
    "temperature_C",
    "voltage_V",
    "error",
]
TEXT_HEADER = ["No", "Pos", "Gol", "Ft", "V", "C", "T", "Vol"]


def csv_row(row, index, legacy):
    if legacy:
        return [
            index,
            row.get(56, 0),
            row.get("goal", 0),
            row.get(60, 0),
            row.get(58, 0),
            row.get(69, 0),
            row.get(63, 0),
            row.get(62, 0),
            "END",
        ]
    return [
        row["timestamp"],
        row["id"],
        row.get(56, ""),
        row.get("goal", ""),
        row.get(60, ""),
        row.get(58, ""),
        row.get(69, ""),
        row.get(63, ""),
        row[62] / 10 if 62 in row else "",
        row.get("error", ""),
    ]


def write_csv(path, rows, legacy=False):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(TEXT_HEADER if legacy else CSV_HEADER)
        for i, row in enumerate(rows, 1):
            w.writerow(csv_row(row, i, legacy))


class Recorder:
    """Buffered telemetry recording with periodic flush."""

    def __init__(self, path, legacy=False):
        self.path = path
        self.legacy = legacy
        self.buffer = []
        self.count = 0
        write_csv(path, [], legacy)

    def append(self, row):
        self.count += 1
        self.buffer.append((self.count, row.copy()))

    def flush(self):
        if not self.buffer:
            return
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for i, row in self.buffer:
                w.writerow(csv_row(row, i, self.legacy))
        self.buffer.clear()


def inspect_firmware(path):
    data = Path(path).read_bytes()
    if not data:
        raise ValueError("空のファームウェアです")
    result = {
        "name": Path(path).name,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "flash_supported": False,
    }
    if Path(path).suffix.lower() == ".hex":
        base = 0
        memory: dict[int, int] = {}
        eof = False
        for line in data.decode("ascii").splitlines():
            if not line:
                continue
            if eof:
                raise ValueError("EOF後にHEXレコードがあります")
            if not line.startswith(":"):
                raise ValueError("Intel HEXレコードが不正です")
            b = bytes.fromhex(line[1:])
            if len(b) < 5 or len(b) != b[0] + 5 or sum(b) & 255:
                raise ValueError("Intel HEXの長さ・チェックサムが不正です")
            n, addr, kind = b[0], int.from_bytes(b[1:3], "big"), b[3]
            payload = b[4:-1]
            if kind == 0:
                for i, v in enumerate(payload):
                    a = base + addr + i
                    if a in memory and memory[a] != v:
                        raise ValueError("HEXのアドレスが重複しています")
                    memory[a] = v
            elif kind == 1:
                if n != 0 or addr != 0:
                    raise ValueError("HEX EOFが不正です")
                eof = True
            elif kind in (2, 4):
                if n != 2 or addr != 0:
                    raise ValueError("HEX拡張アドレスが不正です")
                base = int.from_bytes(payload, "big") << (4 if kind == 2 else 16)
            elif kind in (3, 5):
                if n != 4:
                    raise ValueError("HEX開始アドレスが不正です")
            else:
                raise ValueError("未対応のHEXレコード")
        if not eof:
            raise ValueError("Intel HEX EOFがありません")
        result.update(
            data_bytes=len(memory),
            address_min=min(memory) if memory else None,
            address_max=max(memory) if memory else None,
        )
    return result
