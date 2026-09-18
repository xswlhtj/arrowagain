from __future__ import annotations

import unittest

from game.scoring import calculate_score, calculate_stars, format_time


class ScoringTests(unittest.TestCase):
    def test_score_bonuses_and_hint_penalty(self) -> None:
        self.assertEqual(
            calculate_score(12, 3, 40.9, 60, 1, cleared=True),
            1750,
        )

    def test_live_score_never_goes_negative(self) -> None:
        self.assertEqual(
            calculate_score(0, 3, 0, 60, 8, cleared=False),
            0,
        )

    def test_star_boundaries(self) -> None:
        self.assertEqual(calculate_stars(3, 60, 60, 0, cleared=True), 3)
        self.assertEqual(calculate_stars(2, 90, 60, 1, cleared=True), 2)
        self.assertEqual(calculate_stars(1, 91, 60, 0, cleared=True), 1)
        self.assertEqual(calculate_stars(3, 1, 60, 0, cleared=False), 0)

    def test_time_format(self) -> None:
        self.assertEqual(format_time(78.9), "01:18")


if __name__ == "__main__":
    unittest.main()
