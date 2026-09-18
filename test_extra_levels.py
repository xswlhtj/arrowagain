from __future__ import annotations

import unittest

from game.extra_levels import EXTRA_LEVELS
from game.models import Direction
from game.rules import validate_level, validate_solution


class ExtraLevelTests(unittest.TestCase):
    def test_challenge_levels_are_frozen_and_solvable(self) -> None:
        self.assertEqual([len(level.arrows) for level in EXTRA_LEVELS], [24, 28, 32])
        for level in EXTRA_LEVELS:
            self.assertEqual((level.rows, level.cols), (8, 8))
            self.assertEqual(level.pack, "challenge")
            self.assertEqual({arrow.direction for arrow in level.arrows}, set(Direction))
            self.assertEqual(validate_level(level), [])
            self.assertEqual(validate_solution(level), [])


if __name__ == "__main__":
    unittest.main()
