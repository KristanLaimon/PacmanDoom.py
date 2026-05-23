"""Classic 2D pygame renderer for the search maze."""

from __future__ import annotations

import math
from collections.abc import Iterable

import pygame

from doom_search.algorithms import SearchResult
from doom_search.animation import BoardAnimator
from doom_search.colors import fade
from doom_search.entities import Pos
from doom_search.game_state import GameState, SearchSnapshot
from doom_search.geometry import hex_color, map_center, map_center_float
from doom_search.settings import CLASSIC_CELL, HUD_HEIGHT, VIEW_HEIGHT, VIEW_WIDTH
from doom_search.sprites import SpriteStore


class ClassicRenderer:
    """Draws the maze, search overlays, sprites, and compact HUD."""

    def __init__(
        self,
        screen: pygame.Surface,
        state: GameState,
        sprites: SpriteStore,
        animator: BoardAnimator,
    ) -> None:
        self.screen = screen
        self.state = state
        self.sprites = sprites
        self.animator = animator
        self.small_font = pygame.font.SysFont("Segoe UI", 13)
        self.credit_font = pygame.font.SysFont("Segoe UI", 15)
        self.bold_font = pygame.font.SysFont("Segoe UI", 17, bold=True)
        self.title_font = pygame.font.SysFont("Segoe UI", 22, bold=True)

    def draw(
        self,
        snapshot: SearchSnapshot,
        *,
        tick_ms: int,
        show_hint: bool,
        show_ghost_paths: bool,
        show_tree: bool,
    ) -> None:
        """Draw one complete frame."""
        self.screen.fill(hex_color("#050507"))
        self.draw_maze(snapshot, show_hint=show_hint, show_ghost_paths=show_ghost_paths, show_tree=show_tree)
        self.draw_hud(snapshot, tick_ms)
        if self.state.game_over or self.state.win:
            message = "Ganaste" if self.state.win else "Game over"
            self.draw_text(f"{message}. Presiona R para reiniciar", VIEW_WIDTH // 2, VIEW_HEIGHT // 2, self.title_font, "#ffffff", center=True)

    def draw_maze(
        self,
        snapshot: SearchSnapshot,
        *,
        show_hint: bool,
        show_ghost_paths: bool,
        show_tree: bool,
    ) -> None:
        """Draw the board and optional search visualizations."""
        maze_width = self.state.maze.width * CLASSIC_CELL
        maze_height = self.state.maze.height * CLASSIC_CELL
        origin = ((VIEW_WIDTH - maze_width) // 2, (VIEW_HEIGHT - maze_height) // 2)
        pygame.draw.rect(self.screen, hex_color("#020617"), (0, 0, VIEW_WIDTH, VIEW_HEIGHT))
        self.draw_text(
            "Equipo: Andryk, Angélica, Kristan y Joaquín - Inteligencia artificial ITLP",
            VIEW_WIDTH // 2,
            VIEW_HEIGHT - 18,
            self.credit_font,
            "#64748b",
            center=True,
        )
        pygame.draw.rect(
            self.screen,
            hex_color("#050507"),
            (origin[0] - 10, origin[1] - 10, maze_width + 20, maze_height + 20),
        )
        self.draw_walls(origin)
        self.draw_search_layers(snapshot, origin, show_hint, show_ghost_paths, show_tree)
        self.draw_pellets(snapshot, origin)
        self.draw_player(origin)
        self.draw_ghosts(origin)
        self.draw_text("Modo clasico", 14, 12, self.bold_font, "#f8fafc")

    def draw_search_layers(
        self,
        snapshot: SearchSnapshot,
        origin: tuple[int, int],
        show_hint: bool,
        show_ghost_paths: bool,
        show_tree: bool,
    ) -> None:
        """Render explored cells, frontiers, chosen paths, and parent tree edges."""
        if show_hint:
            self.draw_cells(snapshot.player_hint.explored, "#143642", max(3, CLASSIC_CELL // 5), origin)
            self.draw_cells(snapshot.player_hint.frontier, "#265f73", max(3, CLASSIC_CELL // 5), origin)
            self.draw_cells(snapshot.player_hint.path[1:], "#2ec4b6", max(5, CLASSIC_CELL // 4), origin)

        if show_ghost_paths:
            for ghost, search in zip(self.state.ghosts, snapshot.ghost_searches):
                path_cells = set(search.path)
                self.draw_cells(search.explored - path_cells, ghost.search_color, max(2, CLASSIC_CELL // 7), origin)
                self.draw_cells(search.frontier, fade(ghost.path_color, 2), max(2, CLASSIC_CELL // 7), origin)
                self.draw_cells(search.path[1:-1], ghost.path_color, max(4, CLASSIC_CELL // 4), origin)
                if len(search.path) > 1:
                    current = map_center(search.path[0], origin, CLASSIC_CELL)
                    next_step = map_center(search.path[1], origin, CLASSIC_CELL)
                    pygame.draw.line(self.screen, hex_color("#ffffff"), current, next_step, max(2, CLASSIC_CELL // 7))
                    pygame.draw.circle(self.screen, hex_color("#ffffff"), next_step, max(5, CLASSIC_CELL // 3), 2)

        if show_tree and snapshot.ghost_searches:
            self.draw_search_tree(snapshot.ghost_searches[0], self.state.ghosts[0].path_color, origin)
            self.draw_search_tree(snapshot.player_hint, "#94d2bd", origin, max_edges=32)

    def draw_walls(self, origin: tuple[int, int]) -> None:
        """Draw maze wall blocks."""
        for x, y in self.state.maze.walls:
            rect = pygame.Rect(origin[0] + x * CLASSIC_CELL, origin[1] + y * CLASSIC_CELL, CLASSIC_CELL, CLASSIC_CELL)
            pygame.draw.rect(self.screen, hex_color("#1d4ed8"), rect)
            pygame.draw.rect(self.screen, hex_color("#60a5fa"), rect, 1)

    def draw_pellets(self, snapshot: SearchSnapshot, origin: tuple[int, int]) -> None:
        """Draw normal pellets, power pellets, and ghost-search ownership rings."""
        for pellet in self.state.pellets:
            center = map_center(pellet, origin, CLASSIC_CELL)
            pygame.draw.circle(self.screen, hex_color("#f8fafc"), center, max(2, CLASSIC_CELL // 8))
            self.draw_pellet_rings(center, snapshot.pellet_ghost_colors.get(pellet, []))
        for pellet in self.state.power_pellets:
            center = map_center(pellet, origin, CLASSIC_CELL)
            pygame.draw.circle(self.screen, hex_color("#fef08a"), center, max(5, CLASSIC_CELL // 5))
            self.draw_pellet_rings(center, snapshot.pellet_ghost_colors.get(pellet, []), start_radius=max(8, CLASSIC_CELL // 3))

    def draw_pellet_rings(self, center: tuple[int, int], colors: list[str], start_radius: int = 5) -> None:
        """Draw small color rings around pellets touched by ghost searches."""
        for index, color in enumerate(colors[:4]):
            pygame.draw.circle(self.screen, hex_color(color), center, start_radius + index * 2, 1)

    def draw_player(self, origin: tuple[int, int]) -> None:
        """Draw Pac-Man at the interpolated player position."""
        x, y = map_center_float(self.animator.player_pos, origin, CLASSIC_CELL)
        size = max(16, int(CLASSIC_CELL * 0.88))
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (x, y)
        sprite_key = f"pac_{self.state.direction.lower()}"
        if self.sprites.draw(self.screen, sprite_key, rect):
            return
        radius = max(7, CLASSIC_CELL // 3)
        pygame.draw.circle(self.screen, hex_color("#ffd60a"), (x, y), radius)
        pygame.draw.circle(self.screen, hex_color("#fff7ad"), (x, y), radius, 2)
        pygame.draw.line(
            self.screen,
            hex_color("#111111"),
            (x, y),
            (x + int(math.cos(self.animator.angle) * radius * 1.3), y + int(math.sin(self.animator.angle) * radius * 1.3)),
            2,
        )

    def draw_ghosts(self, origin: tuple[int, int]) -> None:
        """Draw every ghost and its compact algorithm label."""
        for index, ghost in enumerate(self.state.ghosts):
            pos = self.animator.ghost_positions[index] if index < len(self.animator.ghost_positions) else ghost.pos
            center = map_center_float(pos, origin, CLASSIC_CELL)
            size = max(15, int(CLASSIC_CELL * 0.9))
            rect = pygame.Rect(0, 0, size, size)
            rect.center = center
            if not self.sprites.draw(self.screen, self.animator.ghost_sprite_key(index), rect):
                radius = max(6, CLASSIC_CELL // 3)
                pygame.draw.circle(self.screen, hex_color(ghost.color), center, radius)
                pygame.draw.circle(self.screen, hex_color("#ffffff"), center, radius, 1)
            self.draw_ghost_label(ghost.algorithm, (center[0] + size // 2 + 4, center[1] - size // 2 - 2), ghost.path_color)

    def draw_ghost_label(self, text: str, top_left: tuple[int, int], accent: str) -> None:
        """Draw a small readable label near a ghost."""
        surface = self.bold_font.render(text, True, hex_color("#ffffff"))
        rect = pygame.Rect(top_left[0], top_left[1], surface.get_width() + 10, surface.get_height() + 4)
        if rect.right > VIEW_WIDTH - 4:
            rect.right = VIEW_WIDTH - 4
        if rect.top < 4:
            rect.top = 4
        label_layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(label_layer, (2, 6, 23, 116), label_layer.get_rect(), border_radius=4)
        pygame.draw.rect(label_layer, (*hex_color(accent), 210), label_layer.get_rect(), 1, border_radius=4)
        self.screen.blit(label_layer, rect.topleft)
        self.screen.blit(surface, (rect.left + 5, rect.top + 2))

    def draw_hud(self, snapshot: SearchSnapshot, tick_ms: int) -> None:
        """Draw the bottom status area with compact live game data."""
        top = VIEW_HEIGHT
        pygame.draw.rect(self.screen, hex_color("#111827"), (0, top, VIEW_WIDTH, HUD_HEIGHT))
        status = "Pausa" if self.state.paused else "Jugando"
        if self.state.game_over:
            status = "Game over"
        elif self.state.win:
            status = "Ganaste"

        ghost_nodes = sum(len(search.explored) for search in snapshot.ghost_searches)
        self.draw_text(
            f"Puntos: {self.state.score}   Vidas: {self.state.lives}   Estado: {status}   Velocidad: {tick_ms} ms",
            12,
            top + 12,
            self.bold_font,
            "#f9fafb",
        )
        self.draw_text(
            f"Pacman Dijkstra: ruta {max(0, len(snapshot.player_hint.path) - 1)} pasos, {len(snapshot.player_hint.explored)} nodos | "
            f"Fantasma Dijkstra: {ghost_nodes} nodos",
            12,
            top + 38,
            self.small_font,
            "#cbd5e1",
        )
        self.draw_text(
            "Flechas/WASD mover | +/- velocidad | H pista | G Dijkstra | T arbol | Espacio pausa | R reiniciar",
            12,
            top + 62,
            self.small_font,
            "#cbd5e1",
        )

    def draw_cells(self, cells: Iterable[Pos], color: str, radius: int, origin: tuple[int, int]) -> None:
        """Draw circular markers on a group of maze cells."""
        for pos in cells:
            pygame.draw.circle(self.screen, hex_color(color), map_center(pos, origin, CLASSIC_CELL), radius)

    def draw_search_tree(
        self,
        result: SearchResult,
        color: str,
        origin: tuple[int, int],
        max_edges: int = 45,
    ) -> None:
        """Draw parent links from a search result."""
        edges = [(child, parent) for child, parent in result.came_from.items() if parent is not None]
        for child, parent in edges[:max_edges]:
            pygame.draw.line(
                self.screen,
                hex_color(color),
                map_center(parent, origin, CLASSIC_CELL),
                map_center(child, origin, CLASSIC_CELL),
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
        """Render a single line of text."""
        surface = font.render(text, True, hex_color(color))
        rect = surface.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surface, rect)
