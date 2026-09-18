"""Pure score, timer formatting, and star-rating helpers."""

from __future__ import annotations


def calculate_score(
    successful_moves: int,
    remaining_mistakes: int,
    elapsed_seconds: float,
    par_seconds: int,
    hints_used: int,
    *,
    cleared: bool,
) -> int:
    base = max(0, successful_moves) * 100
    hint_penalty = max(0, hints_used) * 100
    if not cleared:
        return max(0, base - hint_penalty)

    mistake_bonus = max(0, remaining_mistakes) * 150
    time_bonus = max(0, par_seconds - int(max(0.0, elapsed_seconds))) * 10
    return max(0, base + mistake_bonus + time_bonus - hint_penalty)


def calculate_stars(
    remaining_mistakes: int,
    elapsed_seconds: float,
    par_seconds: int,
    hints_used: int,
    *,
    cleared: bool,
) -> int:
    if not cleared:
        return 0
    if (
        remaining_mistakes == 3
        and hints_used == 0
        and elapsed_seconds <= par_seconds
    ):
        return 3
    if (
        remaining_mistakes >= 2
        and hints_used <= 1
        and elapsed_seconds <= par_seconds * 1.5
    ):
        return 2
    return 1


def format_time(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, remainder = divmod(total, 60)
    return f"{minutes:02d}:{remainder:02d}"
