"""Public desktop entry points."""

from .app import main
from .trend import Trend
from .window import Window

__all__ = ["main", "Window", "Trend"]
