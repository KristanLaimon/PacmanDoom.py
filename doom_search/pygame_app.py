"""Pygame application controller for the classic search game."""

from __future__ import annotations

import pygame

from doom_search.animation import BoardAnimator
from doom_search.game_state import GameState
from doom_search.level import KEY_TO_DIRECTION
from doom_search.renderer import ClassicRenderer
from doom_search.settings import DEFAULT_TICK_MS, HUD_HEIGHT, SMOOTH_VIEW_FPS, VIEW_HEIGHT, VIEW_WIDTH
from doom_search.sprites import SpriteStore


class PygameSearchGame:
    """Owns pygame setup, input handling, ticking, and frame rendering."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Pac-Man Search: Dijkstra en tiempo real")

        self.state = GameState()
        self.screen = pygame.display.set_mode((VIEW_WIDTH, VIEW_HEIGHT + HUD_HEIGHT))
        self.clock = pygame.time.Clock()
        self.tick_ms = DEFAULT_TICK_MS
        self.last_tick = pygame.time.get_ticks()

        self.show_hint = True
        self.show_ghost_paths = True
        self.show_tree = True

        self.sprites = SpriteStore()
        self.animator = BoardAnimator(self.state, self.tick_ms, self.last_tick)
        self.renderer = ClassicRenderer(self.screen, self.state, self.sprites, self.animator)

    def run(self) -> None:
        """Run the event loop until the player closes the window."""
        running = True
        while running:
            running = self.handle_events()
            now = pygame.time.get_ticks()
            self.advance_game_if_needed(now)
            self.animator.tick_ms = self.tick_ms
            self.animator.update(now)
            self.draw()
            self.clock.tick(SMOOTH_VIEW_FPS)
        pygame.quit()

    def advance_game_if_needed(self, now: int) -> None:
        """Advance the grid state on the configured fixed game interval."""
        if now - self.last_tick < self.tick_ms:
            return

        previous_player = self.state.player
        previous_direction = self.state.direction
        previous_ghosts = [ghost.pos for ghost in self.state.ghosts]
        self.state.tick()
        self.animator.begin_player_move(previous_player, self.state.player, now)
        self.animator.begin_ghost_moves(previous_ghosts, [ghost.pos for ghost in self.state.ghosts], now)
        self.animator.begin_turn(previous_direction, self.state.direction, now)
        self.last_tick = now

    def handle_events(self) -> bool:
        """Process pygame window and keyboard events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                self.handle_key(event)
        return True

    def handle_key(self, event: pygame.event.Event) -> None:
        """Handle all keyboard commands for classic mode."""
        key_name = pygame.key.name(event.key).lower()
        if key_name in KEY_TO_DIRECTION:
            self.state.request_direction(KEY_TO_DIRECTION[key_name])
        elif event.key == pygame.K_SPACE:
            self.state.toggle_pause()
        elif event.key == pygame.K_r:
            self.state.reset()
            self.animator.snap_all()
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
        """Render the current frame and publish it to the display."""
        self.renderer.draw(
            self.state.search_snapshot(),
            tick_ms=self.tick_ms,
            show_hint=self.show_hint,
            show_ghost_paths=self.show_ghost_paths,
            show_tree=self.show_tree,
        )
        pygame.display.flip()
