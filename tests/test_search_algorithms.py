from __future__ import annotations

import unittest

from pacman_search import Ghost, MAZE, PacmanSearchGame, SearchResult


def build_headless_game() -> PacmanSearchGame:
    game = PacmanSearchGame.__new__(PacmanSearchGame)
    game.width = len(MAZE[0])
    game.height = len(MAZE)
    game.walls = {
        (x, y)
        for y, row in enumerate(MAZE)
        for x, char in enumerate(row)
        if char == "#"
    }
    game.pellets = {
        (x, y)
        for y, row in enumerate(MAZE)
        for x, char in enumerate(row)
        if char == "."
    }
    game.power_pellets = {
        (x, y)
        for y, row in enumerate(MAZE)
        for x, char in enumerate(row)
        if char == "o"
    }
    game.pacman = next(
        (x, y)
        for y, row in enumerate(MAZE)
        for x, char in enumerate(row)
        if char == "P"
    )
    return game


class SearchAlgorithmTests(unittest.TestCase):
    def test_maze_rows_have_consistent_width(self) -> None:
        widths = {len(row) for row in MAZE}
        self.assertEqual(widths, {21})

    def test_bfs_finds_path_around_wall(self) -> None:
        game = build_headless_game()

        result = PacmanSearchGame.bfs(game, (1, 1), (9, 1))

        self.assertEqual(result.path[0], (1, 1))
        self.assertEqual(result.path[-1], (9, 1))
        self.assertTrue(all(pos not in game.walls for pos in result.path))

    def test_a_star_targets_nearest_pellet(self) -> None:
        game = PacmanSearchGame.__new__(PacmanSearchGame)
        game.width = 5
        game.height = 3
        game.walls = set()
        game.pacman = (0, 1)
        game.pellets = {(4, 1), (1, 1)}
        game.power_pellets = set()

        result = PacmanSearchGame.a_star_to_nearest_pellet(game)

        self.assertEqual(result.path[0], (0, 1))
        self.assertIn(result.path[-1], game.pellets)
        self.assertEqual(len(result.path), 2)
        self.assertIn((0, 1), result.explored)

    def test_all_pellets_are_reachable(self) -> None:
        game = build_headless_game()
        targets = game.pellets | game.power_pellets

        for target in targets:
            with self.subTest(target=target):
                result = PacmanSearchGame.bfs(game, game.pacman, target)
                self.assertEqual(result.path[-1], target)

    def test_level_has_no_single_exit_dead_ends(self) -> None:
        game = build_headless_game()
        open_cells = {
            (x, y)
            for y, row in enumerate(MAZE)
            for x, char in enumerate(row)
            if char != "#"
        }

        for cell in open_cells:
            with self.subTest(cell=cell):
                self.assertGreaterEqual(len(PacmanSearchGame.neighbors(game, cell)), 2)

    def test_color_sum_clamps_channels(self) -> None:
        game = PacmanSearchGame.__new__(PacmanSearchGame)

        color = PacmanSearchGame.sum_colors(game, ["#ff4d6d", "#4cc9f0"])

        self.assertEqual(color, "#ffffff")

    def test_pellets_use_sum_of_searching_ghost_colors(self) -> None:
        game = PacmanSearchGame.__new__(PacmanSearchGame)
        game.pellets = {(2, 1), (3, 1)}
        game.power_pellets = set()
        game.ghosts = [
            Ghost((1, 1), "#100000", "Rojo", (1, 1)),
            Ghost((4, 1), "#002000", "Verde", (4, 1)),
        ]
        searches = [
            SearchResult(path=[(1, 1), (2, 1)], explored={(1, 1), (2, 1)}, came_from={}, frontier=set()),
            SearchResult(path=[(4, 1), (3, 1), (2, 1)], explored={(4, 1), (3, 1)}, came_from={}, frontier={(2, 1)}),
        ]

        colors = PacmanSearchGame.searched_pellet_colors(game, searches)

        self.assertEqual(colors[(2, 1)], "#102000")
        self.assertEqual(colors[(3, 1)], "#002000")


if __name__ == "__main__":
    unittest.main()
