"""Checked access to widgets created by the desktop layout."""

from typing import TypeVar

T = TypeVar("T")


def required(value: T | None) -> T:
    if value is None:
        raise RuntimeError("画面部品が初期化されていません")
    return value
