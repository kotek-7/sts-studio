"""Headless command line entry point; imports no Qt modules."""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from typing import Any

from serial.tools import list_ports

from ..contracts import Link
from ..files import inspect_firmware
from ..service import Service
from ..simulator import VirtualLink
from ..wire import LinkError, SerialLink
from .commands import execute
from .parser import build_parser


def json_default(value: object) -> str:
    if isinstance(value, bytes):
        return value.hex()
    raise TypeError(f"JSON出力できない型: {type(value).__name__}")


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, default=json_default), flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "scan" and args.first > args.last:
        parser.error("--first は --last 以下にしてください")
    if args.command == "pwm" and not (
        500 <= args.value <= 2500 if args.kind == "pulse" else args.value in (0, 1)
    ):
        parser.error("pulseは500..2500、mode/enableは0または1です")
    if args.command not in ("ports", "inspect") and not args.port and not args.demo:
        parser.error("--port または --demo を指定してください")
    link: Link | None = None
    try:
        if args.command == "ports":
            emit(
                {
                    "ports": [
                        {"device": p.device, "description": p.description, "hwid": p.hwid}
                        for p in sorted(list_ports.comports(), key=lambda p: p.device)
                    ]
                }
            )
            return 0
        if args.command == "inspect":
            emit(inspect_firmware(args.file))
            return 0

        def trace(direction: str, raw: bytes) -> None:
            if args.trace:
                print(f"{direction} {raw.hex(' ').upper()}", file=sys.stderr, flush=True)

        link = (
            VirtualLink(trace)
            if args.demo
            else SerialLink(args.port, args.baud, args.parity, args.timeout_ms, trace)
        )
        return execute(args, Service(link), emit)
    except KeyboardInterrupt:
        print("中断しました。実行済みの指令・設定は戻していません。", file=sys.stderr)
        return 130
    except (LinkError, OSError, ValueError, KeyError) as error:
        payload: dict[str, Any] = {"error": str(error), "command": args.command}
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 1
    finally:
        if link is not None:
            link.close()
