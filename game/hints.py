"""Hint selection built on the same path rule used by normal clicks."""

from __future__ import annotations

from game.models import Arrow
from game.rules import is_blocked


def available_arrow_ids(
    arrows: list[Arrow],
    rows: int,
    cols: int,
) -> list[str]:
    occupied = {(arrow.row, arrow.col) for arrow in arrows}
    return [
        arrow.id
        for arrow in arrows
        if not is_blocked(arrow, occupied, rows, cols)
    ]


def choose_hint(
    arrows: list[Arrow],
    rows: int,
    cols: int,
) -> str | None:
    available = set(available_arrow_ids(arrows, rows, cols))
    if not available:
        return None

    before = len(available)
    candidates: list[tuple[int, int, int, str]] = []
    for arrow in arrows:
        if arrow.id not in available:
            continue
        remaining = [item for item in arrows if item.id != arrow.id]
        newly_available = len(available_arrow_ids(remaining, rows, cols)) - (before - 1)
        candidates.append((-newly_available, arrow.row, arrow.col, arrow.id))
    return min(candidates)[3]
