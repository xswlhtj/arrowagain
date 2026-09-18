from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.progress import ProgressData, load_progress, save_progress, update_record


class ProgressTests(unittest.TestCase):
    def test_round_trip_and_record_updates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            progress = ProgressData(resume={"level_key": "classic:2"})
            self.assertTrue(
                update_record(
                    progress,
                    "classic:1",
                    score=1800,
                    elapsed_seconds=42.5,
                    stars=3,
                )
            )
            save_progress(path, progress)
            loaded = load_progress(path)
            self.assertEqual(loaded.resume, {"level_key": "classic:2"})
            self.assertEqual(loaded.records["classic:1"].best_score, 1800)
            self.assertEqual(loaded.records["classic:1"].best_time_ms, 42500)

    def test_invalid_json_returns_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            path.write_text("{broken", encoding="utf-8")
            loaded = load_progress(path)
            self.assertEqual(loaded.records, {})
            self.assertIsNone(loaded.resume)


if __name__ == "__main__":
    unittest.main()
