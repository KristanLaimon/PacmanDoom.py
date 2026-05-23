"""Maze layout and movement helpers."""

from __future__ import annotations

from dataclasses import dataclass

from pycman.entities import Direction, Pos

MAZE = [
    "#####################",
    "#.........#.........#",
    "#.###.###.#.###.###.#",
    "#o....#.....#.....o.#",
    "#.###.#.###.#.###.#.#",
    "#.....#..#..#.....#.#",
    "#.#####..#..#####.#.#",
    "#....... P .........#",
    "#.#####..#..#####.#.#",
    "#.....#..#..#.....#.#",
    "#.###.#.###.#.###.#.#",
    "#o....#.....#.....o.#",
    "#.###.###.#.###.###.#",
    "#.........#.........#",
    "#####################",
]

DIRECTIONS: dict[Direction, Pos] = {
    "Up": (0, -1),
    "Down": (0, 1),
    "Left": (-1, 0),
    "Right": (1, 0),
}

KEY_TO_DIRECTION: dict[str, Direction] = {
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "w": "Up",
    "s": "Down",
    "a": "Left",
    "d": "Right",
}


@dataclass(frozen=True)
class Maze:
    """Immutable maze representation built from simple text rows."""

    rows: tuple[str, ...]
    walls: frozenset[Pos]
    pellets: frozenset[Pos]
    power_pellets: frozenset[Pos]
    player_start: Pos

    @classmethod
    def from_rows(cls, rows: list[str] | tuple[str, ...]) -> "Maze":
        """Parse walls, pellets, power pellets, and the player start."""
        if not rows:
            raise ValueError("Maze cannot be empty.")
        widths = {len(row) for row in rows}
        if len(widths) != 1:
            raise ValueError("All maze rows must have the same width.")

        walls: set[Pos] = set()
        pellets: set[Pos] = set()
        power_pellets: set[Pos] = set()
        player_start: Pos | None = None

        for y, row in enumerate(rows):
            for x, char in enumerate(row):
                pos = (x, y)
                if char == "#":
                    walls.add(pos)
                elif char == ".":
                    pellets.add(pos)
                elif char == "o":
                    power_pellets.add(pos)
                elif char == "P":
                    player_start = pos

        if player_start is None:
            raise ValueError("Maze must include a player start marked with P.")

        return cls(
            rows=tuple(rows),
            walls=frozenset(walls),
            pellets=frozenset(pellets),
            power_pellets=frozenset(power_pellets),
            player_start=player_start,
        )

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def height(self) -> int:
        return len(self.rows)

    def step(self, pos: Pos, direction: Direction) -> Pos:
        """Return the next cell in a direction, wrapping horizontally."""
        dx, dy = DIRECTIONS[direction]
        return ((pos[0] + dx) % self.width, pos[1] + dy)

    def can_move(self, pos: Pos, direction: Direction) -> bool:
        """Return whether moving from a cell in a direction is legal."""
        candidate = self.step(pos, direction)
        return 0 <= candidate[1] < self.height and candidate not in self.walls

    def neighbors(self, pos: Pos) -> list[Pos]:
        """Return all legal neighboring cells from a position."""
        result: list[Pos] = []
        for direction in DIRECTIONS:
            candidate = self.step(pos, direction)
            if 0 <= candidate[1] < self.height and candidate not in self.walls:
                result.append(candidate)
        return result


DEFAULT_MAZE = Maze.from_rows(MAZE)
