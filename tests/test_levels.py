from __future__ import annotations

import unittest

from game.levels import LEVELS
from game.models import Direction
from game.rules import validate_level, validate_solution


def dependency_metrics(level) -> tuple[int, int, int]:
    position_to_id = {(arrow.row, arrow.col): arrow.id for arrow in level.arrows}
    dependencies: dict[str, set[str]] = {}
    for arrow in level.arrows:
        dr, dc = arrow.direction.vector
        row, col = arrow.row + dr, arrow.col + dc
        blockers: set[str] = set()
        while 0 <= row < level.rows and 0 <= col < level.cols:
            blocker = position_to_id.get((row, col))
            if blocker is not None:
                blockers.add(blocker)
            row += dr
            col += dc
        dependencies[arrow.id] = blockers

    memo: dict[str, int] = {}

    def depth(arrow_id: str, visiting: set[str]) -> int:
        if arrow_id in memo:
            return memo[arrow_id]
        if arrow_id in visiting:
            raise AssertionError("level contains a dependency cycle")
        next_visiting = visiting | {arrow_id}
        blockers = dependencies[arrow_id]
        result = 1 if not blockers else 1 + max(depth(item, next_visiting) for item in blockers)
        memo[arrow_id] = result
        return result

    dependency_count = sum(len(items) for items in dependencies.values())
    initial_moves = sum(not items for items in dependencies.values())
    longest_depth = max(depth(arrow_id, set()) for arrow_id in dependencies)
    return dependency_count, initial_moves, longest_depth


class LevelTests(unittest.TestCase):
    def test_sizes_and_arrow_counts_increase(self) -> None:
        self.assertEqual(
            [(level.rows, level.cols) for level in LEVELS],
            [(6, 6), (7, 7), (7, 7)],
        )
        self.assertEqual([len(level.arrows) for level in LEVELS], [12, 16, 20])

    def test_every_level_contains_all_four_directions(self) -> None:
        expected = set(Direction)
        for level in LEVELS:
            with self.subTest(level=level.id):
                self.assertEqual({arrow.direction for arrow in level.arrows}, expected)

    def test_level_templates_are_valid_and_solvable(self) -> None:
        for level in LEVELS:
            with self.subTest(level=level.id):
                self.assertEqual(validate_level(level), [])
                self.assertEqual(validate_solution(level), [])

    def test_documented_difficulty_metrics(self) -> None:
        self.assertEqual(
            [dependency_metrics(level) for level in LEVELS],
            [(8, 6, 4), (16, 4, 6), (33, 4, 8)],
        )


if __name__ == "__main__":
    unittest.main()

