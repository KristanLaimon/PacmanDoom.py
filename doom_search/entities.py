"""Shared type aliases and simple game entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Pos = tuple[int, int]
Direction = Literal["Up", "Down", "Left", "Right"]
SearchAlgorithm = Literal["Dijkstra"]


@dataclass
class Ghost:
    """Enemy actor with rendering colors and a pathfinding strategy."""

    pos: Pos
    color: str
    name: str
    start: Pos
    algorithm: SearchAlgorithm
    search_color: str
    path_color: str
