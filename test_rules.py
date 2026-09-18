from __future__ import annotations

import unittest

from game.levels import LEVELS
from game.models import (
    MAX_MISTAKES,
    Arrow,
    ArrowState,
    ClickResult,
    Direction,
    GameSession,
    ScreenState,
)
from game.rules import (
    attempt_arrow_click,
    finalize_collision,
    finalize_flight,
    find_arrow_at,
    is_blocked,
    screen_to_cell,
    start_level,
)


class PathRuleTests(unittest.TestCase):
    def test_four_direction_vectors_and_blocking(self) -> None:
        cases = (
            (Direction.UP, (1, 2)),
            (Direction.DOWN, (3, 2)),
            (Direction.LEFT, (2, 1)),
            (Direction.RIGHT, (2, 3)),
        )
        for direction, blocker in cases:
            with self.subTest(direction=direction):
                arrow = Arrow("A", 2, 2, direction)
                self.assertTrue(is_blocked(arrow, {blocker}, 5, 5))

    def test_arrow_behind_or_diagonal_does_not_block(self) -> None:
        arrow = Arrow("A", 2, 2, Direction.RIGHT)
        occupied = {(2, 1), (1, 3), (3, 3)}
        self.assertFalse(is_blocked(arrow, occupied, 5, 5))

    def test_edge_arrows_facing_out_can_fly_in_all_directions(self) -> None:
        cases = (
            Arrow("U", 0, 2, Direction.UP),
            Arrow("D", 4, 2, Direction.DOWN),
            Arrow("L", 2, 0, Direction.LEFT),
            Arrow("R", 2, 4, Direction.RIGHT),
        )
        for arrow in cases:
            with self.subTest(direction=arrow.direction):
                self.assertFalse(is_blocked(arrow, {(2, 2)}, 5, 5))


    def test_screen_to_cell_handles_edges(self) -> None:
        board = (100, 200, 420, 420)
        self.assertEqual(screen_to_cell(100, 200, board, 60), (0, 0))
        self.assertEqual(screen_to_cell(519, 619, board, 60), (6, 6))
        self.assertIsNone(screen_to_cell(520, 620, board, 60))
        self.assertIsNone(screen_to_cell(99, 200, board, 60))


class SessionRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.level = LEVELS[0]
        self.session = GameSession()
        start_level(self.session, 0, self.level)

    def test_start_level_creates_runtime_copy_and_three_mistakes(self) -> None:
        self.assertEqual(self.session.remaining_mistakes, MAX_MISTAKES)
        self.assertEqual(len(self.session.arrows), 12)
        self.session.arrows.pop()
        self.assertEqual(len(self.level.arrows), 12)

    def test_blocked_click_retains_arrow_and_deducts_once(self) -> None:
        result = attempt_arrow_click(self.session, self.level, "K")
        self.assertIs(result, ClickResult.COLLIDE)
        self.assertEqual(self.session.remaining_mistakes, 2)
        self.assertIsNotNone(find_arrow_at(self.session.arrows, 1, 3))
        self.assertIs(
            find_arrow_at(self.session.arrows, 1, 3).state,
            ArrowState.COLLIDING,
        )

        second_result = attempt_arrow_click(self.session, self.level, "K")
        self.assertIs(second_result, ClickResult.IGNORED)
        self.assertEqual(self.session.remaining_mistakes, 2)

    def test_third_mistake_enters_failed_state_after_feedback(self) -> None:
        for expected in (2, 1, 0):
            self.assertIs(
                attempt_arrow_click(self.session, self.level, "K"),
                ClickResult.COLLIDE,
            )
            self.assertEqual(self.session.remaining_mistakes, expected)
            finalize_collision(self.session, "K")

        self.assertIs(self.session.screen_state, ScreenState.FAILED)

    def test_successful_arrow_is_removed_after_animation(self) -> None:
        self.assertIs(
            attempt_arrow_click(self.session, self.level, "C"),
            ClickResult.FLY,
        )
        self.assertEqual(len(self.session.arrows), 12)
        finalize_flight(self.session, "C", is_last_level=False)
        self.assertEqual(len(self.session.arrows), 11)

    def test_restart_restores_layout_and_mistakes(self) -> None:
        attempt_arrow_click(self.session, self.level, "C")
        finalize_flight(self.session, "C", is_last_level=False)
        attempt_arrow_click(self.session, self.level, "K")
        finalize_collision(self.session, "K")
        start_level(self.session, 0, self.level)

        self.assertEqual(len(self.session.arrows), 12)
        self.assertEqual(self.session.remaining_mistakes, 3)
        self.assertIs(self.session.screen_state, ScreenState.PLAYING)


if __name__ == "__main__":
    unittest.main()
