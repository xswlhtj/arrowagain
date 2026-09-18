from __future__ import annotations

import unittest

from game.hints import available_arrow_ids, choose_hint
from game.levels import LEVELS
from game.models import GameSession
from game.rules import find_arrow_by_id, is_blocked, start_level


class HintTests(unittest.TestCase):
    def test_hint_is_always_currently_available(self) -> None:
        for level in LEVELS:
            session = GameSession()
            start_level(session, 0, level)
            hint = choose_hint(session.arrows, level.rows, level.cols)
            self.assertIsNotNone(hint)
            arrow = find_arrow_by_id(session.arrows, hint)
            occupied = {(item.row, item.col) for item in session.arrows}
            self.assertFalse(is_blocked(arrow, occupied, level.rows, level.cols))

    def test_hint_does_not_modify_input(self) -> None:
        level = LEVELS[0]
        session = GameSession()
        start_level(session, 0, level)
        before = [(item.id, item.row, item.col, item.state) for item in session.arrows]
        first = choose_hint(session.arrows, level.rows, level.cols)
        second = choose_hint(session.arrows, level.rows, level.cols)
        after = [(item.id, item.row, item.col, item.state) for item in session.arrows]
        self.assertEqual(first, second)
        self.assertEqual(before, after)
        self.assertIn(first, available_arrow_ids(session.arrows, level.rows, level.cols))


if __name__ == "__main__":
    unittest.main()
