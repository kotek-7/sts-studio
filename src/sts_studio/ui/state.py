"""Typed state owned by the motion and monitoring features."""

from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict

from ..automation import Pattern
from ..files import Recorder

MotionArgs = tuple[list[int], int, int, int, int, str]


@dataclass(frozen=True)
class ServoCommand:
    args: MotionArgs


@dataclass(frozen=True)
class PwmPulse:
    value: int


class AutoBase(TypedDict):
    pattern: Pattern
    delay: float
    next: float


class ServoAuto(AutoBase):
    pwm: Literal[False]
    ids: list[int]
    speed: int
    acc: int
    time: int
    method: str


class PwmAuto(AutoBase):
    pwm: Literal[True]


AutoPlan = ServoAuto | PwmAuto


class CaptureState(TypedDict):
    recorder: Recorder
    interval: float
    flush_at: float
    path: NotRequired[str]
