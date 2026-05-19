from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass
from typing import Callable

from doom_search.entities import Pos


@dataclass(frozen=True)
class SearchResult:
    path: list[Pos]
    explored: set[Pos]
    came_from: dict[Pos, Pos | None]
    frontier: set[Pos]


NeighborFn = Callable[[Pos], list[Pos]]


def bfs(start: Pos, goal: Pos, neighbors: NeighborFn) -> SearchResult:
    queue: deque[Pos] = deque([start])
    came_from: dict[Pos, Pos | None] = {start: None}
    explored: set[Pos] = set()
    frontier: set[Pos] = {start}

    while queue:
        current = queue.popleft()
        frontier.discard(current)
        explored.add(current)
        if current == goal:
            return SearchResult(reconstruct_path(came_from, current), explored, came_from, frontier)

        for neighbor in neighbors(current):
            if neighbor in came_from:
                continue
            came_from[neighbor] = current
            frontier.add(neighbor)
            queue.append(neighbor)

    return SearchResult([start], explored, came_from, frontier)


def a_star_to_nearest_goal(start: Pos, goals: set[Pos], neighbors: NeighborFn) -> SearchResult:
    if not goals:
        return SearchResult([start], set(), {start: None}, set())

    open_heap: list[tuple[int, int, Pos]] = [(0, 0, start)]
    came_from: dict[Pos, Pos | None] = {start: None}
    best_cost: dict[Pos, int] = {start: 0}
    explored: set[Pos] = set()
    frontier: set[Pos] = {start}
    tie_breaker = 0

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        frontier.discard(current)
        if current in explored:
            continue
        explored.add(current)
        if current in goals:
            return SearchResult(reconstruct_path(came_from, current), explored, came_from, frontier)

        for neighbor in neighbors(current):
            new_cost = best_cost[current] + 1
            if new_cost >= best_cost.get(neighbor, 10**9):
                continue
            best_cost[neighbor] = new_cost
            came_from[neighbor] = current
            tie_breaker += 1
            priority = new_cost + closest_goal_distance(neighbor, goals)
            frontier.add(neighbor)
            heapq.heappush(open_heap, (priority, tie_breaker, neighbor))

    return SearchResult([start], explored, came_from, frontier)


def a_star(start: Pos, goal: Pos, neighbors: NeighborFn) -> SearchResult:
    open_heap: list[tuple[int, int, Pos]] = [(closest_goal_distance(start, {goal}), 0, start)]
    came_from: dict[Pos, Pos | None] = {start: None}
    best_cost: dict[Pos, int] = {start: 0}
    explored: set[Pos] = set()
    frontier: set[Pos] = {start}
    tie_breaker = 0

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        frontier.discard(current)
        if current in explored:
            continue
        explored.add(current)
        if current == goal:
            return SearchResult(reconstruct_path(came_from, current), explored, came_from, frontier)

        for neighbor in neighbors(current):
            new_cost = best_cost[current] + 1
            if new_cost >= best_cost.get(neighbor, 10**9):
                continue
            best_cost[neighbor] = new_cost
            came_from[neighbor] = current
            tie_breaker += 1
            priority = new_cost + closest_goal_distance(neighbor, {goal})
            frontier.add(neighbor)
            heapq.heappush(open_heap, (priority, tie_breaker, neighbor))

    return SearchResult([start], explored, came_from, frontier)


def closest_goal_distance(pos: Pos, goals: set[Pos]) -> int:
    return min(abs(pos[0] - goal[0]) + abs(pos[1] - goal[1]) for goal in goals)


def reconstruct_path(came_from: dict[Pos, Pos | None], current: Pos) -> list[Pos]:
    path = [current]
    while came_from[current] is not None:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
