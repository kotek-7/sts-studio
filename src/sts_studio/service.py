"""Servo operations. No Qt dependencies; effects and partial failures are explicit."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event

from .catalog import PROTOCOL, Profile, decode, identify, unsigned_word
from .contracts import Feedback, Link, RestoreResult, Snapshot
from .wire import Bus, LinkError, StatusError, Timeout


@dataclass
class Servo:
    sid: int
    model: str
    profile: Profile | None
    header: bytes

    def require_profile(self) -> Profile:
        if self.profile is None:
            raise LinkError("未対応ファームウェアです")
        return self.profile

    @property
    def firmware(self) -> str:
        return f"{self.header[0]}.{self.header[1]}"


class Service:
    def __init__(self, link: Link) -> None:
        self.link = link
        self.bus = Bus(link)
        self.servos: dict[int, Servo] = {}
        self.pending: set[int] = set()

    def discover(self, sid: int) -> tuple[Servo, int]:
        header, bits = self.bus.read(sid, 0, 9)
        model, profile = identify(header)
        servo = Servo(sid, model, profile, header)
        self.servos[sid] = servo
        return (servo, bits)

    def scan(
        self, start: int, end: int, cancel: Event, progress: Callable[[int, Servo | None], None]
    ) -> list[Servo]:
        found = []
        for sid in ([253] if start <= 253 <= end else []) + [
            i for i in range(start, end + 1) if i != 253
        ]:
            if cancel.is_set():
                break
            try:
                s, b = self.discover(sid)
                found.append(s)
                progress(sid, s)
            except Timeout:
                progress(sid, None)
        return found

    def get(self, sid: int) -> Servo:
        servo = self.servos[sid]
        if not servo.profile:
            raise LinkError(
                "このファームウェアに一致するメモリ表がありません。書き込みを禁止しています"
            )
        return servo

    def snapshot(self, sid: int) -> Snapshot:
        s = self.get(sid)
        boundary = 40
        p = s.require_profile()
        if not p.programmable:
            raise LinkError(
                "このファームウェアの設定メモリ表はありません。操作・監視のみ対応します"
            )
        a, e1 = self.bus.read(sid, 0, min(boundary, p.end))
        b, e2 = self.bus.read(sid, boundary, p.end - boundary) if p.end > boundary else (b"", 0)
        raw = a + b
        return {
            "id": sid,
            "raw": raw,
            "values": p.decode_memory(raw),
            "error": e1 | e2,
            "goal": decode(raw[67:69], p.order, 15) if len(raw) >= 69 else None,
        }

    def feedback(self, sid: int) -> Feedback:
        p = self.get(sid).require_profile()
        raw, bits = self.bus.read(sid, p.feedback_start, p.feedback_size)
        vals = {
            56: decode(raw[0:2], p.order, 15),
            58: decode(raw[2:4], p.order, 15),
            60: decode(raw[4:6], p.order, 10),
            62: raw[6],
            63: raw[7],
            64: raw[8],
            65: raw[9],
            66: raw[10],
            69: decode(raw[13:15], p.order, 15),
        }
        return {
            "id": sid,
            "values": vals,
            "goal": decode(raw[11:13], p.order, 15),
            "error": bits,
            "timestamp": time.time(),
        }

    def read_value(self, sid: int, address: int) -> tuple[int, int]:
        p = self.get(sid).require_profile()
        r = p.field(address)
        data, bits = self.bus.read(sid, address, r.size)
        return (r.unpack(data, p.order), bits)

    def verify(self, sid: int, address: int, data: bytes, ignore_alarm: bool = False) -> None:
        raw, bits = self.bus.read(sid, address, len(data))
        if raw != data:
            raise LinkError(
                f"ID {sid} アドレス{address}: 読み戻し不一致。書込状態を再読込してください"
            )
        if bits and (not ignore_alarm):
            raise StatusError(bits)

    def write_verified(
        self, sid: int, address: int, data: bytes, ignore_alarm: bool = False
    ) -> None:
        self.bus.send(sid, address, data)
        self.verify(sid, address, data, ignore_alarm)

    def set_torque(self, ids: list[int], enabled: bool) -> list[int]:
        done = []
        failures = []
        for sid in ids:
            try:
                s = self.get(sid)
                address = s.require_profile().data["torque_address"]
                if not address:
                    raise LinkError("このプロファイルはトルク制御に対応していません")
                self.write_verified(sid, address, bytes((int(enabled),)), ignore_alarm=not enabled)
                done.append(sid)
            except Exception as e:
                failures.append(f"ID {sid}: {e}")
                if enabled:
                    break
        if failures:
            raise LinkError(
                f"トルク {('ON' if enabled else 'OFF')}: 確認済みID {done}; 未確認 "
                + " / ".join(failures)
            )
        return done

    def write_register(self, sid: int, address: int, value: int) -> int:
        s = self.get(sid)
        p = s.require_profile()
        r = p.field(address)
        if not r.writable:
            raise ValueError("読み取り専用項目です")
        data = r.pack(value, p.order)
        if r.area != "EPROM":
            self.write_verified(sid, address, data, ignore_alarm=address == 40 and value == 0)
            return sid
        torque, bits = self.read_value(sid, p.data["torque_address"])
        if torque:
            raise LinkError("EEPROM変更はトルクOFFで実行してください")
        if bits:
            raise StatusError(bits)
        if address == 5 and value != sid:
            try:
                self.bus.read(value, 0, 9)
            except Timeout:
                pass
            else:
                raise LinkError(f"ID {value} は使用中です")
        if address == 6 and p.family != "STS":
            raise LinkError(
                "この系列の通信速度コード対応は未検証です。ネイティブ版では変更を禁止しています"
            )
        old_lock, _ = self.read_value(sid, p.lock)
        new_sid = sid
        errors = []
        try:
            self.write_verified(sid, p.lock, b"\x00")
            self.bus.send(sid, address, data)
            time.sleep(0.02)
            if address == 5:
                new_sid = value
                s.sid = value
                self.servos.pop(sid)
                self.servos[value] = s
            if address == 6:
                self.link.baud = PROTOCOL["sts_baud_codes"][value]
            self.verify(new_sid, address, data)
        except Exception as e:
            errors.append(str(e))
        finally:
            try:
                self.write_verified(new_sid, p.lock, bytes((old_lock,)))
            except Exception as e:
                errors.append("EEPROMロック復元未確認: " + str(e))
        if errors:
            raise LinkError(
                " / ".join(errors) + f"（現在の接続先 ID {new_sid}, {self.link.baud} bps）"
            )
        return new_sid

    def restore(self, sid: int, changes: list[tuple[int, int]], cancel: Event) -> RestoreResult:
        completed: list[int] = []
        for address, value in changes:
            if cancel.is_set():
                return {"completed": completed, "cancelled": True, "id": sid}
            try:
                sid = self.write_register(sid, address, value)
                completed.append(address)
            except Exception as e:
                raise LinkError(
                    f"復元を中止。適用済みアドレス {completed}; 失敗 {address}: {e}"
                ) from e
        return {"completed": completed, "cancelled": False, "id": sid}

    def control_payload(
        self, sid: int, position: int, speed: int, acc: int, time_raw: int
    ) -> bytes:
        p = self.get(sid).require_profile()
        if not p.motion_supported:
            raise LinkError("このプロファイルの動作指令は未確認です")
        if not -32766 <= position <= 32766 or not -32766 <= speed <= 32766:
            raise ValueError("位置・速度は -32766..32766")
        if not 0 <= acc <= 254 or not 0 <= time_raw <= 65535:
            raise ValueError("加速度0..254 / Time生値0..65535")
        if p.family == "SCS" and (position < 0 or speed < 0):
            raise ValueError("SCSの位置・速度は非負で指定してください")
        return (
            bytes((acc,))
            + unsigned_word(position, p.order, 15)
            + time_raw.to_bytes(2, p.order)
            + unsigned_word(speed, p.order, 15)
        )

    def control(
        self,
        ids: list[int],
        position: int,
        speed: int,
        acc: int,
        time_raw: int,
        method: str = "write",
        cancel: Event | None = None,
    ) -> list[int]:
        if cancel is not None and cancel.is_set():
            raise LinkError("指令は送信前に中止されました")
        entries = [(sid, self.control_payload(sid, position, speed, acc, time_raw)) for sid in ids]
        if not entries:
            raise ValueError("対象を選択してください")
        if method == "sync":
            if len(entries) > 30:
                raise ValueError("同期指令は最大30台です（250バイト上限）")
            addresses = {
                self.get(sid).require_profile().data["control_start"] for sid, _ in entries
            }
            if len(addresses) != 1:
                raise ValueError("制御アドレスが異なる機種を同時にSync Writeできません")
            address = addresses.pop()
            self.bus.sync(address, entries)
        elif method in ("write", "registered"):
            for sid, data in entries:
                if cancel is not None and cancel.is_set():
                    raise LinkError("残りの送信を中止しました")
                self.bus.send(
                    sid,
                    self.get(sid).require_profile().data["control_start"],
                    data,
                    registered=method == "registered",
                )
                if method == "registered":
                    self.pending.add(sid)
        else:
            raise ValueError("書込方式が不正です")
        return ids

    def action(self) -> list[int]:
        ids = sorted(self.pending)
        self.bus.action()
        self.pending.clear()
        return ids

    def reset(self, sid: int) -> str:
        self.bus.reset(sid)
        self.servos.pop(sid, None)
        self.pending.discard(sid)
        return "Recovery指令を送信しました。完了・ID・通信速度は未確認です。再検索してください。"

    def calibration(self, sid: int) -> int:
        s = self.get(sid)
        if s.require_profile().family != "STS":
            raise LinkError("中点校正はSTS専用です")
        torque, bits = self.read_value(sid, 40)
        if torque or bits:
            raise LinkError("トルクOFFとエラー解消が必要です")
        self.bus.send(sid, 40, b"\x80")
        time.sleep(0.05)
        position, bits = self.read_value(sid, 56)
        if bits or abs(position - 2048) > 2:
            raise LinkError("校正結果を確認できません")
        return position

    def pwm(self, kind: str, value: int) -> str:
        addresses = {"mode": (9, 1), "pulse": (33, 2), "enable": (35, 1)}
        if kind not in addresses:
            raise ValueError("未検証のPWM指令です")
        if kind == "pulse" and (not 500 <= value <= 2500):
            raise ValueError("PWM幅は500..2500 µsです")
        if kind != "pulse" and value not in (0, 1):
            raise ValueError("0または1を指定してください")
        address, size = addresses[kind]
        data = value.to_bytes(size, "little")
        self.bus.send(253, address, data)
        return "アダプターID253へ送信済み（出力未確認）"
