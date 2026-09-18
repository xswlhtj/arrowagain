"""Versioned JSON progress storage with validation and atomic writes."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LevelRecord:
    cleared: bool = False
    best_score: int = 0
    best_time_ms: int | None = None
    best_stars: int = 0


@dataclass
class ProgressData:
    version: int = 1
    records: dict[str, LevelRecord] = field(default_factory=dict)
    resume: dict[str, Any] | None = None
    sound_enabled: bool = True


def _valid_record(value: object) -> LevelRecord | None:
    if not isinstance(value, dict):
        return None
    time_value = value.get("best_time_ms")
    if time_value is not None and (not isinstance(time_value, int) or time_value < 0):
        time_value = None
    return LevelRecord(
        cleared=bool(value.get("cleared", False)),
        best_score=max(0, int(value.get("best_score", 0))),
        best_time_ms=time_value,
        best_stars=min(3, max(0, int(value.get("best_stars", 0)))),
    )


def load_progress(path: Path) -> ProgressData:
    if not path.exists():
        return ProgressData()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("version") != 1:
            return ProgressData()
        records: dict[str, LevelRecord] = {}
        raw_records = raw.get("records", {})
        if isinstance(raw_records, dict):
            for key, value in raw_records.items():
                record = _valid_record(value)
                if isinstance(key, str) and record is not None:
                    records[key] = record
        resume = raw.get("resume")
        if resume is not None and not isinstance(resume, dict):
            resume = None
        settings = raw.get("settings", {})
        sound_enabled = (
            bool(settings.get("sound_enabled", True))
            if isinstance(settings, dict)
            else True
        )
        return ProgressData(
            records=records,
            resume=resume,
            sound_enabled=sound_enabled,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return ProgressData()


def save_progress(path: Path, progress: ProgressData) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": progress.version,
        "records": {
            key: asdict(record) for key, record in progress.records.items()
        },
        "resume": progress.resume,
        "settings": {"sound_enabled": progress.sound_enabled},
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def update_record(
    progress: ProgressData,
    level_key: str,
    *,
    score: int,
    elapsed_seconds: float,
    stars: int,
) -> bool:
    record = progress.records.setdefault(level_key, LevelRecord())
    elapsed_ms = max(0, int(elapsed_seconds * 1000))
    changed = not record.cleared
    record.cleared = True
    if score > record.best_score:
        record.best_score = score
        changed = True
    if record.best_time_ms is None or elapsed_ms < record.best_time_ms:
        record.best_time_ms = elapsed_ms
        changed = True
    if stars > record.best_stars:
        record.best_stars = stars
        changed = True
    return changed
