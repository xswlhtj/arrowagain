from __future__ import annotations

import unittest

from game.generator import generate_level
from game.rules import validate_level, validate_solution


class GeneratorTests(unittest.TestCase):
    def test_same_seed_repeats_and_is_solvable(self) -> None:
        first = generate_level(20260917, "standard")
        second = generate_level(20260917, "standard")
        self.assertEqual(first.arrows, second.arrows)
        self.assertEqual(first.solution_order, second.solution_order)
        self.assertEqual(validate_level(first), [])
        self.assertEqual(validate_solution(first), [])
        self.assertEqual({arrow.direction for arrow in first.arrows}, set(type(first.arrows[0].direction)))

    def test_all_presets_generate_valid_levels(self) -> None:
        for index, difficulty in enumerate(("casual", "standard", "hard")):
            level = generate_level(700 + index, difficulty)
            self.assertEqual(validate_solution(level), [])


if __name__ == "__main__":
    unittest.main()
