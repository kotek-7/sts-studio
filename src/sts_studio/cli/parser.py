"""CLI syntax and validation, performed before opening a serial port."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from .. import __version__
from ..catalog import PROTOCOL


def integer_range(low: int, high: int) -> Callable[[str], int]:
    def parse(text: str) -> int:
        try:
            value = int(text, 16 if text.lower().startswith(("0x", "-0x")) else 10)
        except ValueError as error:
            raise argparse.ArgumentTypeError("整数を指定してください") from error
        if not low <= value <= high:
            raise argparse.ArgumentTypeError(f"{low}..{high} の範囲で指定してください")
        return value

    return parse


def ids(text: str) -> list[int]:
    result = [integer_range(0, 253)(part.strip()) for part in text.split(",")]
    if len(result) != len(set(result)):
        raise argparse.ArgumentTypeError("IDが重複しています")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sts-studio", description="STS Studio CLI (JSON出力)")
    parser.add_argument("--version", action="version", version=__version__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--port", help="/dev/ttyUSB0 または /dev/serial/by-id/...")
    source.add_argument("--demo", action="store_true", help="仮想ID1/2。実機へ接続しない")
    parser.add_argument(
        "--baud", type=int, choices=PROTOCOL["port"]["baud_choices"], default=115200
    )
    parser.add_argument("--parity", choices=["N", "O", "E"], default="N")
    parser.add_argument("--timeout-ms", type=integer_range(5, 5000), default=50)
    parser.add_argument("--trace", action="store_true", help="送受信HEXをstderrへ出力")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ports", help="シリアルポート一覧（接続不要）")
    scan = commands.add_parser("scan", help="ID範囲を検索")
    scan.add_argument("--first", type=integer_range(0, 253), default=0)
    scan.add_argument("--last", type=integer_range(0, 253), default=253)
    for name, description in [
        ("info", "モデル・FW・プロファイル"),
        ("read", "メモリまたは1項目読取"),
        ("write", "1項目の設定保存"),
        ("feedback", "フィードバック取得"),
        ("watch", "フィードバック連続取得"),
        ("backup", "STS設定をxdat保存"),
        ("restore", "xdat差分を確認・適用"),
        ("calibrate", "STS中点校正"),
        ("reset", "Recovery指令を送信"),
    ]:
        command = commands.add_parser(name, help=description)
        command.add_argument("--id", required=True, type=integer_range(0, 253))
        if name in ("read", "write"):
            command.add_argument("--address", type=integer_range(0, 255), required=name == "write")
        if name == "write":
            command.add_argument(
                "--value", type=int, required=True, help="レジスタ値（Baudはコード0..7）"
            )
        if name == "watch":
            command.add_argument("--interval-ms", type=integer_range(20, 60000), default=100)
            command.add_argument(
                "--count", type=integer_range(0, 1000000), default=0, help="0=Ctrl+Cまで"
            )
        if name in ("backup", "restore"):
            command.add_argument("file")
        if name == "restore":
            command.add_argument("--apply", action="store_true", help="省略時は差分表示のみ")
            command.add_argument(
                "--include-identity", action="store_true", help="ID・Baudも復元対象に含める"
            )
    move = commands.add_parser("move", help="目標指令を送信（トルクを自動ONにはしない）")
    move.add_argument("--ids", type=ids, required=True, help="カンマ区切り: 1,2")
    move.add_argument("--position", required=True, type=integer_range(-32766, 32766))
    move.add_argument("--speed", type=integer_range(-32766, 32766), default=0)
    move.add_argument("--acc", type=integer_range(0, 254), default=0)
    move.add_argument("--time-raw", type=integer_range(0, 65535), default=0)
    move.add_argument("--method", choices=["write", "sync", "registered"], default="write")
    torque = commands.add_parser("torque", help="トルクON/OFFを読戻し確認")
    torque.add_argument("--ids", type=ids, required=True)
    torque.add_argument("state", choices=["on", "off"])
    stop = commands.add_parser("stop", help="指定IDのトルクOFF（全対象を試行）")
    stop.add_argument("--ids", type=ids, required=True)
    commands.add_parser("action", help="バス全体に登録指令の実行を送信")
    pwm = commands.add_parser("pwm", help="アダプターID253への送信（出力未確認）")
    pwm.add_argument("kind", choices=["mode", "pulse", "enable"])
    pwm.add_argument("value", type=int)
    inspect = commands.add_parser("inspect", help="ファームウェアファイルの検査（接続不要）")
    inspect.add_argument("file")
    return parser
