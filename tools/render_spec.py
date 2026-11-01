#!/usr/bin/env python3
"""Render product specifications and API index from structured definitions."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generated():
    contracts = json.loads((ROOT / "spec/features.json").read_text())["features"]
    catalog = json.loads((ROOT / "spec/catalog.json").read_text())
    protocol = json.loads((ROOT / "spec/protocol.json").read_text())
    lines = [
        "# STS Studio 機能仕様書",
        "",
        "機能ごとの入力、実行手順、成功条件、エラー処理を定義します。機械可読定義は `spec/features.json`、設計は [DESIGN.md](DESIGN.md)、メモリ表は [REGISTERS.md](REGISTERS.md) を参照してください。",
        "",
        "自動テストと実行方法は [VALIDATION.md](VALIDATION.md) を参照してください。",
        "",
    ]
    matrix = [
        "# STS Studio 機能一覧",
        "",
        "| ID | 機能 | 状態 | 実装 | テスト |",
        "|---|---|---|---|---|",
    ]
    for f in contracts:
        status = "対応" if f["status"] == "implemented" else "未対応"
        matrix.append(
            f"| {f['id']} | {f['title']} | {status} | `{f['implementation'] or '—'}` | `{f['test'] or '—'}` |"
        )
        lines += [f"## {f['id']}: {f['title']}", "", f"状態: **{status}**", "", "### 入力", ""]
        if f["inputs"]:
            lines += ["| 項目 | 型・範囲・既定値 |", "|---|---|"] + [
                f"| {k} | {v} |" for k, v in f["inputs"].items()
            ]
        else:
            lines += ["追加入力なし。"]
        for label, key in [
            ("前提", "preconditions"),
            ("実行手順・通信", "effect"),
            ("成功条件・後状態", "postconditions"),
            ("エラー・中止", "failure"),
        ]:
            lines += ["", f"**{label}**: {f[key]}"]
        lines += [
            "",
            f"**実装**: `{f['implementation'] or '—'}` / **テスト**: `{f['test'] or '—'}`",
            "",
        ]
    lines += ["## 通信フレームの検証ベクトル", "", "| ID | TX | 意味 |", "|---|---|---|"]
    for v in protocol["test_vectors"]:
        lines.append(f"| {v['id']} | `{v['frame']}` | {v['meaning']} |")
    regs = [
        "# メモリ表・モデル識別仕様",
        "",
        "機械可読定義は `spec/catalog.json`。`-1 / -1`は入力範囲未指定です。実効範囲は格納幅・符号bitによる範囲と明示範囲の共通部分です。",
        "",
    ]
    for p in catalog["profiles"]:
        regs += [
            f"## {p['name']} / {p['family']}",
            "",
            f"FW {p['firmware_major']}.{p['firmware_minor_min']}〜{p['firmware_major']}.{p['firmware_minor_max']}、byte order: {'big' if p['endian'] else 'little'}。feedback {p['feedback_start']}..{p['feedback_end']}、control {p['control_start']}、lock {p['lock_address']}。",
            "",
        ]
        for note in p["notes"]:
            regs += [note, ""]
        regs += [
            "| Addr | Name | bytes | default | sign bit | area | access | min | max |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for r in p["registers"]:
            regs.append(
                "| "
                + " | ".join(
                    str(r[k])
                    for k in [
                        "address",
                        "name",
                        "size",
                        "default",
                        "sign_bit",
                        "area",
                        "access",
                        "minimum",
                        "maximum",
                    ]
                )
                + " |"
            )
        regs.append("")
    regs += [
        "## 操作・監視プロファイル",
        "",
        "設定メモリ表とは独立した定義です。メモリ表がなくても対応する操作・監視を使用できます。torque=0の定義は監視のみです。",
        "",
        "| FW | endian | feedback | control | torque | position divisor | speed multiplier |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in catalog["debug_profiles"]:
        regs.append(
            f"| {d['firmware_major']}.{d['firmware_minor_min']}..{d['firmware_minor_max']} | {d['endian']} | {d['feedback_start']}..{d['feedback_end']} | {d['control_start']} | {d['torque_address']} | {d['position_divisor']} | {d['speed_multiplier']} |"
        )
    regs.append("")
    regs += ["## モデル名識別", "", "| major | minor range | endian | name |", "|---|---|---|---|"]
    for m in catalog["models"]:
        regs.append(
            f"| {m['major']} | {m['minor_min']}..{m['minor_max']} | {m['endian']} | {m['name']} |"
        )
    api = [
        "# モジュール・関数索引",
        "",
        "モジュール別のシグネチャと定義行を示します。動作仕様はSPECIFICATION / DESIGNを参照してください。",
        "",
    ]
    for file in sorted((ROOT / "src/sts_studio").rglob("*.py")):
        tree = ast.parse(file.read_text())
        api += [
            f"## {file.relative_to(ROOT / 'src/sts_studio').as_posix()}",
            "",
            ast.get_docstring(tree) or "",
            "",
        ]
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                api += [f"- `{node.name}({ast.unparse(node.args)})` — line {node.lineno}"]
            elif isinstance(node, ast.ClassDef):
                api += [f"### {node.name}", ""]
                for method in node.body:
                    if isinstance(method, ast.FunctionDef):
                        api += [
                            f"- `{node.name}.{method.name}({ast.unparse(method.args)})` — line {method.lineno}"
                        ]
                api.append("")
    return {
        "SPECIFICATION.md": "\n".join(lines) + "\n",
        "FEATURE_MATRIX.md": "\n".join(matrix) + "\n",
        "REGISTERS.md": "\n".join(regs) + "\n",
        "API_INDEX.md": "\n".join(api) + "\n",
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for name, text in generated().items():
        path = ROOT / "docs" / name
        if args.check:
            if not path.exists() or path.read_text() != text:
                stale.append(name)
        else:
            path.write_text(text)
    if stale:
        raise SystemExit("仕様書を再生成してください: " + ", ".join(stale))
