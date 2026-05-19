from __future__ import annotations

import heapq
import random
import tkinter as tk
from collections import deque
from dataclasses import dataclass
from typing import Iterable


CELL = 24
HUD_HEIGHT = 92
PANEL_WIDTH = 310
DEFAULT_TICK_MS = 320

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
class SearchResult:
    path: list[Pos]
    explored: set[Pos]
    came_from: dict[Pos, Pos | None]
    frontier: set[Pos]


@dataclass
class Ghost:
    pos: Pos
    color: str
    name: str
    start: Pos


class PacmanSearchGame:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Pac-Man: busqueda A*, BFS y arboles de decision")
        self.width = len(MAZE[0])
        self.height = len(MAZE)
        self.board_width = self.width * CELL
        self.board_height = self.height * CELL
        self.speed_ms = tk.IntVar(value=DEFAULT_TICK_MS)
        self.canvas = tk.Canvas(
            self.root,
            width=self.board_width + PANEL_WIDTH,
            height=self.board_height + HUD_HEIGHT,
            background="#050507",
            highlightthickness=0,
        )
        self.canvas.pack()
        self.speed_slider = tk.Scale(
            self.root,
            from_=80,
            to=850,
            resolution=10,
            orient="horizontal",
            variable=self.speed_ms,
            label="Velocidad: milisegundos por turno (mas alto = mas lento)",
            length=self.board_width + PANEL_WIDTH - 20,
        )
        self.speed_slider.pack(padx=8, pady=(2, 8))
        self.root.bind("<KeyPress>", self.on_key_press)

        self.show_hint = True
        self.show_ghost_paths = True
        self.show_tree = True
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
            Ghost((9, 3), "#ff4d6d", "Rojo", (9, 3)),
            Ghost((11, 3), "#4cc9f0", "Azul", (11, 3)),
            Ghost((9, 11), "#f8961e", "Naranja", (9, 11)),
            Ghost((11, 11), "#b5179e", "Rosa", (11, 11)),
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
        elif event.char in {"t", "T"}:
            self.show_tree = not self.show_tree
            self.draw()

    def run(self) -> None:
        self.root.after(self.speed_ms.get(), self.tick)
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
        self.root.after(self.speed_ms.get(), self.tick)

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
        reserved = {ghost.pos for ghost in self.ghosts}
        for ghost in self.ghosts:
            reserved.discard(ghost.pos)
            result = self.bfs(ghost.pos, self.pacman)
            candidates = [result.path[1]] if len(result.path) > 1 else []
            candidates.extend(neighbor for neighbor in self.neighbors(ghost.pos) if neighbor not in candidates)
            next_pos = self.choose_ghost_step(ghost.pos, candidates, reserved)
            ghost.pos = next_pos
            reserved.add(next_pos)

    def choose_ghost_step(self, current: Pos, candidates: Iterable[Pos], reserved: set[Pos]) -> Pos:
        for candidate in candidates:
            if candidate == self.pacman or candidate not in reserved:
                return candidate
        options = [candidate for candidate in candidates if candidate not in reserved]
        return random.choice(options) if options else current

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

        a_star = self.a_star_to_nearest_pellet()
        ghost_searches = [self.bfs(ghost.pos, self.pacman) for ghost in self.ghosts]

        if self.show_hint:
            self.draw_cells(a_star.explored, "#143642", radius=4)
            self.draw_cells(a_star.frontier, "#265f73", radius=4)
            self.draw_cells(a_star.path[1:], "#2ec4b6", radius=7)

        if self.show_ghost_paths:
            for ghost, search in zip(self.ghosts, ghost_searches):
                self.draw_cells(search.explored - set(search.path), self.fade(ghost.color), radius=3)
                self.draw_cells(search.path[1:-1], ghost.color, radius=4)

        if self.show_tree and ghost_searches:
            self.draw_search_tree(ghost_searches[0], "#ffb3c1")
            self.draw_search_tree(a_star, "#94d2bd", max_edges=32)

        pellet_colors = self.searched_pellet_colors(ghost_searches)
        self.draw_pellets(pellet_colors)
        self.draw_pacman()
        self.draw_ghosts()
        self.draw_hud(a_star, ghost_searches)
        self.draw_lesson_panel(a_star, ghost_searches)

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

    def draw_pellets(self, searched_colors: dict[Pos, str]) -> None:
        for pellet in self.pellets:
            color = searched_colors.get(pellet, "#f8fafc")
            radius = 5 if pellet in searched_colors else 3
            self.draw_cells([pellet], color, radius=radius)
        for pellet in self.power_pellets:
            color = searched_colors.get(pellet, "#fef08a")
            self.draw_cells([pellet], color, radius=8)

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
        occupied_count: dict[Pos, int] = {}
        for ghost in self.ghosts:
            index = occupied_count.get(ghost.pos, 0)
            occupied_count[ghost.pos] = index + 1
            offset_x = (index % 2) * 7 - (3 if index else 0)
            offset_y = (index // 2) * 7 - (3 if index else 0)
            x, y = self.center(ghost.pos)
            x += offset_x
            y += offset_y
            self.canvas.create_oval(
                x - 10,
                y - 10,
                x + 10,
                y + 10,
                fill=ghost.color,
                outline="#ffffff",
                width=1,
            )
            self.canvas.create_text(x, y + 1, text=ghost.name[0], fill="#fff", font=("Segoe UI", 8, "bold"))

    def draw_hud(self, a_star: SearchResult, ghost_searches: list[SearchResult]) -> None:
        top = self.board_height
        self.canvas.create_rectangle(0, top, self.board_width, top + HUD_HEIGHT, fill="#111827", outline="")
        state = "Pausa" if self.paused else "Jugando"
        if self.game_over:
            state = "Game over"
        elif self.win:
            state = "Ganaste"
        ghost_nodes = sum(len(search.explored) for search in ghost_searches)
        text = (
            f"Puntos: {self.score}   Vidas: {self.lives}   Estado: {state}   "
            f"Velocidad: {self.speed_ms.get()} ms"
        )
        self.canvas.create_text(12, top + 16, text=text, anchor="w", fill="#f9fafb", font=("Segoe UI", 10, "bold"))
        search_text = (
            f"A*: ruta {max(0, len(a_star.path) - 1)} pasos, {len(a_star.explored)} nodos | "
            f"BFS fantasmas: {ghost_nodes} nodos"
        )
        self.canvas.create_text(12, top + 40, text=search_text, anchor="w", fill="#cbd5e1", font=("Segoe UI", 9))
        controls = "Flechas/WASD mover | H A* | G BFS | T arbol | Espacio pausa | R reiniciar"
        self.canvas.create_text(12, top + 64, text=controls, anchor="w", fill="#cbd5e1", font=("Segoe UI", 9))
        if self.game_over or self.win:
            message = "Presiona R para reiniciar"
            self.canvas.create_text(
                self.board_width // 2,
                self.board_height // 2,
                text=message,
                fill="#ffffff",
                font=("Segoe UI", 20, "bold"),
            )

    def draw_lesson_panel(self, a_star: SearchResult, ghost_searches: list[SearchResult]) -> None:
        left = self.board_width
        self.canvas.create_rectangle(left, 0, left + PANEL_WIDTH, self.board_height + HUD_HEIGHT, fill="#0f172a", outline="")
        x = left + 16
        y = 20
        lines = [
            "Como leer la busqueda",
            "",
            "A* de Pac-Man",
            "Verde claro: ruta elegida al pellet.",
            "Verde oscuro: nodos ya evaluados.",
            "Verde medio: frontera pendiente.",
            "",
            "BFS de fantasmas",
            "Color fuerte: camino mas corto.",
            "Color tenue: opciones exploradas.",
            "Dots con color: pellets buscados.",
            "Si varios fantasmas buscan el",
            "mismo dot, sus colores se suman.",
            "",
            "Arbol de decision",
            "Lineas = padre -> hijo.",
            "Cada nodo representa una posicion.",
            "La ruta final se reconstruye",
            "regresando por los padres.",
            "",
            f"A* exploro {len(a_star.explored)} nodos.",
            f"BFS rojo exploro {len(ghost_searches[0].explored) if ghost_searches else 0} nodos.",
            "",
            "Baja la velocidad para ver",
            "como se recalcula cada turno.",
        ]
        for index, line in enumerate(lines):
            font = ("Segoe UI", 11, "bold") if index in {0, 2, 7, 14} else ("Segoe UI", 9)
            fill = "#f8fafc" if index in {0, 2, 7, 14} else "#cbd5e1"
            self.canvas.create_text(x, y, text=line, anchor="nw", fill=fill, font=font, width=PANEL_WIDTH - 30)
            y += 22 if line else 10

    def draw_cells(self, cells: Iterable[Pos], color: str, radius: int) -> None:
        for pos in cells:
            x, y = self.center(pos)
            self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=color, outline="")

    def draw_search_tree(self, result: SearchResult, color: str, max_edges: int = 45) -> None:
        edges = [(child, parent) for child, parent in result.came_from.items() if parent is not None]
        for child, parent in edges[:max_edges]:
            x1, y1 = self.center(parent)
            x2, y2 = self.center(child)
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=1, arrow=tk.LAST)

    def searched_pellet_colors(self, ghost_searches: list[SearchResult]) -> dict[Pos, str]:
        searchable_pellets = self.pellets | self.power_pellets
        color_parts: dict[Pos, list[str]] = {}
        for ghost, search in zip(self.ghosts, ghost_searches):
            searched_cells = search.explored | search.frontier | set(search.path)
            for pellet in searchable_pellets & searched_cells:
                color_parts.setdefault(pellet, []).append(ghost.color)
        return {pellet: self.sum_colors(colors) for pellet, colors in color_parts.items()}

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

    def bfs(self, start: Pos, goal: Pos) -> SearchResult:
        queue: deque[Pos] = deque([start])
        came_from: dict[Pos, Pos | None] = {start: None}
        explored: set[Pos] = set()
        frontier: set[Pos] = {start}

        while queue:
            current = queue.popleft()
            frontier.discard(current)
            explored.add(current)
            if current == goal:
                return SearchResult(self.reconstruct_path(came_from, current), explored, came_from, frontier)
            for neighbor in self.neighbors(current):
                if neighbor in came_from:
                    continue
                came_from[neighbor] = current
                frontier.add(neighbor)
                queue.append(neighbor)
        return SearchResult([start], explored, came_from, frontier)

    def a_star_to_nearest_pellet(self) -> SearchResult:
        goals = self.pellets | self.power_pellets
        if not goals:
            return SearchResult([self.pacman], set(), {self.pacman: None}, set())

        open_heap: list[tuple[int, int, Pos]] = []
        heapq.heappush(open_heap, (0, 0, self.pacman))
        came_from: dict[Pos, Pos | None] = {self.pacman: None}
        best_cost: dict[Pos, int] = {self.pacman: 0}
        explored: set[Pos] = set()
        frontier: set[Pos] = {self.pacman}
        tie_breaker = 0

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            frontier.discard(current)
            if current in explored:
                continue
            explored.add(current)
            if current in goals:
                return SearchResult(self.reconstruct_path(came_from, current), explored, came_from, frontier)
            for neighbor in self.neighbors(current):
                new_cost = best_cost[current] + 1
                if new_cost >= best_cost.get(neighbor, 10**9):
                    continue
                best_cost[neighbor] = new_cost
                came_from[neighbor] = current
                tie_breaker += 1
                priority = new_cost + self.closest_goal_distance(neighbor, goals)
                frontier.add(neighbor)
                heapq.heappush(open_heap, (priority, tie_breaker, neighbor))
        return SearchResult([self.pacman], explored, came_from, frontier)

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

    def fade(self, color: str) -> str:
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
        return f"#{red // 3:02x}{green // 3:02x}{blue // 3:02x}"

    def sum_colors(self, colors: Iterable[str]) -> str:
        red = 0
        green = 0
        blue = 0
        for color in colors:
            red += int(color[1:3], 16)
            green += int(color[3:5], 16)
            blue += int(color[5:7], 16)
        return f"#{min(red, 255):02x}{min(green, 255):02x}{min(blue, 255):02x}"


if __name__ == "__main__":
    PacmanSearchGame().run()
