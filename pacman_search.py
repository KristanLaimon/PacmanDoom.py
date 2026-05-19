from __future__ import annotations

import heapq
import random
import tkinter as tk
from collections import deque
from dataclasses import dataclass
from typing import Iterable


CELL = 24
TICK_MS = 145

MAZE = [
    "#####################",
    "#.........#.........#",
    "#.###.###.#.###.###.#",
    "#o# #.#     #.# #.#o#",
    "#.###.#.###.#.###.#.#",
    "#.....#..#..#.....#.#",
    "#####.##.#.##.#####.#",
    "    #....P....#     #",
    "#####.#.###.#.#####.#",
    "#.....#..#..#.....#.#",
    "#.###.#.###.#.###.#.#",
    "#o# #.#     #.# #.#o#",
    "#.###.###.#.###.###.#",
    "#.........#.........#",
    "#####################",
]

DIRECTIONS = {
    "Up": (0, -1),
    "Down": (0, 1),
    "Left": (-1, 0),
    "Right": (1, 0),
}

KEY_TO_DIRECTION = {
    "Up": "Up",
    "Down": "Down",
    "Left": "Left",
    "Right": "Right",
    "w": "Up",
    "W": "Up",
    "s": "Down",
    "S": "Down",
    "a": "Left",
    "A": "Left",
    "d": "Right",
    "D": "Right",
}

Pos = tuple[int, int]


@dataclass
class Ghost:
    pos: Pos
    color: str
    start: Pos
    scatter_target: Pos


