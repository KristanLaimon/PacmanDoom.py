"""Search algorithms used by the game AI and visual overlays."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Callable

from pycman.entities import Pos


@dataclass(frozen=True)
class SearchResult:
    """Result data needed both to move actors and explain a search visually."""

    path: list[Pos]
    explored: set[Pos]
    came_from: dict[Pos, Pos | None]
    frontier: set[Pos]


NeighborFn = Callable[[Pos], list[Pos]]


def dijkstra(start: Pos, goal: Pos, neighbors: NeighborFn) -> SearchResult:
    """Find the cheapest path when each maze edge has cost one."""
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
        if current == goal:
            return SearchResult(reconstruct_path(came_from, current), explored, came_from, frontier)

        for neighbor in neighbors(current):
            new_cost = best_cost[current] + 1
            if new_cost >= best_cost.get(neighbor, 10**9):
                continue
            best_cost[neighbor] = new_cost
            came_from[neighbor] = current
            tie_breaker += 1
            frontier.add(neighbor)
            heapq.heappush(open_heap, (new_cost, tie_breaker, neighbor))

    return SearchResult([start], explored, came_from, frontier)


def dijkstra_to_nearest_goal(start: Pos, goals: set[Pos], neighbors: NeighborFn) -> SearchResult:
    """Find a path to the closest reachable goal using only Dijkstra."""
    if not goals:
        return SearchResult([start], set(), {start: None}, set())

    open_heap: list[tuple[int, int, Pos]] = [(0, 0, start)]
    came_from: dict[Pos, Pos | None] = {start: None}
    best_cost: dict[Pos, int] = {start: 0}
    explored: set[Pos] = set()
    frontier: set[Pos] = {start}
    tie_breaker = 0

    while open_heap:
        cost, _, current = heapq.heappop(open_heap)
        frontier.discard(current)
        if current in explored:
            continue
        explored.add(current)
        if current in goals:
            return SearchResult(reconstruct_path(came_from, current), explored, came_from, frontier)

        for neighbor in neighbors(current):
            new_cost = cost + 1
            if new_cost >= best_cost.get(neighbor, 10**9):
                continue
            best_cost[neighbor] = new_cost
            came_from[neighbor] = current
            tie_breaker += 1
            frontier.add(neighbor)
            heapq.heappush(open_heap, (new_cost, tie_breaker, neighbor))

    return SearchResult([start], explored, came_from, frontier)


def reconstruct_path(came_from: dict[Pos, Pos | None], current: Pos) -> list[Pos]:
    """Walk a parent map backward and return a start-to-goal path."""
    path = [current]
    while came_from[current] is not None:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
