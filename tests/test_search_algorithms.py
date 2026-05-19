from __future__ import annotations

import unittest

from pacman_search import MAZE, PacmanSearchGame


class SearchAlgorithmTests(unittest.TestCase):
    def test_maze_rows_have_consistent_width(self) -> None:
        widths = {len(row) for row in MAZE}
        self.assertEqual(widths, {21})

    def test_bfs_finds_path_around_wall(self) -> None:
        game = PacmanSearchGame.__new__(PacmanSearchGame)
        game.width = len(MAZE[0])
        game.height = len(MAZE)
        game.walls = {
            (x, y)
            for y, row in enumerate(MAZE)
            for x, char in enumerate(row)
            if char == "#"
        }

        path = PacmanSearchGame.bfs(game, (1, 1), (9, 1))

        self.assertEqual(path[0], (1, 1))
        self.assertEqual(path[-1], (9, 1))
        self.assertTrue(all(pos not in game.walls for pos in path))

    def test_a_star_targets_nearest_pellet(self) -> None:
        game = PacmanSearchGame.__new__(PacmanSearchGame)
        game.width = 5
        game.height = 3
        game.walls = set()
        game.pacman = (0, 1)
        game.pellets = {(4, 1), (1, 1)}
        game.power_pellets = set()

        path, explored = PacmanSearchGame.a_star_to_nearest_pellet(game)

        self.assertEqual(path, [(0, 1), (1, 1)])
        self.assertIn((0, 1), explored)


if __name__ == "__main__":
    unittest.main()