class PacmanSearchGame:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Pac-Man: busqueda A* y BFS")
        self.width = len(MAZE[0])
        self.height = len(MAZE)
        self.canvas = tk.Canvas(
            self.root,
            width=self.width * CELL,
            height=self.height * CELL + 58,
            background="#050507",
            highlightthickness=0,
        )
        self.canvas.pack()
        self.root.bind("<KeyPress>", self.on_key_press)

        self.show_hint = True
        self.show_ghost_paths = True
        self.paused = False
        self.reset()

    def reset(self) -> None:
        self.walls: set[Pos] = set()
        self.pellets: set[Pos] = set()
        self.power_pellets: set[Pos] = set()
        self.pacman: Pos = (10, 7)
        for y, row in enumerate(MAZE):
            for x, char in enumerate(row):
                if char == "#":
                    self.walls.add((x, y))
                elif char == ".":
                    self.pellets.add((x, y))
                elif char == "o":
                    self.power_pellets.add((x, y))
                elif char == "P":
                    self.pacman = (x, y)

        self.ghosts = [
            Ghost((9, 3), "#ff4d6d", (9, 3), (1, 1)),
            Ghost((11, 3), "#4cc9f0", (11, 3), (19, 1)),
            Ghost((9, 11), "#f8961e", (9, 11), (1, 13)),
            Ghost((11, 11), "#b5179e", (11, 11), (19, 13)),
        ]
        self.score = 0
        self.lives = 3
        self.direction = "Left"
        self.next_direction = "Left"
        self.game_over = False
        self.win = False
        self.draw()

    def on_key_press(self, event: tk.Event) -> None:
        key = event.keysym if event.keysym in KEY_TO_DIRECTION else event.char
        if key in KEY_TO_DIRECTION:
            self.next_direction = KEY_TO_DIRECTION[key]
        elif event.keysym == "space":
            self.paused = not self.paused
            self.draw()
        elif event.char in {"r", "R"}:
            self.reset()
        elif event.char in {"h", "H"}:
            self.show_hint = not self.show_hint
            self.draw()
        elif event.char in {"g", "G"}:
            self.show_ghost_paths = not self.show_ghost_paths
            self.draw()

    def run(self) -> None:
        self.root.after(TICK_MS, self.tick)
        self.root.mainloop()

    def tick(self) -> None:
        if not self.paused and not self.game_over and not self.win:
            self.move_pacman()
            self.collect()
            self.move_ghosts()
            self.resolve_collisions()
            if not self.pellets and not self.power_pellets:
                self.win = True
            self.draw()
        self.root.after(TICK_MS, self.tick)

    def move_pacman(self) -> None:
        if self.can_move(self.pacman, self.next_direction):
            self.direction = self.next_direction
        if self.can_move(self.pacman, self.direction):
            self.pacman = self.step(self.pacman, self.direction)

    def collect(self) -> None:
        if self.pacman in self.pellets:
            self.pellets.remove(self.pacman)
            self.score += 10
        if self.pacman in self.power_pellets:
            self.power_pellets.remove(self.pacman)
            self.score += 50

    def move_ghosts(self) -> None:
        for ghost in self.ghosts:
            path = self.bfs(ghost.pos, self.pacman)
            if len(path) > 1:
                ghost.pos = path[1]
            else:
                options = [n for n in self.neighbors(ghost.pos)]
                if options:
                    ghost.pos = random.choice(options)

    def resolve_collisions(self) -> None:
        if all(ghost.pos != self.pacman for ghost in self.ghosts):
            return
        self.lives -= 1
        if self.lives <= 0:
            self.game_over = True
            return
        self.pacman = (10, 7)
        self.direction = "Left"
        self.next_direction = "Left"
        for ghost in self.ghosts:
            ghost.pos = ghost.start

    def draw(self) -> None:
        self.canvas.delete("all")
        self.draw_maze()

        hint_path, explored = self.a_star_to_nearest_pellet()
        if self.show_hint:
            self.draw_cells(explored, "#143642", radius=4)
            self.draw_cells(hint_path[1:], "#2ec4b6", radius=7)

        if self.show_ghost_paths:
            for ghost in self.ghosts:
                path = self.bfs(ghost.pos, self.pacman)
                self.draw_cells(path[1:-1], ghost.color, radius=3)

        self.draw_pellets()
        self.draw_pacman()
        self.draw_ghosts()
        self.draw_hud(len(explored), max(0, len(hint_path) - 1))

    def draw_maze(self) -> None:
        for x, y in self.walls:
            x1, y1 = x * CELL, y * CELL
            self.canvas.create_rectangle(
                x1,
                y1,
                x1 + CELL,
                y1 + CELL,
                fill="#1d4ed8",
                outline="#60a5fa",
                width=1,
            )

    def draw_pellets(self) -> None:
        self.draw_cells(self.pellets, "#f8fafc", radius=3)
        self.draw_cells(self.power_pellets, "#fef08a", radius=7)

    def draw_pacman(self) -> None:
        x, y = self.center(self.pacman)
        self.canvas.create_oval(
            x - 10,
            y - 10,
            x + 10,
            y + 10,
            fill="#ffd60a",
            outline="#fff7ad",
            width=2,
        )
        eye_x = x + (4 if self.direction != "Left" else -4)
        self.canvas.create_oval(eye_x - 2, y - 6, eye_x + 2, y - 2, fill="#111")

    def draw_ghosts(self) -> None:
        for ghost in self.ghosts:
            x, y = self.center(ghost.pos)
            self.canvas.create_oval(
                x - 10,
                y - 10,
                x + 10,
                y + 10,
                fill=ghost.color,
                outline="#ffffff",
                width=1,
            )
            self.canvas.create_oval(x - 5, y - 4, x - 1, y, fill="#fff", outline="")
            self.canvas.create_oval(x + 2, y - 4, x + 6, y, fill="#fff", outline="")

    def draw_hud(self, explored_count: int, hint_steps: int) -> None:
        top = self.height * CELL
        self.canvas.create_rectangle(0, top, self.width * CELL, top + 58, fill="#111827", outline="")
        state = "Pausa" if self.paused else "Jugando"
        if self.game_over:
            state = "Game over"
        elif self.win:
            state = "Ganaste"
        text = (
            f"Puntos: {self.score}   Vidas: {self.lives}   Estado: {state}   "
            f"A*: {hint_steps} pasos, {explored_count} nodos"
        )
        self.canvas.create_text(12, top + 16, text=text, anchor="w", fill="#f9fafb", font=("Segoe UI", 10, "bold"))
        controls = "Flechas/WASD mover | H ruta A* | G rutas BFS | Espacio pausa | R reiniciar"
        self.canvas.create_text(12, top + 40, text=controls, anchor="w", fill="#cbd5e1", font=("Segoe UI", 9))
        if self.game_over or self.win:
            message = "Presiona R para reiniciar"
            self.canvas.create_text(
                self.width * CELL // 2,
                self.height * CELL // 2,
                text=message,
                fill="#ffffff",
                font=("Segoe UI", 20, "bold"),
            )

    def draw_cells(self, cells: Iterable[Pos], color: str, radius: int) -> None:
        for pos in cells:
            x, y = self.center(pos)
            self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=color, outline="")

    def can_move(self, pos: Pos, direction: str) -> bool:
        return self.step(pos, direction) not in self.walls

    def step(self, pos: Pos, direction: str) -> Pos:
        dx, dy = DIRECTIONS[direction]
        x = (pos[0] + dx) % self.width
        y = pos[1] + dy
        return (x, y)

    def neighbors(self, pos: Pos) -> list[Pos]:
        result = []
        for dx, dy in DIRECTIONS.values():
            candidate = ((pos[0] + dx) % self.width, pos[1] + dy)
            if 0 <= candidate[1] < self.height and candidate not in self.walls:
                result.append(candidate)
        return result

    def bfs(self, start: Pos, goal: Pos) -> list[Pos]:
        if start == goal:
            return [start]
        queue: deque[Pos] = deque([start])
        came_from: dict[Pos, Pos | None] = {start: None}
        while queue:
            current = queue.popleft()
            for neighbor in self.neighbors(current):
                if neighbor in came_from:
                    continue
                came_from[neighbor] = current
                if neighbor == goal:
                    return self.reconstruct_path(came_from, neighbor)
                queue.append(neighbor)
        return [start]

    def a_star_to_nearest_pellet(self) -> tuple[list[Pos], set[Pos]]:
        goals = self.pellets | self.power_pellets
        if not goals:
            return [self.pacman], set()

        open_heap: list[tuple[int, int, Pos]] = []
        heapq.heappush(open_heap, (0, 0, self.pacman))
        came_from: dict[Pos, Pos | None] = {self.pacman: None}
        best_cost: dict[Pos, int] = {self.pacman: 0}
        explored: set[Pos] = set()
        tie_breaker = 0

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in explored:
                continue
            explored.add(current)
            if current in goals:
                return self.reconstruct_path(came_from, current), explored
            for neighbor in self.neighbors(current):
                new_cost = best_cost[current] + 1
                if new_cost >= best_cost.get(neighbor, 10**9):
                    continue
                best_cost[neighbor] = new_cost
                came_from[neighbor] = current
                tie_breaker += 1
                priority = new_cost + self.closest_goal_distance(neighbor, goals)
                heapq.heappush(open_heap, (priority, tie_breaker, neighbor))
        return [self.pacman], explored

    def closest_goal_distance(self, pos: Pos, goals: set[Pos]) -> int:
        return min(abs(pos[0] - goal[0]) + abs(pos[1] - goal[1]) for goal in goals)

    def reconstruct_path(self, came_from: dict[Pos, Pos | None], current: Pos) -> list[Pos]:
        path = [current]
        while came_from[current] is not None:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def center(self, pos: Pos) -> tuple[int, int]:
        return (pos[0] * CELL + CELL // 2, pos[1] * CELL + CELL // 2)


if __name__ == "__main__":
    PacmanSearchGame().run()
