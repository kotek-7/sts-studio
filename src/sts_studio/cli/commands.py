"""Synchronous CLI workflows using the same service as the desktop UI."""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from threading import Event
from typing import Any

from ..files import ParameterImage
from ..service import Service, Servo
from ..wire import LinkError

Emit = Callable[[object], None]


def describe(servo: Servo) -> dict[str, object]:
    return {
        "id": servo.sid,
        "model": servo.model,
        "firmware": servo.firmware,
        "profile": servo.profile.name if servo.profile else None,
        "programmable": bool(servo.profile and servo.profile.programmable),
    }


def stop_targets(service: Service, targets: list[int], emit: Emit) -> int:
    results: list[dict[str, object]] = []
    for sid in targets:
        try:
            service.discover(sid)
            service.set_torque([sid], False)
            results.append({"id": sid, "confirmed": True})
        except (LinkError, OSError, ValueError, KeyError) as error:
            results.append({"id": sid, "confirmed": False, "error": str(error)})
    emit({"operation": "stop", "results": results})
    return 0 if all(item["confirmed"] for item in results) else 1


def execute(args: argparse.Namespace, service: Service, emit: Emit) -> int:
    command: str = args.command
    if command == "scan":
        found = service.scan(args.first, args.last, Event(), lambda sid, servo: None)
        emit({"servos": [describe(s) for s in found]})
        return 0
    if command == "stop" or (command == "torque" and args.state == "off"):
        return stop_targets(service, args.ids, emit)
    if command == "action":
        service.action()
        emit({"operation": "action", "scope": "broadcast", "sent": True, "confirmed": False})
        return 0
    if command == "pwm":
        message = service.pwm(args.kind, args.value)
        emit({"operation": "pwm", "sent": True, "confirmed": False, "message": message})
        return 0
    if command in ("move", "torque"):
        for sid in args.ids:
            service.discover(sid)
        if command == "move":
            service.control(
                args.ids, args.position, args.speed, args.acc, args.time_raw, args.method
            )
            emit(
                {
                    "operation": "move",
                    "ids": args.ids,
                    "method": args.method,
                    "sent": True,
                    "confirmed": False,
                }
            )
        else:
            confirmed = service.set_torque(args.ids, True)
            emit({"operation": "torque", "enabled": True, "confirmed_ids": confirmed})
        return 0
    sid = args.id
    servo, bits = service.discover(sid)
    if command == "info":
        emit({**describe(servo), "error": bits})
    elif command == "read":
        if args.address is None:
            emit(service.snapshot(sid))
        else:
            value, error = service.read_value(sid, args.address)
            emit({"id": sid, "address": args.address, "value": value, "error": error})
    elif command == "write":
        new_id = service.write_register(sid, args.address, args.value)
        emit(
            {
                "id": new_id,
                "baud": service.link.baud,
                "address": args.address,
                "value": args.value,
                "confirmed": True,
            }
        )
    elif command == "feedback":
        emit(service.feedback(sid))
    elif command == "watch":
        index = 0
        while args.count == 0 or index < args.count:
            started = time.monotonic()
            emit(service.feedback(sid))
            index += 1
            if args.count == 0 or index < args.count:
                time.sleep(max(0, args.interval_ms / 1000 - (time.monotonic() - started)))
    elif command == "backup":
        if servo.require_profile().family != "STS":
            raise ValueError("xdat保存はSTS専用です")
        snapshot = service.snapshot(sid)
        ParameterImage(0, snapshot["raw"][:40]).save(args.file)
        emit({"id": sid, "file": args.file, "saved": True})
    elif command == "restore":
        servo.require_profile()
        image = ParameterImage.load(args.file)
        changes: list[tuple[int, int]] = image.changes(servo, service.snapshot(sid)["values"])
        excluded = [
            address for address, value in changes if address in (5, 6) and not args.include_identity
        ]
        changes = [(a, v) for a, v in changes if a not in excluded]
        changes.sort(key=lambda pair: (pair[0] in (5, 6), pair[0]))
        result: dict[str, Any] = {
            "id": sid,
            "changes": [{"address": a, "value": v} for a, v in changes],
            "excluded_addresses": excluded,
            "applied": False,
        }
        if args.apply:
            result.update(service.restore(sid, changes, Event()))
            result.update(applied=True, baud=service.link.baud)
        emit(result)
    elif command == "calibrate":
        emit({"id": sid, "position": service.calibration(sid), "confirmed": True})
    elif command == "reset":
        servo.require_profile()
        emit({"id": sid, "message": service.reset(sid), "sent": True, "confirmed": False})
    else:
        raise ValueError(f"未対応コマンド: {command}")
    return 0
