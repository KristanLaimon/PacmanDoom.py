"""Sprite loading and frame selection for pygame rendering."""

from __future__ import annotations

import pygame

from doom_search.settings import ASSET_DIR, FRAME_DIR, GHOST_ANIMATION_MS, PACMAN_ANIMATION_MS

SPRITE_FILES = {
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


class SpriteStore:
    """Loads animated sprites once and serves scaled frames from a cache."""

    def __init__(self) -> None:
        self.frames = self._load_all()
        self.scaled: dict[tuple[str, int, int, int], pygame.Surface] = {}

    def draw(self, screen: pygame.Surface, key: str, rect: pygame.Rect) -> bool:
        """Draw a sprite into ``rect`` and return whether the sprite existed."""
        sprite = self.get(key, rect.width, rect.height)
        if sprite is None:
            return False
        screen.blit(sprite, rect)
        return True

    def get(self, key: str, width: int, height: int | None = None) -> pygame.Surface | None:
        """Return the current scaled frame for a sprite key."""
        if key not in self.frames:
            return None
        height = width if height is None else height
        frame_index = self.current_frame_index(key)
        cache_key = (key, frame_index, width, height)
        if cache_key not in self.scaled:
            self.scaled[cache_key] = pygame.transform.scale(
                self.frames[key][frame_index],
                (width, height),
            )
        return self.scaled[cache_key]

    def current_frame_index(self, key: str) -> int:
        """Pick a frame based on pygame's running clock."""
        frames = self.frames.get(key, [])
        if len(frames) <= 1:
            return 0
        frame_ms = GHOST_ANIMATION_MS if key.startswith("ghost_") else PACMAN_ANIMATION_MS
        return (pygame.time.get_ticks() // frame_ms) % len(frames)

    def _load_all(self) -> dict[str, list[pygame.Surface]]:
        sprites: dict[str, list[pygame.Surface]] = {}
        for key, filename in SPRITE_FILES.items():
            frames = self._load_png_frames(key)
            if not frames:
                path = ASSET_DIR / filename
                if path.exists():
                    frames = [pygame.image.load(str(path)).convert_alpha()]
            if frames:
                sprites[key] = frames
        return sprites

    def _load_png_frames(self, key: str) -> list[pygame.Surface]:
        frame_path = FRAME_DIR / key
        if not frame_path.exists():
            return []
        return [
            pygame.image.load(str(path)).convert_alpha()
            for path in sorted(frame_path.glob("*.png"))
        ]
