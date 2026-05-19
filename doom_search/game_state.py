from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterable

from doom_search.algorithms import SearchResult, a_star, a_star_to_nearest_goal, bfs
from doom_search.colors import sum_colors
from doom_search.entities import Direction, Ghost, Pos
from doom_search.level import DEFAULT_MAZE, Maze


@dataclass
class SearchSnapshot:
    player_hint: SearchResult
    ghost_searches: list[SearchResult]
    pellet_colors: dict[Pos, str]
    pellet_ghost_colors: dict[Pos, list[str]]


@dataclass
class GameState:
    maze: Maze = DEFAULT_MAZE
    pellets: set[Pos] = field(default_factory=set)
    power_pellets: set[Pos] = field(default_factory=set)
    ghosts: list[Ghost] = field(default_factory=list)
    player: Pos = (0, 0)
    direction: Direction = "Left"
    next_direction: Direction = "Left"
    score: int = 0
    lives: int = 3
    paused: bool = False
    game_over: bool = False
    win: bool = False

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.pellets = set(self.maze.pellets)
        self.power_pellets = set(self.maze.power_pellets)
        self.player = self.maze.player_start
        self.ghosts = [
            Ghost((9, 3), "#ff4d6d", "A*", (9, 3), "A*", "#5b1f2d", "#ff4d6d"),
            Ghost((11, 11), "#4cc9f0", "BFS", (11, 11), "BFS", "#183f4d", "#4cc9f0"),
        ]
        self.direction = "Left"
        self.next_direction = "Left"
        self.score = 0
        self.lives = 3
        self.paused = False
        self.game_over = False
        self.win = False

    def request_direction(self, direction: Direction) -> None:
        self.next_direction = direction

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def tick(self) -> None:
        if self.paused or self.game_over or self.win:
            return

        self.move_player()
        self.collect()
        self.move_ghosts()
        self.resolve_collisions()
        if not self.pellets and not self.power_pellets:
            self.win = True

    def move_player(self) -> None:
        if self.maze.can_move(self.player, self.next_direction):
            self.direction = self.next_direction
        if self.maze.can_move(self.player, self.direction):
            self.player = self.maze.step(self.player, self.direction)

    def collect(self) -> None:
        if self.player in self.pellets:
            self.pellets.remove(self.player)
            self.score += 10
        if self.player in self.power_pellets:
            self.power_pellets.remove(self.player)
            self.score += 50

    def move_ghosts(self) -> None:
        reserved = {ghost.pos for ghost in self.ghosts}
        for ghost in self.ghosts:
            reserved.discard(ghost.pos)
            result = self.ghost_search(ghost)
            candidates = [result.path[1]] if len(result.path) > 1 else []
            candidates.extend(neighbor for neighbor in self.maze.neighbors(ghost.pos) if neighbor not in candidates)
            ghost.pos = self.choose_ghost_step(ghost.pos, candidates, reserved)
            reserved.add(ghost.pos)

    def choose_ghost_step(self, current: Pos, candidates: Iterable[Pos], reserved: set[Pos]) -> Pos:
        for candidate in candidates:
            if candidate == self.player or candidate not in reserved:
                return candidate
        options = [candidate for candidate in candidates if candidate not in reserved]
        return random.choice(options) if options else current

    def resolve_collisions(self) -> None:
        if all(ghost.pos != self.player for ghost in self.ghosts):
            return
        self.lives -= 1
        if self.lives <= 0:
            self.game_over = True
            return
        self.player = self.maze.player_start
        self.direction = "Left"
        self.next_direction = "Left"
        for ghost in self.ghosts:
            ghost.pos = ghost.start

    def bfs(self, start: Pos, goal: Pos) -> SearchResult:
        return bfs(start, goal, self.maze.neighbors)

    def a_star(self, start: Pos, goal: Pos) -> SearchResult:
        return a_star(start, goal, self.maze.neighbors)

    def ghost_search(self, ghost: Ghost) -> SearchResult:
        if ghost.algorithm == "A*":
            return self.a_star(ghost.pos, self.player)
        return self.bfs(ghost.pos, self.player)

    def player_hint(self) -> SearchResult:
        return a_star_to_nearest_goal(self.player, self.pellets | self.power_pellets, self.maze.neighbors)

    def search_snapshot(self) -> SearchSnapshot:
        player_hint = self.player_hint()
        ghost_searches = [self.ghost_search(ghost) for ghost in self.ghosts]
        pellet_colors = self.searched_pellet_colors(ghost_searches)
        pellet_ghost_colors = self.searched_pellet_color_parts(ghost_searches)
        return SearchSnapshot(player_hint, ghost_searches, pellet_colors, pellet_ghost_colors)

    def searched_pellet_colors(self, ghost_searches: list[SearchResult]) -> dict[Pos, str]:
        return {pellet: sum_colors(colors) for pellet, colors in self.searched_pellet_color_parts(ghost_searches).items()}

    def searched_pellet_color_parts(self, ghost_searches: list[SearchResult]) -> dict[Pos, list[str]]:
        searchable_pellets = self.pellets | self.power_pellets
        color_parts: dict[Pos, list[str]] = {}
        for ghost, search in zip(self.ghosts, ghost_searches):
            searched_cells = search.explored | search.frontier | set(search.path)
            for pellet in searchable_pellets & searched_cells:
                color_parts.setdefault(pellet, []).append(ghost.color)
        return color_parts
