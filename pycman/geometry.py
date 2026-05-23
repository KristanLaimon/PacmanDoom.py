"""Small geometry helpers used by animation and rendering code."""

from __future__ import annotations

import math

from pycman.entities import Pos


def hex_color(color: str) -> tuple[int, int, int]:
    """Convert a ``#rrggbb`` color string to a pygame RGB tuple."""
    return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))


def normalize_angle(angle: float) -> float:
    """Normalize an angle to the ``-pi`` to ``pi`` range."""
    while angle <= -math.pi:
        angle += math.tau
    while angle > math.pi:
        angle -= math.tau
    return angle


def map_center(pos: Pos, origin: tuple[int, int], cell_size: int) -> tuple[int, int]:
    """Return the pixel center of a maze cell."""
    return (
        origin[0] + pos[0] * cell_size + cell_size // 2,
        origin[1] + pos[1] * cell_size + cell_size // 2,
    )


def map_center_float(
    pos: tuple[float, float],
    origin: tuple[int, int],
    cell_size: int,
) -> tuple[int, int]:
    """Return the pixel center of a possibly interpolated maze position."""
    return (
        int(origin[0] + pos[0] * cell_size + cell_size / 2),
        int(origin[1] + pos[1] * cell_size + cell_size / 2),
    )
