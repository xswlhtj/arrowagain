from __future__ import annotations

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game.animation import AnimationKind
from game.app import GameApp, WINDOW_SIZE
from game.extra_levels import EXTRA_LEVELS
from game.generator import generate_level
from game.levels import LEVELS
from game.models import ScreenState
from game.progress import update_record
from game.rules import find_arrow_by_id


class AppFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = GameApp()

    def tearDown(self) -> None:
        pygame.quit()

    def click_arrow(self, arrow_id: str) -> None:
        arrow = find_arrow_by_id(self.app.session.arrows, arrow_id)
        self.assertIsNotNone(arrow)
        board, cell_size = self.app._board_layout()
        position = (
            int(board.left + (arrow.col + 0.5) * cell_size),
            int(board.top + (arrow.row + 0.5) * cell_size),
        )
        self.app._handle_click(position)

    def test_all_screens_render_at_native_resolution(self) -> None:
        self.assertEqual(self.app.screen.get_size(), WINDOW_SIZE)
        self.assertIsNotNone(self.app.background)
        if sys.platform == "win32":
            self.assertEqual(
                os.environ.get("SDL_WINDOWS_DPI_AWARENESS"),
                "permonitorv2",
            )

        self.app.draw()
        self.app.session.screen_state = ScreenState.LEVEL_SELECT
        self.app.draw()
        self.app.start_game()
        for state in (
            ScreenState.PLAYING,
            ScreenState.LEVEL_CLEAR,
            ScreenState.FAILED,
            ScreenState.ALL_CLEAR,
        ):
            self.app.session.screen_state = state
            self.app.draw()

    def test_documented_solution_clears_all_three_levels(self) -> None:
        self.app.start_game()
        for level_index, level in enumerate(LEVELS):
            self.assertEqual(self.app.session.current_level_index, level_index)
            for arrow_id in level.solution_order:
                self.click_arrow(arrow_id)
                self.assertIsNotNone(self.app.animation)
                self.assertIs(self.app.animation.kind, AnimationKind.FLY)
                self.app.update(1.0)

            expected = (
                ScreenState.ALL_CLEAR
                if level_index == len(LEVELS) - 1
                else ScreenState.LEVEL_CLEAR
            )
            self.assertIs(self.app.session.screen_state, expected)
            if expected is ScreenState.LEVEL_CLEAR:
                self.app._activate_result_primary()

    def test_three_collisions_fail_then_restart_restores_level(self) -> None:
        self.app.start_game()
        for remaining in (2, 1, 0):
            self.click_arrow("K")
            self.assertIs(self.app.animation.kind, AnimationKind.COLLIDE)
            self.assertIn("阻挡", self.app.session.message)
            self.assertEqual(self.app.session.remaining_mistakes, remaining)
            self.app.update(1.0)

        self.assertIs(self.app.session.screen_state, ScreenState.FAILED)
        self.app._activate_result_primary()
        self.assertIs(self.app.session.screen_state, ScreenState.PLAYING)
        self.assertEqual(self.app.session.remaining_mistakes, 3)
        self.assertEqual(len(self.app.session.arrows), 12)

    def test_blank_cell_click_does_not_change_state(self) -> None:
        self.app.start_game()
        board, cell_size = self.app._board_layout()
        before = (len(self.app.session.arrows), self.app.session.remaining_mistakes)
        self.app._handle_click(
            (board.left + cell_size // 2, board.top + cell_size // 2)
        )
        after = (len(self.app.session.arrows), self.app.session.remaining_mistakes)
        self.assertEqual(after, before)
        self.assertIsNone(self.app.animation)

    def test_hint_marks_a_safe_arrow_without_changing_board(self) -> None:
        self.app.start_game()
        before = [arrow.id for arrow in self.app.session.arrows]
        self.app._show_hint()
        self.assertIn(
            self.app.session.hint_arrow_id,
            [arrow.id for arrow in self.app.session.arrows],
        )
        self.assertEqual(self.app.session.hints_used, 1)
        self.assertEqual(before, [arrow.id for arrow in self.app.session.arrows])

    def test_resume_restores_a_settled_fixed_level(self) -> None:
        self.app.start_game()
        self.click_arrow("C")
        self.app.update(1.0)
        self.app.session.elapsed_seconds = 12.5
        self.app._save_resume()
        self.app._go_home()
        self.assertTrue(self.app._resume_game())
        self.assertEqual(len(self.app.session.arrows), 11)
        self.assertEqual(self.app.session.elapsed_seconds, 12.5)
        self.assertNotIn("C", [arrow.id for arrow in self.app.session.arrows])

    def test_challenge_unlock_and_random_start(self) -> None:
        self.assertFalse(self.app._is_unlocked(EXTRA_LEVELS[0]))
        update_record(
            self.app.progress,
            "classic:3",
            score=1,
            elapsed_seconds=1,
            stars=1,
        )
        self.assertTrue(self.app._is_unlocked(EXTRA_LEVELS[0]))

        self.app._start_random_level("casual", 12345)
        expected = generate_level(12345, "casual")
        self.assertEqual(self.app.level.arrows, expected.arrows)
        self.assertEqual(self.app.random_seed, 12345)
        self.assertEqual(self.app.session.remaining_mistakes, 3)
        self.app.start_game(0)
        self.assertEqual(self.app.random_seed, 12345)
        self.assertEqual(self.app.random_difficulty, "casual")


if __name__ == "__main__":
    unittest.main()
