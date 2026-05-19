from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Pos = tuple[int, int]
Direction = Literal["Up", "Down", "Left", "Right"]


@dataclass
class Ghost:
    pos: Pos
    color: str
    name: str
    start: Pos
