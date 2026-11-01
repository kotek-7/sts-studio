"""Explicit virtual bus. Never imports serial or opens a /dev device."""

import time

from .catalog import decode
from .wire import Timeout, frame


class VirtualLink:
    def __init__(self, trace=None):
        self.baud = 1000000
        self.timeout = 0.05
        self.trace = trace or (lambda *a: None)
        self.tx_bytes = 0
        self.rx_bytes = 0
        self.pending = {}
        self.mem = {}
        self.last = time.monotonic()
        self.history = []
        for sid in (1, 2):
            m = bytearray(256)
            for a, v, n in [
                (0, 3, 1),
                (1, 6, 1),
                (3, 9, 1),
                (4, 3, 1),
                (5, sid, 1),
                (8, 1, 1),
                (11, 4095, 2),
                (13, 70, 1),
                (14, 80, 1),
                (15, 40, 1),
                (16, 1000, 2),
                (21, 32, 1),
                (22, 32, 1),
                (24, 16, 2),
                (28, 500, 2),
                (30, 1, 1),
                (35, 200, 1),
                (36, 80, 1),
                (41, 10, 1),
                (42, 2048, 2),
                (46, 200, 2),
                (48, 1000, 2),
                (55, 1, 1),
                (56, 2048, 2),
                (62, 74, 1),
                (63, 25, 1),
                (69, 10, 2),
            ]:
                m[a : a + n] = v.to_bytes(n, "little")
            self.mem[sid] = m
        self.adapter = bytearray(256)

    def close(self):
        pass

    def tick(self):
        now = time.monotonic()
        dt = now - self.last
        self.last = now
        for m in self.mem.values():
            pos = decode(m[56:58], sign_bit=15)
            target = decode(m[42:44], sign_bit=15)
            speed = decode(m[46:48], sign_bit=15)
            moving = False
            if m[40] == 1:
                if m[33] == 1:
                    pos = int((pos + speed * dt) % 4096)
                    moving = speed != 0
                else:
                    difference = target - pos
                    delta = min(abs(difference), max(1, int((abs(speed) or 1000) * dt)))
                    pos += (1 if difference > 0 else -1) * delta if difference else 0
                    moving = pos != target
            m[56:58] = (abs(pos) | (0x8000 if pos < 0 else 0)).to_bytes(2, "little")
            m[66] = int(moving)
            m[58:60] = (abs(speed) | (0x8000 if speed < 0 else 0) if moving else 0).to_bytes(
                2, "little"
            )
            m[60:62] = (180 if moving else 0).to_bytes(2, "little")
            m[69:71] = (32 if moving else 10).to_bytes(2, "little")

    def exchange(self, sid, ins, params=b"", expected=0, wait=True):
        tx = frame(sid, ins, params)
        self.history.append(tx)
        self.trace("TX", tx)
        self.tx_bytes += len(tx)
        self.tick()
        if sid == 253:
            if ins == 2:
                raise Timeout("仮想アダプターは識別READに応答しません")
            if ins == 3:
                self.adapter[params[0] : params[0] + len(params) - 1] = params[1:]
            return b"", 0
        if sid == 254 and ins == 131:
            a, n = params[:2]
            for i in range(2, len(params), n + 1):
                if params[i] in self.mem:
                    self.mem[params[i]][a : a + n] = params[i + 1 : i + 1 + n]
            return b"", 0
        if sid == 254 and ins == 5:
            for target, (a, data) in self.pending.items():
                self.mem[target][a : a + len(data)] = data
                self.mem[target][64] = 0
            self.pending.clear()
            return b"", 0
        if sid not in self.mem:
            raise Timeout(f"仮想ID {sid}: 応答なし")
        m = self.mem[sid]
        data = b""
        if ins == 2:
            data = bytes(m[params[0] : params[0] + params[1]])
        elif ins in (3, 4):
            a, payload = params[0], params[1:]
            if ins == 4:
                self.pending[sid] = (a, payload)
                m[64] = 1
            elif a == 40 and payload == b"\x80":
                m[56:58] = (2048).to_bytes(2, "little")
            else:
                if a >= 40 or m[55] == 0:
                    m[a : a + len(payload)] = payload
                if a == 5 and m[5] != sid:
                    self.mem[m[5]] = self.mem.pop(sid)
        elif ins == 6:
            m[40] = 0  # Deliberately does not claim to simulate real factory reset semantics.
        if not wait:
            return b"", 0
        rx = frame(sid, 0, data)
        self.trace("RX", rx)
        self.rx_bytes += len(rx)
        return data, 0
