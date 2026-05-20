"""Shared configuration values for the pygame front end."""

from __future__ import annotations

import math
from pathlib import Path

from doom_search.entities import Direction

VIEW_WIDTH = 760
VIEW_HEIGHT = 520
HUD_HEIGHT = 92
CLASSIC_CELL = 28
DEFAULT_TICK_MS = 320
SMOOTH_VIEW_FPS = 60

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
FRAME_DIR = ASSET_DIR / "frames"
PACMAN_ANIMATION_MS = 90
GHOST_ANIMATION_MS = 140

DIRECTION_ANGLES: dict[Direction, float] = {
    "Right": 0.0,
    "Down": math.pi / 2,
    "Left": math.pi,
    "Up": -math.pi / 2,
}
