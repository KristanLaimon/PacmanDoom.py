"""Frame-to-frame interpolation for board movement."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from doom_search.entities import Direction, Pos
from doom_search.game_state import GameState
from doom_search.geometry import normalize_angle
from doom_search.settings import DIRECTION_ANGLES

FloatPos = tuple[float, float]


@dataclass
class BoardAnimator:
    """Keeps smooth visual positions separate from grid-based game state."""

    state: GameState
    tick_ms: int
    move_started_at: int
    player_start: FloatPos = field(init=False)
    player_end: FloatPos = field(init=False)
    player_pos: FloatPos = field(init=False)
    ghost_starts: list[FloatPos] = field(init=False)
    ghost_ends: list[FloatPos] = field(init=False)
    ghost_positions: list[FloatPos] = field(init=False)
    angle: float = field(init=False)
    angle_start: float = field(init=False)
    angle_end: float = field(init=False)
    turn_started_at: int = field(init=False)
    turn_duration: int = field(init=False)

    def __post_init__(self) -> None:
        self.turn_started_at = self.move_started_at
        self.turn_duration = self.tick_ms
        self.snap_all()

    def begin_turn(self, previous: Direction, current: Direction, now: int) -> None:
        """Animate Pac-Man's mouth direction when the requested direction changes."""
        if previous == current:
            return
        self.update_angle(now)
        self.angle_start = self.angle
        self.angle_end = self.angle + normalize_angle(DIRECTION_ANGLES[current] - self.angle)
        self.turn_started_at = now
        self.turn_duration = max(95, min(190, int(self.tick_ms * 0.58)))

    def begin_player_move(self, previous: Pos, current: Pos, now: int) -> None:
        """Start interpolation for the player, including tunnel wrap movement."""
        animation = self._cell_animation(previous, current)
        if animation is None:
            self.snap_player()
            return
        self.player_start, self.player_end = animation
        self.move_started_at = now

    def begin_ghost_moves(self, previous: list[Pos], current: list[Pos], now: int) -> None:
        """Start interpolation for every ghost."""
        self.ghost_starts = []
        self.ghost_ends = []
        self.move_started_at = now
        for old_pos, new_pos in zip(previous, current):
            animation = self._cell_animation(old_pos, new_pos)
            if animation is None:
                start = (float(new_pos[0]), float(new_pos[1]))
                end = start
            else:
                start, end = animation
            self.ghost_starts.append(start)
            self.ghost_ends.append(end)

    def update(self, now: int) -> None:
        """Refresh every interpolated value for the current frame."""
        eased = self._move_progress(now)
        self.player_pos = self._interpolate(self.player_start, self.player_end, eased)
        self.ghost_positions = [
            self._interpolate(start, end, eased)
            for start, end in zip(self.ghost_starts, self.ghost_ends)
        ]
        self.update_angle(now)

    def update_angle(self, now: int) -> None:
        """Refresh the interpolated facing angle."""
        elapsed = max(0, now - self.turn_started_at)
        progress = min(1.0, elapsed / self.turn_duration)
        eased = 1 - (1 - progress) ** 4
        self.angle = normalize_angle(self.angle_start + (self.angle_end - self.angle_start) * eased)

    def snap_all(self) -> None:
        """Synchronize every visual value to the current game state."""
        self.snap_player()
        self.snap_ghosts()
        self.snap_angle()

    def snap_player(self) -> None:
        """Synchronize the player visual position to the current grid cell."""
        current = (float(self.state.player[0]), float(self.state.player[1]))
        self.player_start = current
        self.player_end = current
        self.player_pos = current

    def snap_ghosts(self) -> None:
        """Synchronize ghost visual positions to their current grid cells."""
        positions = [(float(ghost.pos[0]), float(ghost.pos[1])) for ghost in self.state.ghosts]
        self.ghost_starts = positions
        self.ghost_ends = positions
        self.ghost_positions = positions

    def snap_angle(self) -> None:
        """Synchronize the visual angle to the player's current direction."""
        self.angle = DIRECTION_ANGLES[self.state.direction]
        self.angle_start = self.angle
        self.angle_end = self.angle

    def ghost_sprite_key(self, index: int) -> str:
        """Return the best directional sprite key for a ghost's current movement."""
        if index >= len(self.ghost_starts) or index >= len(self.ghost_ends):
            return "ghost_right"
        start = self.ghost_starts[index]
        end = self.ghost_ends[index]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        if abs(dx) > self.state.maze.width / 2:
            dx = -math.copysign(1.0, dx)
        if abs(dx) >= abs(dy) and abs(dx) > 0.01:
            return "ghost_right" if dx > 0 else "ghost_left"
        if abs(dy) > 0.01:
            return "ghost_down" if dy > 0 else "ghost_up"
        return "ghost_right"

    def _cell_animation(self, previous: Pos, current: Pos) -> tuple[FloatPos, FloatPos] | None:
        wrapped_dx = abs(current[0] - previous[0])
        moved_through_tunnel = wrapped_dx == self.state.maze.width - 1 and current[1] == previous[1]
        moved_one_cell = abs(current[0] - previous[0]) + abs(current[1] - previous[1]) == 1
        if previous == current or not (moved_one_cell or moved_through_tunnel):
            return None

        start_x, start_y = float(previous[0]), float(previous[1])
        end_x, end_y = float(current[0]), float(current[1])
        if abs(end_x - start_x) > self.state.maze.width / 2:
            if end_x < start_x:
                end_x += self.state.maze.width
            else:
                start_x += self.state.maze.width
        return (start_x, start_y), (end_x, end_y)

    def _move_progress(self, now: int) -> float:
        elapsed = max(0, now - self.move_started_at)
        progress = min(1.0, elapsed / max(80, self.tick_ms))
        return progress * progress * (3.0 - 2.0 * progress)

    def _interpolate(self, start: FloatPos, end: FloatPos, progress: float) -> FloatPos:
        x = start[0] + (end[0] - start[0]) * progress
        y = start[1] + (end[1] - start[1]) * progress
        return (x % self.state.maze.width, y)
