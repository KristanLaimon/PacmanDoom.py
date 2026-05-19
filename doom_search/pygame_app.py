from __future__ import annotations

import math

import pygame

from doom_search.algorithms import SearchResult
from doom_search.colors import fade
from doom_search.entities import Pos
from doom_search.game_state import GameState, SearchSnapshot
from doom_search.level import KEY_TO_DIRECTION

VIEW_WIDTH = 640
VIEW_HEIGHT = 420
MAP_CELL = 14
HUD_HEIGHT = 92
PANEL_WIDTH = 360
DEFAULT_TICK_MS = 320
SMOOTH_VIEW_FPS = 60
FOV = math.radians(68)
MAX_VIEW_DISTANCE = 16.0
RAY_STEP = 4

VIEW_ANGLES = {
    "Right": 0.0,
    "Down": math.pi / 2,
    "Left": math.pi,
    "Up": -math.pi / 2,
}


class PygameSearchGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("DOOM Search: A* y BFS en tiempo real")

        self.state = GameState()
        self.view_width = VIEW_WIDTH
        self.view_height = VIEW_HEIGHT
        self.map_width = self.state.maze.width * MAP_CELL
        self.map_height = self.state.maze.height * MAP_CELL
        self.screen = pygame.display.set_mode((self.view_width + PANEL_WIDTH, self.view_height + HUD_HEIGHT))
        self.clock = pygame.time.Clock()
        self.small_font = pygame.font.SysFont("Segoe UI", 13)
        self.bold_font = pygame.font.SysFont("Segoe UI", 17, bold=True)
        self.title_font = pygame.font.SysFont("Segoe UI", 22, bold=True)

        self.show_hint = True
        self.show_ghost_paths = True
        self.show_tree = True
        self.tick_ms = DEFAULT_TICK_MS
        self.last_tick = pygame.time.get_ticks()
        self.visual_player_start = (float(self.state.player[0]), float(self.state.player[1]))
        self.visual_player_end = self.visual_player_start
        self.visual_player_pos = self.visual_player_start
        self.visual_move_start = self.last_tick
        self.visual_move_duration = self.tick_ms

    def run(self) -> None:
        running = True
        while running:
            running = self.handle_events()
            now = pygame.time.get_ticks()
            if now - self.last_tick >= self.tick_ms:
                previous_player = self.state.player
                self.state.tick()
                self.begin_player_animation(previous_player, self.state.player, now)
                self.last_tick = now
            self.update_visual_player(now)
            self.draw()
            self.clock.tick(SMOOTH_VIEW_FPS)
        pygame.quit()

    def begin_player_animation(self, previous: Pos, current: Pos, now: int) -> None:
        wrapped_dx = abs(current[0] - previous[0])
        moved_through_tunnel = wrapped_dx == self.state.maze.width - 1 and current[1] == previous[1]
        moved_one_cell = abs(current[0] - previous[0]) + abs(current[1] - previous[1]) == 1
        if previous == current or not (moved_one_cell or moved_through_tunnel):
            self.snap_visual_player()
            return

        start_x, start_y = float(previous[0]), float(previous[1])
        end_x, end_y = float(current[0]), float(current[1])
        if abs(end_x - start_x) > self.state.maze.width / 2:
            if end_x < start_x:
                end_x += self.state.maze.width
            else:
                start_x += self.state.maze.width
        self.visual_player_start = (start_x, start_y)
        self.visual_player_end = (end_x, end_y)
        self.visual_move_start = now
        self.visual_move_duration = max(80, self.tick_ms)

    def snap_visual_player(self) -> None:
        current = (float(self.state.player[0]), float(self.state.player[1]))
        self.visual_player_start = current
        self.visual_player_end = current
        self.visual_player_pos = current

    def update_visual_player(self, now: int) -> None:
        elapsed = max(0, now - self.visual_move_start)
        progress = min(1.0, elapsed / self.visual_move_duration)
        eased = progress * progress * (3.0 - 2.0 * progress)
        x = self.visual_player_start[0] + (self.visual_player_end[0] - self.visual_player_start[0]) * eased
        y = self.visual_player_start[1] + (self.visual_player_end[1] - self.visual_player_start[1]) * eased
        self.visual_player_pos = (x % self.state.maze.width, y)

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                self.handle_key(event)
        return True

    def handle_key(self, event: pygame.event.Event) -> None:
        key_name = pygame.key.name(event.key).lower()
        if key_name in KEY_TO_DIRECTION:
            self.state.request_direction(KEY_TO_DIRECTION[key_name])
        elif event.key == pygame.K_SPACE:
            self.state.toggle_pause()
        elif event.key == pygame.K_r:
            self.state.reset()
            self.snap_visual_player()
        elif event.key == pygame.K_h:
            self.show_hint = not self.show_hint
        elif event.key == pygame.K_g:
            self.show_ghost_paths = not self.show_ghost_paths
        elif event.key == pygame.K_t:
            self.show_tree = not self.show_tree
        elif event.key in {pygame.K_MINUS, pygame.K_KP_MINUS}:
            self.tick_ms = min(850, self.tick_ms + 30)
        elif event.key in {pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS}:
            self.tick_ms = max(80, self.tick_ms - 30)

    def draw(self) -> None:
        snapshot = self.state.search_snapshot()
        self.screen.fill(hex_color("#050507"))
        self.draw_player_window()
        self.draw_map_window(snapshot)
        self.draw_hud(snapshot)
        pygame.display.flip()

    def draw_player_window(self) -> None:
        self.draw_sky_and_floor()
        self.draw_raycast_walls()
        self.draw_visible_sprites()
        self.draw_crosshair()
        direction_name = {"Left": "Oeste", "Right": "Este", "Up": "Norte", "Down": "Sur"}[self.state.direction]
        self.draw_text(f"Vista 3D - mirando {direction_name}", 12, 12, self.bold_font, "#f8fafc")

    def draw_sky_and_floor(self) -> None:
        horizon = self.view_height // 2
        for y in range(horizon):
            shade = int(14 + 34 * (y / max(1, horizon)))
            pygame.draw.line(self.screen, (shade // 2, shade, shade + 18), (0, y), (self.view_width, y))
        for y in range(horizon, self.view_height):
            shade = int(42 - 24 * ((y - horizon) / max(1, horizon)))
            pygame.draw.line(self.screen, (shade + 14, shade, max(12, shade - 8)), (0, y), (self.view_width, y))

    def draw_raycast_walls(self) -> None:
        view_angle = VIEW_ANGLES[self.state.direction]
        for x in range(0, self.view_width, RAY_STEP):
            ray_angle = view_angle - FOV / 2 + FOV * (x / self.view_width)
            distance, hit_axis = self.cast_ray(ray_angle)
            corrected = max(0.08, distance * math.cos(ray_angle - view_angle))
            wall_height = min(self.view_height * 1.8, self.view_height / corrected)
            top = int((self.view_height - wall_height) / 2)
            rect = pygame.Rect(x, top, RAY_STEP + 1, int(wall_height))
            shade = max(42, min(210, int(220 - corrected * 23)))
            color = (shade // 3, shade // 2, shade)
            if hit_axis == "y":
                color = (max(25, color[0] - 16), max(25, color[1] - 16), max(50, color[2] - 12))
            pygame.draw.rect(self.screen, color, rect)

    def cast_ray(self, angle: float) -> tuple[float, str]:
        origin_x = self.visual_player_pos[0] + 0.5
        origin_y = self.visual_player_pos[1] + 0.5
        step_x = math.cos(angle) * 0.035
        step_y = math.sin(angle) * 0.035
        ray_x = origin_x
        ray_y = origin_y
        previous_cell = (math.floor(origin_x) % self.state.maze.width, math.floor(origin_y))
        distance = 0.0

        while distance < MAX_VIEW_DISTANCE:
            ray_x += step_x
            ray_y += step_y
            distance += 0.035
            if ray_y < 0 or ray_y >= self.state.maze.height:
                return distance, "y"

            cell = (math.floor(ray_x) % self.state.maze.width, math.floor(ray_y))
            if cell in self.state.maze.walls:
                return distance, "x" if cell[0] != previous_cell[0] else "y"
            previous_cell = cell

        return MAX_VIEW_DISTANCE, "x"

    def draw_visible_sprites(self) -> None:
        sprites: list[tuple[float, Pos, str, str]] = []
        for pellet in self.state.pellets:
            sprites.append((self.sprite_distance(pellet), pellet, "#f8fafc", "pellet"))
        for pellet in self.state.power_pellets:
            sprites.append((self.sprite_distance(pellet), pellet, "#fef08a", "power"))
        for ghost in self.state.ghosts:
            sprites.append((self.sprite_distance(ghost.pos), ghost.pos, ghost.color, "enemy"))

        for _, pos, color, kind in sorted(sprites, reverse=True):
            projection = self.project_sprite(pos)
            if projection is None:
                continue
            screen_x, depth = projection
            if kind == "enemy":
                size = int(max(22, min(120, self.view_height / depth * 0.42)))
                rect = pygame.Rect(0, 0, size, int(size * 1.15))
                rect.midbottom = (screen_x, self.view_height - 34)
                pygame.draw.ellipse(self.screen, hex_color(color), rect)
                pygame.draw.ellipse(self.screen, hex_color("#ffffff"), rect, 2)
            else:
                scale = 0.055 if kind == "pellet" else 0.09
                radius = int(max(4, min(18, self.view_height / depth * scale)))
                y = int(self.view_height // 2 + self.view_height / depth * 0.12)
                pygame.draw.circle(self.screen, hex_color("#020617"), (screen_x, y), radius + 3)
                pygame.draw.circle(self.screen, hex_color(color), (screen_x, y), radius)
                pygame.draw.circle(self.screen, hex_color("#111827"), (screen_x, y), radius + 1, 1)
                if kind == "pellet":
                    pygame.draw.circle(self.screen, hex_color("#ffffff"), (screen_x, y), max(1, radius // 2))
                else:
                    pygame.draw.circle(self.screen, hex_color("#ffffff"), (screen_x, y), radius + 4, 1)

    def project_sprite(self, pos: Pos) -> tuple[int, float] | None:
        dx, dy = self.shortest_delta_to(pos)
        distance = max(0.01, math.hypot(dx, dy))
        angle_to_sprite = math.atan2(dy, dx)
        angle_diff = normalize_angle(angle_to_sprite - VIEW_ANGLES[self.state.direction])
        if abs(angle_diff) > FOV * 0.58:
            return None

        depth = distance * math.cos(angle_diff)
        if depth <= 0.2:
            return None
        wall_distance, _ = self.cast_ray(angle_to_sprite)
        if wall_distance + 0.35 < distance:
            return None

        screen_x = int(self.view_width / 2 + (angle_diff / (FOV / 2)) * (self.view_width / 2))
        return screen_x, depth

    def draw_crosshair(self) -> None:
        center = (self.view_width // 2, self.view_height // 2)
        pygame.draw.line(self.screen, hex_color("#d1d5db"), (center[0] - 9, center[1]), (center[0] + 9, center[1]), 1)
        pygame.draw.line(self.screen, hex_color("#d1d5db"), (center[0], center[1] - 9), (center[0], center[1] + 9), 1)

    def draw_map_window(self, snapshot: SearchSnapshot) -> None:
        left = self.view_width
        pygame.draw.rect(self.screen, hex_color("#0f172a"), (left, 0, PANEL_WIDTH, self.view_height + HUD_HEIGHT))
        self.draw_text("Mapa y busqueda", left + 16, 16, self.title_font, "#f8fafc")

        origin = (left + 18, 58)
        pygame.draw.rect(
            self.screen,
            hex_color("#020617"),
            (origin[0] - 8, origin[1] - 8, self.map_width + 16, self.map_height + 16),
        )
        self.draw_map_maze(origin)
        self.draw_search_layers(snapshot, origin)
        self.draw_map_pellets(snapshot, origin)
        self.draw_map_player(origin)
        self.draw_map_ghosts(origin)
        self.draw_lesson_panel(snapshot, left, origin[1] + self.map_height + 24)

    def draw_search_layers(self, snapshot: SearchSnapshot, origin: tuple[int, int]) -> None:
        if self.show_hint:
            self.draw_map_cells(snapshot.player_hint.explored, "#143642", 3, origin)
            self.draw_map_cells(snapshot.player_hint.frontier, "#265f73", 3, origin)
            self.draw_map_cells(snapshot.player_hint.path[1:], "#2ec4b6", 5, origin)

        if self.show_ghost_paths:
            for ghost, search in zip(self.state.ghosts, snapshot.ghost_searches):
                self.draw_map_cells(search.explored - set(search.path), ghost.search_color, 2, origin)
                self.draw_map_cells(search.frontier, fade(ghost.path_color, 2), 2, origin)
                self.draw_map_cells(search.path[1:-1], ghost.path_color, 4, origin)

        if self.show_tree and snapshot.ghost_searches:
            self.draw_search_tree(snapshot.ghost_searches[0], self.state.ghosts[0].path_color, origin)
            self.draw_search_tree(snapshot.player_hint, "#94d2bd", origin, max_edges=32)

    def draw_map_maze(self, origin: tuple[int, int]) -> None:
        for x, y in self.state.maze.walls:
            rect = pygame.Rect(origin[0] + x * MAP_CELL, origin[1] + y * MAP_CELL, MAP_CELL, MAP_CELL)
            pygame.draw.rect(self.screen, hex_color("#1d4ed8"), rect)
            pygame.draw.rect(self.screen, hex_color("#60a5fa"), rect, 1)

    def draw_map_pellets(self, snapshot: SearchSnapshot, origin: tuple[int, int]) -> None:
        for pellet in self.state.pellets:
            center = self.map_center(pellet, origin)
            pygame.draw.circle(self.screen, hex_color("#f8fafc"), center, 2)
            self.draw_pellet_search_rings(center, snapshot.pellet_ghost_colors.get(pellet, []))
        for pellet in self.state.power_pellets:
            center = self.map_center(pellet, origin)
            pygame.draw.circle(self.screen, hex_color("#fef08a"), center, 5)
            self.draw_pellet_search_rings(center, snapshot.pellet_ghost_colors.get(pellet, []), start_radius=8)

    def draw_pellet_search_rings(self, center: tuple[int, int], colors: list[str], start_radius: int = 5) -> None:
        for index, color in enumerate(colors[:4]):
            pygame.draw.circle(self.screen, hex_color(color), center, start_radius + index * 2, 1)

    def draw_map_player(self, origin: tuple[int, int]) -> None:
        x, y = self.map_center(self.state.player, origin)
        pygame.draw.circle(self.screen, hex_color("#ffd60a"), (x, y), 7)
        pygame.draw.circle(self.screen, hex_color("#fff7ad"), (x, y), 7, 2)
        angle = VIEW_ANGLES[self.state.direction]
        pygame.draw.line(self.screen, hex_color("#111111"), (x, y), (x + int(math.cos(angle) * 10), y + int(math.sin(angle) * 10)), 2)

    def draw_map_ghosts(self, origin: tuple[int, int]) -> None:
        for ghost in self.state.ghosts:
            center = self.map_center(ghost.pos, origin)
            pygame.draw.circle(self.screen, hex_color(ghost.color), center, 6)
            pygame.draw.circle(self.screen, hex_color("#ffffff"), center, 6, 1)
            self.draw_text(ghost.algorithm, center[0] + 8, center[1] - 8, self.small_font, "#f8fafc")

    def draw_hud(self, snapshot: SearchSnapshot) -> None:
        top = self.view_height
        pygame.draw.rect(self.screen, hex_color("#111827"), (0, top, self.view_width, HUD_HEIGHT))
        state = "Pausa" if self.state.paused else "Jugando"
        if self.state.game_over:
            state = "Game over"
        elif self.state.win:
            state = "Ganaste"

        ghost_nodes = sum(len(search.explored) for search in snapshot.ghost_searches)
        self.draw_text(
            f"Puntos: {self.state.score}   Vidas: {self.state.lives}   Estado: {state}   Velocidad: {self.tick_ms} ms",
            12,
            top + 12,
            self.bold_font,
            "#f9fafb",
        )
        self.draw_text(
            f"A*: ruta {max(0, len(snapshot.player_hint.path) - 1)} pasos, {len(snapshot.player_hint.explored)} nodos | "
            f"Fantasmas A*/BFS: {ghost_nodes} nodos",
            12,
            top + 38,
            self.small_font,
            "#cbd5e1",
        )
        self.draw_text(
            "Flechas/WASD mover | +/- velocidad | H pista A* | G fantasmas | T arbol | Espacio pausa | R reiniciar",
            12,
            top + 62,
            self.small_font,
            "#cbd5e1",
        )
        if self.state.game_over or self.state.win:
            self.draw_text("Presiona R para reiniciar", self.view_width // 2, self.view_height // 2, self.title_font, "#ffffff", center=True)

    def draw_lesson_panel(self, snapshot: SearchSnapshot, left: int, top: int) -> None:
        lines = [
            ("Como leerlo", self.title_font, "#f8fafc"),
            ("A*: verde brillante ruta, verde medio frontera, verde oscuro explorados.", self.small_font, "#cbd5e1"),
            ("Fantasma A*: rojo fuerte camino, rojo oscuro busqueda.", self.small_font, "#cbd5e1"),
            ("Fantasma BFS: azul fuerte camino, azul oscuro busqueda.", self.small_font, "#cbd5e1"),
            ("Aros en dots: color del enemigo que alcanzo ese dot durante la busqueda.", self.small_font, "#cbd5e1"),
            ("Arbol: cada linea conecta padre -> hijo para reconstruir la ruta.", self.small_font, "#cbd5e1"),
            (f"A* ahora exploro {len(snapshot.player_hint.explored)} nodos.", self.small_font, "#cbd5e1"),
            (
                " | ".join(
                    f"{ghost.algorithm} exploro {len(search.explored)} nodos"
                    for ghost, search in zip(self.state.ghosts, snapshot.ghost_searches)
                ),
                self.small_font,
                "#cbd5e1",
            ),
        ]

        y = top
        for text, font, color in lines:
            if text:
                y = self.draw_wrapped_text(text, left + 16, y, PANEL_WIDTH - 32, font, color) + 8
            else:
                y += 9

    def draw_map_cells(self, cells: list[Pos] | set[Pos], color: str, radius: int, origin: tuple[int, int]) -> None:
        for pos in cells:
            pygame.draw.circle(self.screen, hex_color(color), self.map_center(pos, origin), radius)

    def draw_search_tree(self, result: SearchResult, color: str, origin: tuple[int, int], max_edges: int = 45) -> None:
        edges = [(child, parent) for child, parent in result.came_from.items() if parent is not None]
        for child, parent in edges[:max_edges]:
            pygame.draw.line(self.screen, hex_color(color), self.map_center(parent, origin), self.map_center(child, origin), 1)

    def draw_text(
        self,
        text: str,
        x: int,
        y: int,
        font: pygame.font.Font,
        color: str,
        *,
        center: bool = False,
    ) -> None:
        surface = font.render(text, True, hex_color(color))
        rect = surface.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surface, rect)

    def draw_wrapped_text(self, text: str, x: int, y: int, width: int, font: pygame.font.Font, color: str) -> int:
        words = text.split()
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if font.size(candidate)[0] <= width:
                line = candidate
            else:
                self.draw_text(line, x, y, font, color)
                y += font.get_linesize()
                line = word
        if line:
            self.draw_text(line, x, y, font, color)
            y += font.get_linesize()
        return y

    def map_center(self, pos: Pos, origin: tuple[int, int]) -> tuple[int, int]:
        return (origin[0] + pos[0] * MAP_CELL + MAP_CELL // 2, origin[1] + pos[1] * MAP_CELL + MAP_CELL // 2)

    def shortest_delta_to(self, pos: Pos) -> tuple[float, float]:
        origin_x = self.visual_player_pos[0] + 0.5
        origin_y = self.visual_player_pos[1] + 0.5
        target_x = pos[0] + 0.5
        target_y = pos[1] + 0.5
        dx = target_x - origin_x
        if abs(dx) > self.state.maze.width / 2:
            dx -= math.copysign(self.state.maze.width, dx)
        return dx, target_y - origin_y

    def sprite_distance(self, pos: Pos) -> float:
        dx, dy = self.shortest_delta_to(pos)
        return math.hypot(dx, dy)


def hex_color(color: str) -> tuple[int, int, int]:
    return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))


def normalize_angle(angle: float) -> float:
    while angle <= -math.pi:
        angle += math.tau
    while angle > math.pi:
        angle -= math.tau
    return angle
