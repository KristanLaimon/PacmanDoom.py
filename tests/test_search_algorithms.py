from __future__ import annotations

import unittest

from doom_search import Ghost, MAZE, GameState, Maze, SearchResult, a_star, a_star_to_nearest_goal, bfs, dijkstra
from doom_search.colors import sum_colors


def build_headless_game() -> GameState:
    return GameState(Maze.from_rows(MAZE))


class SearchAlgorithmTests(unittest.TestCase):
    def test_maze_rows_have_consistent_width(self) -> None:
        widths = {len(row) for row in MAZE}
        self.assertEqual(widths, {21})

    def test_bfs_finds_path_around_wall(self) -> None:
        game = build_headless_game()

        result = bfs((1, 1), (9, 1), game.maze.neighbors)

        self.assertEqual(result.path[0], (1, 1))
        self.assertEqual(result.path[-1], (9, 1))
        self.assertTrue(all(pos not in game.maze.walls for pos in result.path))

    def test_a_star_targets_nearest_pellet(self) -> None:
        maze = Maze.from_rows(["     ", "P. . ", "     "])

        result = a_star_to_nearest_goal(maze.player_start, set(maze.pellets), maze.neighbors)

        self.assertEqual(result.path[0], (0, 1))
        self.assertIn(result.path[-1], maze.pellets)
        self.assertEqual(len(result.path), 2)
        self.assertIn((0, 1), result.explored)

    def test_a_star_finds_specific_goal(self) -> None:
        game = build_headless_game()

        result = a_star((1, 1), (9, 1), game.maze.neighbors)

        self.assertEqual(result.path[0], (1, 1))
        self.assertEqual(result.path[-1], (9, 1))
        self.assertTrue(all(pos not in game.maze.walls for pos in result.path))

    def test_dijkstra_finds_shortest_path(self) -> None:
        game = build_headless_game()

        result = dijkstra((1, 1), (9, 1), game.maze.neighbors)
        bfs_result = bfs((1, 1), (9, 1), game.maze.neighbors)

        self.assertEqual(result.path[0], (1, 1))
        self.assertEqual(result.path[-1], (9, 1))
        self.assertEqual(len(result.path), len(bfs_result.path))

    def test_all_pellets_are_reachable(self) -> None:
        game = build_headless_game()
        targets = game.pellets | game.power_pellets

        for target in targets:
            with self.subTest(target=target):
                result = game.bfs(game.player, target)
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
                self.assertGreaterEqual(len(game.maze.neighbors(cell)), 2)

    def test_color_sum_clamps_channels(self) -> None:
        color = sum_colors(["#ff4d6d", "#4cc9f0"])

        self.assertEqual(color, "#ffffff")

    def test_pellets_use_sum_of_searching_ghost_colors(self) -> None:
        game = GameState(Maze.from_rows(["#####", "#P..#", "#####"]))
        game.pellets = {(2, 1), (3, 1)}
        game.power_pellets = set()
        game.ghosts = [
            Ghost((1, 1), "#100000", "Rojo", (1, 1), "A*", "#080000", "#100000"),
            Ghost((4, 1), "#002000", "Verde", (4, 1), "Dijkstra", "#001000", "#002000"),
        ]
        searches = [
            SearchResult(path=[(1, 1), (2, 1)], explored={(1, 1), (2, 1)}, came_from={}, frontier=set()),
            SearchResult(path=[(4, 1), (3, 1), (2, 1)], explored={(4, 1), (3, 1)}, came_from={}, frontier={(2, 1)}),
        ]

        colors = game.searched_pellet_colors(searches)

        self.assertEqual(colors[(2, 1)], "#102000")
        self.assertEqual(colors[(3, 1)], "#002000")


if __name__ == "__main__":
    unittest.main()
