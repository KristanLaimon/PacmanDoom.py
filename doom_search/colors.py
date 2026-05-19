from __future__ import annotations

from typing import Iterable


def fade(color: str, divisor: int = 3) -> str:
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)
    return f"#{red // divisor:02x}{green // divisor:02x}{blue // divisor:02x}"


def sum_colors(colors: Iterable[str]) -> str:
    red = 0
    green = 0
    blue = 0
    for color in colors:
        red += int(color[1:3], 16)
        green += int(color[3:5], 16)
        blue += int(color[5:7], 16)
    return f"#{min(red, 255):02x}{min(green, 255):02x}{min(blue, 255):02x}"
