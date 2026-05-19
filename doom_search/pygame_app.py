from __future__ import annotations

import math
from pathlib import Path

import pygame

from doom_search.algorithms import SearchResult
from doom_search.colors import fade
from doom_search.entities import Direction, Pos
from doom_search.game_state import GameState, SearchSnapshot
from doom_search.level import KEY_TO_DIRECTION

VIEW_WIDTH = 760
VIEW_HEIGHT = 520
MAP_CELL = 14
CLASSIC_CELL = 28
MINIMAP_CELL = 9
HUD_HEIGHT = 92
PANEL_WIDTH = 380
DEFAULT_TICK_MS = 320
SMOOTH_VIEW_FPS = 60
FOV = math.radians(68)
MAX_VIEW_DISTANCE = 16.0
RAY_STEP = 4
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
FRAME_DIR = ASSET_DIR / "frames"
ANIMATION_MS = 90
GHOST_ANIMATION_MS = 140

VIEW_ANGLES = {
    "Right": 0.0,
    "Down": math.pi / 2,
    "Left": math.pi,
    "Up": -math.pi / 2,
}
ANGLE_DIRECTIONS: list[Direction] = ["Right", "Down", "Left", "Up"]


class PygameSearchGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Pac-Man Search: Dijkstra en tiempo real")

        self.state = GameState()
        self.view_width = VIEW_WIDTH
        self.view_height = VIEW_HEIGHT
        self.screen_width = self.view_width + PANEL_WIDTH
        self.screen_height = self.view_height + HUD_HEIGHT
        self.map_width = self.state.maze.width * MAP_CELL
        self.map_height = self.state.maze.height * MAP_CELL
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        self.clock = pygame.time.Clock()
        self.small_font = pygame.font.SysFont("Segoe UI", 13)
        self.bold_font = pygame.font.SysFont("Segoe UI", 17, bold=True)
        self.title_font = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.sprites = self.load_sprites()
        self.scaled_sprites: dict[tuple[str, int, int, int], pygame.Surface] = {}

        self.show_hint = True
        self.show_ghost_paths = True
        self.show_tree = True
        self.lighting_enabled = False
        self.mode = "classic"
        self.tick_ms = DEFAULT_TICK_MS
        self.last_tick = pygame.time.get_ticks()
        self.mode_button_rect = pygame.Rect(0, 0, 0, 0)
        self.light_button_rect = pygame.Rect(0, 0, 0, 0)
        self.visual_player_start = (float(self.state.player[0]), float(self.state.player[1]))
        self.visual_player_end = self.visual_player_start
        self.visual_player_pos = self.visual_player_start
        self.visual_ghost_starts = [(float(ghost.pos[0]), float(ghost.pos[1])) for ghost in self.state.ghosts]
        self.visual_ghost_ends = list(self.visual_ghost_starts)
        self.visual_ghost_positions = list(self.visual_ghost_starts)
        self.visual_move_start = self.last_tick
        self.visual_move_duration = self.tick_ms
        self.visual_angle = VIEW_ANGLES[self.state.direction]
        self.visual_angle_start = self.visual_angle
        self.visual_angle_end = self.visual_angle
        self.movement_direction = self.state.direction
        self.visual_turn_start = self.last_tick
        self.visual_turn_duration = self.tick_ms

    def load_sprites(self) -> dict[str, list[pygame.Surface]]:
        names = {
            "pac_up": "pac_up.gif",
            "pac_down": "pac_down.gif",
            "pac_left": "pac_left.gif",
            "pac_right": "pac_right.gif",
            "pac_death": "pac_death.gif",
            "ghost_up": "ghost_up.gif",
            "ghost_down": "ghost_down.gif",
            "ghost_left": "ghost_left.gif",
            "ghost_right": "ghost_right.gif",
            "ghost_blue": "ghost_blue.gif",
            "ghost_white": "ghost_white.gif",
        }
        sprites: dict[str, list[pygame.Surface]] = {}
        for key, filename in names.items():
            frames = self.load_sprite_frames(key)
            if frames:
                sprites[key] = frames
                continue
            path = ASSET_DIR / filename
            if path.exists():
                sprites[key] = [pygame.image.load(str(path)).convert_alpha()]
        return sprites

    def load_sprite_frames(self, key: str) -> list[pygame.Surface]:
        frame_path = FRAME_DIR / key
        if not frame_path.exists():
            return []
        return [
            pygame.image.load(str(path)).convert_alpha()
            for path in sorted(frame_path.glob("*.png"))
        ]

    def scaled_sprite(self, key: str, width: int, height: int | None = None) -> pygame.Surface | None:
        if key not in self.sprites:
            return None
        height = width if height is None else height
        frame = self.current_frame_index(key)
        cache_key = (key, frame, width, height)
        if cache_key not in self.scaled_sprites:
            self.scaled_sprites[cache_key] = pygame.transform.scale(self.sprites[key][frame], (width, height))
        return self.scaled_sprites[cache_key]

    def current_frame_index(self, key: str) -> int:
        frames = self.sprites.get(key, [])
        if len(frames) <= 1:
            return 0
        frame_ms = GHOST_ANIMATION_MS if key.startswith("ghost_") else ANIMATION_MS
        return (pygame.time.get_ticks() // frame_ms) % len(frames)

    def draw_sprite(self, key: str, rect: pygame.Rect) -> bool:
        sprite = self.scaled_sprite(key, rect.width, rect.height)
        if sprite is None:
            return False
        self.screen.blit(sprite, rect)
        return True

    def run(self) -> None:
        running = True
        while running:
            running = self.handle_events()
            now = pygame.time.get_ticks()
            if now - self.last_tick >= self.tick_ms:
                previous_player = self.state.player
                previous_direction = self.state.direction
                previous_ghosts = [ghost.pos for ghost in self.state.ghosts]
                self.state.tick()
                self.begin_player_animation(previous_player, self.state.player, now)
                self.begin_ghost_animations(previous_ghosts, [ghost.pos for ghost in self.state.ghosts], now)
                if self.mode == "classic":
                    self.begin_turn_animation(previous_direction, self.state.direction, now)
                self.last_tick = now
            self.update_visual_player(now)
            self.update_visual_ghosts(now)
            self.update_visual_angle(now)
            self.draw()
            self.clock.tick(SMOOTH_VIEW_FPS)
        pygame.quit()

    def begin_player_animation(self, previous: Pos, current: Pos, now: int) -> None:
        animation = self.cell_animation(previous, current)
        if animation is None:
            self.snap_visual_player()
            return

        self.visual_player_start, self.visual_player_end = animation
        self.visual_move_start = now
        self.visual_move_duration = max(80, self.tick_ms)

    def begin_ghost_animations(self, previous_positions: list[Pos], current_positions: list[Pos], now: int) -> None:
        self.visual_ghost_starts = []
        self.visual_ghost_ends = []
        self.visual_move_start = now
        self.visual_move_duration = max(80, self.tick_ms)
        for previous, current in zip(previous_positions, current_positions):
            animation = self.cell_animation(previous, current)
            if animation is None:
                start = (float(current[0]), float(current[1]))
                end = start
            else:
                start, end = animation
            self.visual_ghost_starts.append(start)
            self.visual_ghost_ends.append(end)

    def cell_animation(self, previous: Pos, current: Pos) -> tuple[tuple[float, float], tuple[float, float]] | None:
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

    def begin_turn_animation(self, previous: str, current: str, now: int) -> None:
        if previous == current:
            return

        self.update_visual_angle(now)
        target_angle = self.visual_angle + normalize_angle(VIEW_ANGLES[current] - self.visual_angle)
        self.visual_angle_start = self.visual_angle
        self.visual_angle_end = target_angle
        self.visual_turn_start = now
        self.visual_turn_duration = max(95, min(190, int(self.tick_ms * 0.58)))

    def snap_visual_player(self) -> None:
        current = (float(self.state.player[0]), float(self.state.player[1]))
        self.visual_player_start = current
        self.visual_player_end = current
        self.visual_player_pos = current
        self.movement_direction = self.state.direction
        self.snap_visual_ghosts()
        self.snap_visual_angle()

    def snap_visual_ghosts(self) -> None:
        positions = [(float(ghost.pos[0]), float(ghost.pos[1])) for ghost in self.state.ghosts]
        self.visual_ghost_starts = positions
        self.visual_ghost_ends = positions
        self.visual_ghost_positions = positions

    def snap_visual_angle(self) -> None:
        self.visual_angle = VIEW_ANGLES[self.state.direction]
        self.visual_angle_start = self.visual_angle
        self.visual_angle_end = self.visual_angle

    def update_visual_player(self, now: int) -> None:
        elapsed = max(0, now - self.visual_move_start)
        progress = min(1.0, elapsed / self.visual_move_duration)
        eased = progress * progress * (3.0 - 2.0 * progress)
        x = self.visual_player_start[0] + (self.visual_player_end[0] - self.visual_player_start[0]) * eased
        y = self.visual_player_start[1] + (self.visual_player_end[1] - self.visual_player_start[1]) * eased
        self.visual_player_pos = (x % self.state.maze.width, y)

    def update_visual_ghosts(self, now: int) -> None:
        elapsed = max(0, now - self.visual_move_start)
        progress = min(1.0, elapsed / self.visual_move_duration)
        eased = progress * progress * (3.0 - 2.0 * progress)
        self.visual_ghost_positions = []
        for start, end in zip(self.visual_ghost_starts, self.visual_ghost_ends):
            x = start[0] + (end[0] - start[0]) * eased
            y = start[1] + (end[1] - start[1]) * eased
            self.visual_ghost_positions.append((x % self.state.maze.width, y))

    def update_visual_angle(self, now: int) -> None:
        elapsed = max(0, now - self.visual_turn_start)
        progress = min(1.0, elapsed / self.visual_turn_duration)
        eased = 1 - (1 - progress) ** 4
        self.visual_angle = normalize_angle(
            self.visual_angle_start + (self.visual_angle_end - self.visual_angle_start) * eased
        )

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.mode_button_rect.collidepoint(event.pos):
                    self.toggle_mode()
                elif self.light_button_rect.collidepoint(event.pos):
                    self.lighting_enabled = not self.lighting_enabled
            if event.type == pygame.KEYDOWN:
                self.handle_key(event)
        return True

    def handle_key(self, event: pygame.event.Event) -> None:
        key_name = pygame.key.name(event.key).lower()
        if self.mode == "3d" and event.key in {pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d}:
            self.look_at(self.relative_look_direction(event.key))
        elif self.mode == "3d" and event.key in {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT}:
            direction = self.arrow_movement_direction(event.key)
            self.movement_direction = direction
            self.look_at(direction, duration=230)
            self.state.request_direction(direction)
        elif key_name in KEY_TO_DIRECTION:
            direction = KEY_TO_DIRECTION[key_name]
            self.state.request_direction(direction)
        elif event.key == pygame.K_SPACE:
            self.state.toggle_pause()
        elif event.key == pygame.K_r:
            self.state.reset()
            self.snap_visual_player()
        elif event.key == pygame.K_m:
            self.toggle_mode()
        elif event.key == pygame.K_l:
            self.lighting_enabled = not self.lighting_enabled
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

    def toggle_mode(self) -> None:
        self.mode = "3d" if self.mode == "classic" else "classic"
        if self.mode == "classic":
            self.snap_visual_angle()
            self.movement_direction = self.state.direction
        else:
            self.movement_direction = self.state.direction

    def look_at(self, direction: Direction, *, duration: int = 150) -> None:
        now = pygame.time.get_ticks()
        self.update_visual_angle(now)
        target_angle = self.visual_angle + normalize_angle(VIEW_ANGLES[direction] - self.visual_angle)
        self.visual_angle_start = self.visual_angle
        self.visual_angle_end = target_angle
        self.visual_turn_start = now
        self.visual_turn_duration = duration

    def arrow_movement_direction(self, key: int) -> Direction:
        facing_index = ANGLE_DIRECTIONS.index(self.movement_direction)
        offsets = {
            pygame.K_UP: 0,
            pygame.K_RIGHT: 1,
            pygame.K_DOWN: 2,
            pygame.K_LEFT: -1,
        }
        return ANGLE_DIRECTIONS[(facing_index + offsets[key]) % len(ANGLE_DIRECTIONS)]

    def relative_look_direction(self, key: int) -> Direction:
        facing = self.direction_from_angle(self.visual_angle_end)
        facing_index = ANGLE_DIRECTIONS.index(facing)
        offsets = {
            pygame.K_w: 0,
            pygame.K_d: 1,
            pygame.K_s: 2,
            pygame.K_a: -1,
        }
        return ANGLE_DIRECTIONS[(facing_index + offsets[key]) % len(ANGLE_DIRECTIONS)]

    def relative_direction(self, requested: Direction) -> Direction:
        facing = self.direction_from_angle(self.visual_angle)
        facing_index = ANGLE_DIRECTIONS.index(facing)
        offsets: dict[Direction, int] = {"Up": 0, "Right": 1, "Down": 2, "Left": -1}
        return ANGLE_DIRECTIONS[(facing_index + offsets[requested]) % len(ANGLE_DIRECTIONS)]

    def direction_from_angle(self, angle: float) -> Direction:
        normalized = normalize_angle(angle)
        index = round(normalized / (math.pi / 2)) % len(ANGLE_DIRECTIONS)
        return ANGLE_DIRECTIONS[index]

    def draw(self) -> None:
        snapshot = self.state.search_snapshot()
        self.screen.fill(hex_color("#050507"))
        if self.mode == "classic":
            self.draw_classic_mode(snapshot)
        else:
            self.draw_player_window(snapshot)
            self.draw_minimap(snapshot)
        self.draw_hud(snapshot)
        self.draw_mode_button()
        pygame.display.flip()

    def play_width(self) -> int:
        return self.screen_width if self.mode == "3d" else self.view_width

    def draw_classic_mode(self, snapshot: SearchSnapshot) -> None:
        self.draw_classic_maze(snapshot)
        self.draw_classic_lesson_panel(snapshot)

    def draw_mode_button(self) -> None:
        buttons = [
            ("Luz ON" if self.lighting_enabled else "Luz OFF", "light_button_rect"),
            ("Modo 3D" if self.mode == "classic" else "Modo clasico", "mode_button_rect"),
        ]
        x = self.view_width + PANEL_WIDTH - 12
        for label, attr in reversed(buttons):
            surface = self.small_font.render(label, True, hex_color("#f8fafc"))
            width = surface.get_width() + 18
            height = surface.get_height() + 10
            rect = pygame.Rect(x - width, 10, width, height)
            setattr(self, attr, rect)
            fill = "#334155" if attr == "light_button_rect" and self.lighting_enabled else "#1f2937"
            pygame.draw.rect(self.screen, hex_color(fill), rect, border_radius=5)
            pygame.draw.rect(self.screen, hex_color("#94a3b8"), rect, 1, border_radius=5)
            self.screen.blit(surface, surface.get_rect(center=rect.center))
            x = rect.left - 8

    def draw_player_window(self, snapshot: SearchSnapshot) -> None:
        self.draw_sky_and_floor()
        self.draw_raycast_walls()
        self.draw_3d_path_traces(snapshot)
        self.draw_visible_sprites()
        self.draw_crosshair()
        direction_name = {"Left": "Oeste", "Right": "Este", "Up": "Norte", "Down": "Sur"}[
            self.direction_from_angle(self.visual_angle)
        ]
        self.draw_text(f"Vista 3D - mirando {direction_name}", 12, 12, self.bold_font, "#f8fafc")

    def draw_sky_and_floor(self) -> None:
        width = self.play_width()
        horizon = self.view_height // 2
        for y in range(horizon):
            shade = int(4 + 20 * (y / max(1, horizon)))
            pygame.draw.line(
                self.screen, (shade // 2, shade, shade + 8), (0, y), (width, y)
            )
        for y in range(horizon, self.view_height):
            shade = int(24 - 18 * ((y - horizon) / max(1, horizon)))
            pygame.draw.line(
                self.screen, (shade + 5, shade, max(4, shade - 8)), (0, y), (width, y)
            )

    def draw_raycast_walls(self) -> None:
        width = self.play_width()
        view_angle = self.visual_angle
        for x in range(0, width, RAY_STEP):
            ray_angle = view_angle - FOV / 2 + FOV * (x / width)
            distance, hit_axis = self.cast_ray(ray_angle)
            corrected = max(0.08, distance * math.cos(ray_angle - view_angle))
            wall_height = min(self.view_height * 1.8, self.view_height / corrected)
            top = int((self.view_height - wall_height) / 2)
            rect = pygame.Rect(x, top, RAY_STEP + 1, int(wall_height))
            shade = max(10, min(205, int(230 / (1.0 + corrected * 0.38))))
            color = (shade // 3, shade // 2, shade)
            if hit_axis == "y":
                color = (max(25, color[0] - 16), max(25, color[1] - 16), max(50, color[2] - 12))
            pygame.draw.rect(self.screen, color, rect)
        if self.lighting_enabled:
            self.draw_view_darkness()

    def draw_view_darkness(self) -> None:
        width = self.play_width()
        overlay = pygame.Surface((width, self.view_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 78))
        center = (width // 2, self.view_height // 2)
        for radius, amount in ((620, 26), (460, 42), (300, 62), (185, 86), (72, 118)):
            self.subtract_alpha_circle(overlay, center, radius, amount)
        self.screen.blit(overlay, (0, 0))
        self.draw_screen_light_glow(center, min(width, self.view_height) // 3)

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
        sprites: list[tuple[float, tuple[float, float], str, str, str]] = []
        for pellet in self.state.pellets:
            sprites.append((self.sprite_distance(pellet), (float(pellet[0]), float(pellet[1])), "#f8fafc", "pellet", ""))
        for pellet in self.state.power_pellets:
            sprites.append((self.sprite_distance(pellet), (float(pellet[0]), float(pellet[1])), "#fef08a", "power", ""))
        for index, ghost in enumerate(self.state.ghosts):
            pos = self.visual_ghost_positions[index] if index < len(self.visual_ghost_positions) else ghost.pos
            sprites.append((self.sprite_distance_float(pos), pos, ghost.color, "enemy", self.ghost_sprite_key(index)))

        for _, pos, color, kind, image_key in sorted(sprites, reverse=True):
            projection = self.project_sprite_float(pos)
            if projection is None:
                continue
            screen_x, depth = projection
            if kind == "enemy":
                self.draw_3d_ghost_model(screen_x, depth, color)
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

    def draw_3d_ghost_model(self, screen_x: int, depth: float, color: str) -> None:
        body_width = int(max(30, min(150, self.view_height / depth * 0.52)))
        body_height = int(body_width * 1.18)
        foot_height = max(7, body_height // 7)
        bottom = self.view_height - max(28, int(30 / max(0.85, depth)))
        rect = pygame.Rect(0, 0, body_width, body_height)
        rect.midbottom = (screen_x, bottom)

        base = hex_color(color)
        highlight = brighten(base, 54)
        mid = brighten(base, 20)
        shadow = darken(base, 60)
        dark_shadow = darken(base, 95)

        shadow_rect = pygame.Rect(0, 0, int(body_width * 0.92), max(8, body_width // 6))
        shadow_rect.center = (screen_x, bottom + max(2, foot_height // 3))
        pygame.draw.ellipse(self.screen, (2, 6, 23), shadow_rect)

        dome = pygame.Rect(rect.left, rect.top, body_width, int(body_height * 0.74))
        pygame.draw.ellipse(self.screen, shadow, dome.move(4, 3))
        pygame.draw.ellipse(self.screen, mid, dome)
        pygame.draw.ellipse(self.screen, highlight, dome.inflate(-body_width // 6, -body_height // 7))

        torso = pygame.Rect(rect.left, rect.top + body_height // 3, body_width, body_height - foot_height - body_height // 3)
        pygame.draw.rect(self.screen, mid, torso)
        pygame.draw.rect(self.screen, shadow, (torso.centerx, torso.top, torso.width // 2, torso.height))
        pygame.draw.line(self.screen, highlight, (torso.left + 4, torso.top + 2), (torso.left + 4, torso.bottom - 4), 2)

        foot_count = 4
        foot_width = body_width / foot_count
        points: list[tuple[int, int]] = [(torso.left, torso.bottom)]
        for index in range(foot_count):
            mid_x = torso.left + int((index + 0.5) * foot_width)
            right = torso.left + int((index + 1) * foot_width)
            points.extend([(mid_x, torso.bottom + foot_height), (right, torso.bottom)])
            pygame.draw.circle(self.screen, shadow if index % 2 else mid, (mid_x, torso.bottom), max(4, int(foot_width * 0.45)))
        points.append((torso.left, torso.bottom))
        pygame.draw.polygon(self.screen, shadow, points)

        eye_radius = max(5, body_width // 9)
        pupil_radius = max(2, eye_radius // 2)
        eye_y = rect.top + int(body_height * 0.34)
        eye_offset = body_width // 5
        pupil_dx = max(-pupil_radius, min(pupil_radius, int(math.cos(self.visual_angle) * pupil_radius)))
        for eye_x in (screen_x - eye_offset, screen_x + eye_offset):
            pygame.draw.ellipse(
                self.screen,
                hex_color("#f8fafc"),
                (eye_x - eye_radius, eye_y - eye_radius, eye_radius * 2, int(eye_radius * 2.25)),
            )
            pygame.draw.circle(self.screen, dark_shadow, (eye_x + pupil_dx, eye_y + pupil_radius // 3), pupil_radius)

        pygame.draw.arc(self.screen, dark_shadow, dome, math.pi * 0.06, math.pi * 0.94, max(1, body_width // 30))

    def draw_3d_path_traces(self, snapshot: SearchSnapshot) -> None:
        if self.show_ghost_paths:
            for ghost, search in zip(self.state.ghosts, snapshot.ghost_searches):
                self.draw_3d_path_arrows(search.path[1:9], ghost.path_color, 22, 215)
        if self.show_hint:
            self.draw_3d_path_arrows(snapshot.player_hint.path[1:8], "#2ec4b6", 11, 185)

    def draw_3d_path_arrows(self, path: list[Pos], color: str, max_size: int, alpha: int) -> None:
        if not path:
            return

        projected: list[tuple[float, int, int, int, int]] = []
        for index, pos in enumerate(path):
            projection = self.project_sprite(pos)
            if projection is None:
                continue
            screen_x, depth = projection
            y = int(self.view_height // 2 + min(self.view_height * 0.34, self.view_height / depth * 0.18))
            size = int(max(max_size * 0.42, min(max_size, max_size / max(0.7, depth) * 1.45)))
            projected.append((depth, index, screen_x, y, size))

        points_by_index = {index: (screen_x, y) for _, index, screen_x, y, _ in projected}
        arrow_surface = pygame.Surface((self.play_width(), self.view_height), pygame.SRCALPHA)
        rgb = hex_color(color)
        pulse_index = (pygame.time.get_ticks() // 145) % max(1, len(path))
        for depth, index, screen_x, y, size in sorted(projected, reverse=True):
            next_point = points_by_index.get(index + 1)
            angle = -math.pi / 2
            if next_point is not None:
                angle = math.atan2(next_point[1] - y, next_point[0] - screen_x)
            pulse = 1.0 if index == pulse_index else 0.0
            marker_size = int(size * (1.0 + pulse * 0.32))
            marker_alpha = min(255, int(alpha * (1.0 + pulse * 0.2)))
            self.draw_arrow_marker(arrow_surface, (screen_x, y), angle, marker_size, (*rgb, marker_alpha))
            fade_alpha = max(45, min(145, int(marker_alpha / max(1.0, depth))))
            pygame.draw.circle(arrow_surface, (*rgb, fade_alpha), (screen_x, y), max(2, marker_size // 5))
        self.screen.blit(arrow_surface, (0, 0))

    def draw_arrow_marker(
        self,
        surface: pygame.Surface,
        center: tuple[int, int],
        angle: float,
        size: int,
        color: tuple[int, int, int, int],
    ) -> None:
        tip = (
            center[0] + math.cos(angle) * size,
            center[1] + math.sin(angle) * size,
        )
        left = (
            center[0] + math.cos(angle + 2.42) * size * 0.72,
            center[1] + math.sin(angle + 2.42) * size * 0.72,
        )
        right = (
            center[0] + math.cos(angle - 2.42) * size * 0.72,
            center[1] + math.sin(angle - 2.42) * size * 0.72,
        )
        pygame.draw.polygon(surface, color, [tip, left, right])
        pygame.draw.polygon(surface, (255, 255, 255, min(160, color[3])), [tip, left, right], 1)

    def project_sprite(self, pos: Pos) -> tuple[int, float] | None:
        return self.project_sprite_float((float(pos[0]), float(pos[1])))

    def project_sprite_float(self, pos: tuple[float, float]) -> tuple[int, float] | None:
        dx, dy = self.shortest_delta_to(pos)
        distance = max(0.01, math.hypot(dx, dy))
        angle_to_sprite = math.atan2(dy, dx)
        angle_diff = normalize_angle(angle_to_sprite - self.visual_angle)
        if abs(angle_diff) > FOV * 0.58:
            return None

        depth = distance * math.cos(angle_diff)
        if depth <= 0.2:
            return None
        wall_distance, _ = self.cast_ray(angle_to_sprite)
        if wall_distance + 0.35 < distance:
            return None

        width = self.play_width()
        screen_x = int(width / 2 + (angle_diff / (FOV / 2)) * (width / 2))
        return screen_x, depth

    def draw_crosshair(self) -> None:
        center = (self.play_width() // 2, self.view_height // 2)
        pygame.draw.line(self.screen, hex_color("#d1d5db"), (center[0] - 9, center[1]), (center[0] + 9, center[1]), 1)
        pygame.draw.line(self.screen, hex_color("#d1d5db"), (center[0], center[1] - 9), (center[0], center[1] + 9), 1)

    def draw_map_window(self, snapshot: SearchSnapshot) -> None:
        left = self.view_width
        pygame.draw.rect(self.screen, hex_color("#0f172a"), (left, 0, PANEL_WIDTH, self.view_height + HUD_HEIGHT))
        self.draw_text("Mapa y busqueda", left + 16, 42, self.title_font, "#f8fafc")

        origin = (left + 18, 84)
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
        self.draw_map_light(origin)
        self.draw_lesson_panel(snapshot, left, origin[1] + self.map_height + 24)

    def draw_minimap(self, snapshot: SearchSnapshot) -> None:
        cell_size = MINIMAP_CELL
        maze_width = self.state.maze.width * cell_size
        maze_height = self.state.maze.height * cell_size
        origin = (self.screen_width - maze_width - 18, 48)
        panel_rect = pygame.Rect(origin[0] - 8, origin[1] - 8, maze_width + 16, maze_height + 16)
        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel.fill((2, 6, 23, 226))
        pygame.draw.rect(panel, (148, 163, 184, 110), panel.get_rect(), 1, border_radius=4)
        self.screen.blit(panel, panel_rect.topleft)

        self.draw_map_maze(origin, cell_size)
        self.draw_search_layers(snapshot, origin, cell_size)
        self.draw_map_pellets(snapshot, origin, cell_size)
        self.draw_map_player(origin, cell_size)
        self.draw_map_ghosts(origin, cell_size, show_labels=False)
        self.draw_map_light(origin, cell_size)

    def draw_classic_maze(self, snapshot: SearchSnapshot) -> None:
        maze_width = self.state.maze.width * CLASSIC_CELL
        maze_height = self.state.maze.height * CLASSIC_CELL
        origin = ((self.view_width - maze_width) // 2, (self.view_height - maze_height) // 2)
        pygame.draw.rect(self.screen, hex_color("#020617"), (0, 0, self.view_width, self.view_height))
        pygame.draw.rect(
            self.screen,
            hex_color("#050507"),
            (origin[0] - 10, origin[1] - 10, maze_width + 20, maze_height + 20),
        )
        self.draw_map_maze(origin, CLASSIC_CELL)
        self.draw_search_layers(snapshot, origin, CLASSIC_CELL)
        self.draw_map_pellets(snapshot, origin, CLASSIC_CELL)
        self.draw_map_player(origin, CLASSIC_CELL)
        self.draw_map_ghosts(origin, CLASSIC_CELL)
        self.draw_map_light(origin, CLASSIC_CELL)
        self.draw_text("Modo clasico", 14, 12, self.bold_font, "#f8fafc")

    def draw_classic_lesson_panel(self, snapshot: SearchSnapshot) -> None:
        left = self.view_width
        pygame.draw.rect(self.screen, hex_color("#0f172a"), (left, 0, PANEL_WIDTH, self.view_height + HUD_HEIGHT))
        self.draw_text("Dijkstra paso a paso", left + 16, 42, self.title_font, "#f8fafc")
        self.draw_lesson_panel(snapshot, left, 84)

    def draw_search_layers(self, snapshot: SearchSnapshot, origin: tuple[int, int], cell_size: int = MAP_CELL) -> None:
        if self.show_hint:
            self.draw_map_cells(snapshot.player_hint.explored, "#143642", max(3, cell_size // 5), origin, cell_size)
            self.draw_map_cells(snapshot.player_hint.frontier, "#265f73", max(3, cell_size // 5), origin, cell_size)
            self.draw_map_cells(snapshot.player_hint.path[1:], "#2ec4b6", max(5, cell_size // 4), origin, cell_size)

        if self.show_ghost_paths:
            for ghost, search in zip(self.state.ghosts, snapshot.ghost_searches):
                self.draw_map_cells(search.explored - set(search.path), ghost.search_color, max(2, cell_size // 7), origin, cell_size)
                self.draw_map_cells(search.frontier, fade(ghost.path_color, 2), max(2, cell_size // 7), origin, cell_size)
                self.draw_map_cells(search.path[1:-1], ghost.path_color, max(4, cell_size // 4), origin, cell_size)
                if len(search.path) > 1:
                    current = self.map_center(search.path[0], origin, cell_size)
                    next_step = self.map_center(search.path[1], origin, cell_size)
                    pygame.draw.line(self.screen, hex_color("#ffffff"), current, next_step, max(2, cell_size // 7))
                    pygame.draw.circle(self.screen, hex_color("#ffffff"), next_step, max(5, cell_size // 3), 2)

        if self.show_tree and snapshot.ghost_searches:
            self.draw_search_tree(snapshot.ghost_searches[0], self.state.ghosts[0].path_color, origin, cell_size)
            self.draw_search_tree(snapshot.player_hint, "#94d2bd", origin, cell_size, max_edges=32)

    def draw_map_maze(self, origin: tuple[int, int], cell_size: int = MAP_CELL) -> None:
        for x, y in self.state.maze.walls:
            rect = pygame.Rect(origin[0] + x * cell_size, origin[1] + y * cell_size, cell_size, cell_size)
            pygame.draw.rect(self.screen, hex_color("#1d4ed8"), rect)
            pygame.draw.rect(self.screen, hex_color("#60a5fa"), rect, 1)

    def draw_map_pellets(self, snapshot: SearchSnapshot, origin: tuple[int, int], cell_size: int = MAP_CELL) -> None:
        for pellet in self.state.pellets:
            center = self.map_center(pellet, origin, cell_size)
            pygame.draw.circle(self.screen, hex_color("#f8fafc"), center, max(2, cell_size // 8))
            self.draw_pellet_search_rings(center, snapshot.pellet_ghost_colors.get(pellet, []))
        for pellet in self.state.power_pellets:
            center = self.map_center(pellet, origin, cell_size)
            pygame.draw.circle(self.screen, hex_color("#fef08a"), center, max(5, cell_size // 5))
            self.draw_pellet_search_rings(center, snapshot.pellet_ghost_colors.get(pellet, []), start_radius=max(8, cell_size // 3))

    def draw_pellet_search_rings(self, center: tuple[int, int], colors: list[str], start_radius: int = 5) -> None:
        for index, color in enumerate(colors[:4]):
            pygame.draw.circle(self.screen, hex_color(color), center, start_radius + index * 2, 1)

    def draw_map_player(self, origin: tuple[int, int], cell_size: int = MAP_CELL) -> None:
        x, y = self.map_center_float(self.visual_player_pos, origin, cell_size)
        size = max(16, int(cell_size * 0.88))
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (x, y)
        sprite_key = f"pac_{self.direction_from_angle(self.visual_angle).lower()}"
        drew_sprite = self.draw_sprite(sprite_key, rect)
        if not drew_sprite:
            radius = max(7, cell_size // 3)
            pygame.draw.circle(self.screen, hex_color("#ffd60a"), (x, y), radius)
            pygame.draw.circle(self.screen, hex_color("#fff7ad"), (x, y), radius, 2)
            angle = self.visual_angle
            pygame.draw.line(
                self.screen,
                hex_color("#111111"),
                (x, y),
                (x + int(math.cos(angle) * radius * 1.3), y + int(math.sin(angle) * radius * 1.3)),
                2,
            )

    def draw_map_ghosts(self, origin: tuple[int, int], cell_size: int = MAP_CELL, *, show_labels: bool = True) -> None:
        for index, ghost in enumerate(self.state.ghosts):
            pos = self.visual_ghost_positions[index] if index < len(self.visual_ghost_positions) else ghost.pos
            center = self.map_center_float(pos, origin, cell_size)
            size = max(15, int(cell_size * 0.9))
            rect = pygame.Rect(0, 0, size, size)
            rect.center = center
            if not self.draw_sprite(self.ghost_sprite_key(index), rect):
                radius = max(6, cell_size // 3)
                pygame.draw.circle(self.screen, hex_color(ghost.color), center, radius)
                pygame.draw.circle(self.screen, hex_color("#ffffff"), center, radius, 1)
            if show_labels:
                radius = max(6, size // 2)
                self.draw_ghost_algorithm_label(ghost.algorithm, (center[0] + radius + 4, center[1] - radius - 2), ghost.path_color)

    def draw_ghost_algorithm_label(self, text: str, top_left: tuple[int, int], accent: str) -> None:
        label = "Dijkstra" if text == "Dijkstra" else text
        surface = self.bold_font.render(label, True, hex_color("#ffffff"))
        padding_x = 5
        padding_y = 2
        rect = pygame.Rect(
            top_left[0],
            top_left[1],
            surface.get_width() + padding_x * 2,
            surface.get_height() + padding_y * 2,
        )
        if rect.right > self.view_width - 4:
            rect.right = self.view_width - 4
        if rect.top < 4:
            rect.top = 4
        label_layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(label_layer, (2, 6, 23, 116), label_layer.get_rect(), border_radius=4)
        pygame.draw.rect(label_layer, (*hex_color(accent), 210), label_layer.get_rect(), 1, border_radius=4)
        self.screen.blit(label_layer, rect.topleft)
        self.screen.blit(surface, (rect.left + padding_x, rect.top + padding_y))

    def draw_map_light(self, origin: tuple[int, int], cell_size: int = MAP_CELL) -> None:
        if not self.lighting_enabled:
            return
        width = self.state.maze.width * cell_size
        height = self.state.maze.height * cell_size
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 154))
        center = self.map_center_float(self.visual_player_pos, (0, 0), cell_size)
        polygon = self.light_polygon(center, cell_size)
        if len(polygon) >= 3:
            light_cut = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.polygon(light_cut, (0, 0, 0, 116), polygon)
            mask = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.polygon(mask, (255, 255, 255, 255), polygon)
            for radius, amount in (
                (cell_size * 11, 28),
                (cell_size * 9, 44),
                (cell_size * 7, 62),
                (cell_size * 5, 82),
                (cell_size * 4, 104),
                (cell_size * 3, 132),
                (cell_size * 2, 154),
                (cell_size, 176),
            ):
                pygame.draw.circle(light_cut, (0, 0, 0, amount), center, radius)
            light_cut.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            overlay.blit(light_cut, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        self.redraw_light_blocking_walls(overlay, cell_size)
        self.screen.blit(overlay, origin)
        self.draw_map_light_glow((origin[0] + center[0], origin[1] + center[1]), int(cell_size * 3.5))

    def redraw_light_blocking_walls(self, overlay: pygame.Surface, cell_size: int) -> None:
        wall_alpha = 68
        for x, y in self.state.maze.walls:
            rect = pygame.Rect(x * cell_size, y * cell_size, cell_size, cell_size)
            pygame.draw.rect(overlay, (0, 0, 0, wall_alpha), rect)

    def subtract_alpha_circle(
        self,
        overlay: pygame.Surface,
        center: tuple[int, int],
        radius: int,
        amount: int,
    ) -> None:
        light_cut = pygame.Surface(overlay.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(light_cut, (0, 0, 0, amount), center, radius)
        overlay.blit(light_cut, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    def draw_screen_light_glow(self, center: tuple[int, int], radius: int) -> None:
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        glow_center = (radius, radius)
        for glow_radius, alpha in (
            (radius, 7),
            (int(radius * 0.62), 12),
            (int(radius * 0.36), 22),
            (int(radius * 0.16), 42),
            (5, 165),
        ):
            pygame.draw.circle(glow, (225, 225, 225, alpha), glow_center, max(1, glow_radius))
        self.screen.blit(glow, (center[0] - radius, center[1] - radius))

    def draw_map_light_glow(self, center: tuple[int, int], radius: int) -> None:
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        glow_center = (radius, radius)
        for glow_radius, alpha in (
            (radius, 8),
            (int(radius * 0.52), 16),
            (int(radius * 0.25), 30),
            (max(3, radius // 18), 150),
        ):
            pygame.draw.circle(glow, (235, 235, 235, alpha), glow_center, max(1, glow_radius))
        self.screen.blit(glow, (center[0] - radius, center[1] - radius))

    def light_polygon(self, center: tuple[int, int], cell_size: int) -> list[tuple[int, int]]:
        points: list[tuple[int, int]] = []
        max_distance = cell_size * 10.5
        for step in range(128):
            angle = math.tau * step / 128
            points.append(self.cast_light_pixel(center, angle, max_distance, cell_size))
        return points

    def cast_light_pixel(
        self,
        center: tuple[int, int],
        angle: float,
        max_distance: float,
        cell_size: int,
    ) -> tuple[int, int]:
        ray_x, ray_y = float(center[0]), float(center[1])
        step_x = math.cos(angle) * max(2.0, cell_size / 7)
        step_y = math.sin(angle) * max(2.0, cell_size / 7)
        traveled = 0.0
        while traveled < max_distance:
            ray_x += step_x
            ray_y += step_y
            traveled += math.hypot(step_x, step_y)
            cell = (int(ray_x // cell_size), int(ray_y // cell_size))
            if cell[1] < 0 or cell[1] >= self.state.maze.height:
                break
            cell = (cell[0] % self.state.maze.width, cell[1])
            if cell in self.state.maze.walls:
                break
        width = self.state.maze.width * cell_size
        height = self.state.maze.height * cell_size
        return (max(0, min(width - 1, int(ray_x))), max(0, min(height - 1, int(ray_y))))

    def ghost_sprite_key(self, index: int) -> str:
        if index >= len(self.visual_ghost_starts) or index >= len(self.visual_ghost_ends):
            return "ghost_right"
        start = self.visual_ghost_starts[index]
        end = self.visual_ghost_ends[index]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        if abs(dx) > self.state.maze.width / 2:
            dx = -math.copysign(1.0, dx)
        if abs(dx) >= abs(dy) and abs(dx) > 0.01:
            return "ghost_right" if dx > 0 else "ghost_left"
        if abs(dy) > 0.01:
            return "ghost_down" if dy > 0 else "ghost_up"
        return "ghost_right"

    def draw_hud(self, snapshot: SearchSnapshot) -> None:
        top = self.view_height
        hud_width = self.play_width()
        pygame.draw.rect(self.screen, hex_color("#111827"), (0, top, hud_width, HUD_HEIGHT))
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
            f"Fantasma Dijkstra: {ghost_nodes} nodos",
            12,
            top + 38,
            self.small_font,
            "#cbd5e1",
        )
        movement = (
            "3D: flechas mueven y recentran la camara, WASD gira la mirada"
            if self.mode == "3d"
            else "Clasico: flechas/WASD mueven segun el laberinto 2D"
        )
        self.draw_text(
            f"{movement} | M cambiar modo | +/- velocidad | H pista | G Dijkstra | T arbol | Espacio pausa | R reiniciar",
            12,
            top + 62,
            self.small_font,
            "#cbd5e1",
        )
        if self.state.game_over or self.state.win:
            self.draw_text("Presiona R para reiniciar", self.play_width() // 2, self.view_height // 2, self.title_font, "#ffffff", center=True)

    def draw_lesson_panel(self, snapshot: SearchSnapshot, left: int, top: int) -> None:
        lines = [
            ("Como leerlo", self.title_font, "#f8fafc"),
            ("Jugador: A* en verde sugiere el pellet mas cercano con costo acumulado + distancia estimada.", self.small_font, "#cbd5e1"),
            ("Fantasma: Dijkstra calcula costos desde su casilla y siempre toma el siguiente paso de la ruta mas barata hacia Pac-Man.", self.small_font, "#cbd5e1"),
            (self.ghost_decision_text(snapshot), self.small_font, "#f8fafc"),
            ("Rojo oscuro = casillas que Dijkstra ya cerro. Rojo claro = frontera pendiente. Rojo fuerte = camino elegido.", self.small_font, "#cbd5e1"),
            ("Las lineas del arbol muestran de que casilla vino cada decision; siguiendo padres se reconstruye la ruta final.", self.small_font, "#cbd5e1"),
            ("Aros en dots: el fantasma alcanzo ese dot durante su busqueda antes de decidir el siguiente paso.", self.small_font, "#cbd5e1"),
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

    def ghost_decision_text(self, snapshot: SearchSnapshot) -> str:
        if not snapshot.ghost_searches:
            return "Dijkstra no tiene una ruta activa."
        search = snapshot.ghost_searches[0]
        if len(search.path) <= 1:
            return "Dijkstra ya esta en el objetivo o no encontro un paso nuevo."
        return f"Decision actual: ir de {search.path[0]} a {search.path[1]} porque es el menor costo conocido hacia Pac-Man."

    def draw_map_cells(
        self,
        cells: list[Pos] | set[Pos],
        color: str,
        radius: int,
        origin: tuple[int, int],
        cell_size: int = MAP_CELL,
    ) -> None:
        for pos in cells:
            pygame.draw.circle(self.screen, hex_color(color), self.map_center(pos, origin, cell_size), radius)

    def draw_search_tree(
        self,
        result: SearchResult,
        color: str,
        origin: tuple[int, int],
        cell_size: int = MAP_CELL,
        max_edges: int = 45,
    ) -> None:
        edges = [(child, parent) for child, parent in result.came_from.items() if parent is not None]
        for child, parent in edges[:max_edges]:
            pygame.draw.line(
                self.screen,
                hex_color(color),
                self.map_center(parent, origin, cell_size),
                self.map_center(child, origin, cell_size),
                1,
            )

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

    def map_center(self, pos: Pos, origin: tuple[int, int], cell_size: int = MAP_CELL) -> tuple[int, int]:
        return (origin[0] + pos[0] * cell_size + cell_size // 2, origin[1] + pos[1] * cell_size + cell_size // 2)

    def map_center_float(
        self,
        pos: tuple[float, float],
        origin: tuple[int, int],
        cell_size: int = MAP_CELL,
    ) -> tuple[int, int]:
        return (int(origin[0] + pos[0] * cell_size + cell_size / 2), int(origin[1] + pos[1] * cell_size + cell_size / 2))

    def shortest_delta_to(self, pos: Pos) -> tuple[float, float]:
        return self.shortest_delta_to_float((float(pos[0]), float(pos[1])))

    def shortest_delta_to_float(self, pos: tuple[float, float]) -> tuple[float, float]:
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

    def sprite_distance_float(self, pos: tuple[float, float]) -> float:
        dx, dy = self.shortest_delta_to_float(pos)
        return math.hypot(dx, dy)


def hex_color(color: str) -> tuple[int, int, int]:
    return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))


def brighten(color: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    return tuple(min(255, component + amount) for component in color)


def darken(color: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    return tuple(max(0, component - amount) for component in color)


def normalize_angle(angle: float) -> float:
    while angle <= -math.pi:
        angle += math.tau
    while angle > math.pi:
        angle -= math.tau
    return angle
