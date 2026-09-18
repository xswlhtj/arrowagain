"""Deterministic reverse construction for solvable random levels."""

from __future__ import annotations

import random
from dataclasses import dataclass

from game.models import Arrow, ArrowSpec, Direction, Level
from game.rules import is_blocked, validate_solution


@dataclass(frozen=True)
class DifficultyConfig:
    name: str
    rows: int
    cols: int
    min_arrows: int
    max_arrows: int
    min_initial: int
    max_initial: int
    min_depth: int
    par_seconds: int


DIFFICULTIES: dict[str, DifficultyConfig] = {
    "casual": DifficultyConfig("休闲", 6, 6, 12, 14, 5, 7, 4, 75),
    "standard": DifficultyConfig("标准", 7, 7, 18, 20, 3, 6, 7, 120),
    "hard": DifficultyConfig("困难", 8, 8, 26, 30, 2, 10, 9, 180),
}


def _arrow_id(index: int) -> str:
    result = ""
    value = index
    while True:
        value, remainder = divmod(value, 26)
        result = chr(65 + remainder) + result
        if value == 0:
            return result
        value -= 1


def _blocks(arrow: ArrowSpec, position: tuple[int, int]) -> bool:
    row, col = position
    if arrow.direction is Direction.UP:
        return col == arrow.col and row < arrow.row
    if arrow.direction is Direction.DOWN:
        return col == arrow.col and row > arrow.row
    if arrow.direction is Direction.LEFT:
        return row == arrow.row and col < arrow.col
    return row == arrow.row and col > arrow.col


def _construct(
    rng: random.Random,
    rows: int,
    cols: int,
    count: int,
) -> tuple[tuple[ArrowSpec, ...], tuple[str, ...]] | None:
    placed: list[ArrowSpec] = []
    occupied: set[tuple[int, int]] = set()
    directions = tuple(Direction)

    for index in range(count):
        runtime_placed = [
            Arrow(item.id, item.row, item.col, item.direction) for item in placed
        ]
        currently_available = {
            item.id
            for item in runtime_placed
            if not is_blocked(item, occupied, rows, cols)
        }
        candidates: list[tuple[ArrowSpec, int]] = []
        for row in range(rows):
            for col in range(cols):
                if (row, col) in occupied:
                    continue
                for direction in directions:
                    candidate = Arrow(_arrow_id(index), row, col, direction)
                    if is_blocked(candidate, occupied, rows, cols):
                        continue
                    dependency_gain = sum(
                        _blocks(existing, (row, col)) for existing in placed
                    )
                    safe_gain = sum(
                        existing.id in currently_available
                        and _blocks(existing, (row, col))
                        for existing in placed
                    )
                    spec = ArrowSpec(candidate.id, row, col, direction)
                    candidates.append((spec, safe_gain * 20 + dependency_gain))
        if not candidates:
            return None

        maximum = max(weight for _, weight in candidates)
        shortlist = [
            item for item in candidates if item[1] >= max(0, maximum - 1)
        ]
        spec, _ = rng.choice(shortlist)
        placed.append(spec)
        occupied.add((spec.row, spec.col))

    return tuple(placed), tuple(spec.id for spec in reversed(placed))


def dependency_metrics(level: Level) -> tuple[int, int, int]:
    arrows = [
        Arrow(spec.id, spec.row, spec.col, spec.direction) for spec in level.arrows
    ]
    occupied = {(arrow.row, arrow.col) for arrow in arrows}
    available = sum(
        not is_blocked(arrow, occupied, level.rows, level.cols)
        for arrow in arrows
    )

    dependencies: dict[str, set[str]] = {arrow.id: set() for arrow in arrows}
    edges = 0
    for arrow in arrows:
        dr, dc = arrow.direction.vector
        row, col = arrow.row + dr, arrow.col + dc
        while 0 <= row < level.rows and 0 <= col < level.cols:
            blocker = next(
                (item for item in arrows if item.row == row and item.col == col),
                None,
            )
            if blocker is not None:
                dependencies[arrow.id].add(blocker.id)
                edges += 1
            row += dr
            col += dc

    order_index = {arrow_id: index for index, arrow_id in enumerate(level.solution_order)}
    depth: dict[str, int] = {}
    for arrow_id in level.solution_order:
        earlier = [
            blocker
            for blocker in dependencies[arrow_id]
            if order_index.get(blocker, len(order_index)) < order_index[arrow_id]
        ]
        depth[arrow_id] = 1 + max((depth[item] for item in earlier), default=0)
    return available, edges, max(depth.values(), default=0)


def generate_level(
    seed: int,
    difficulty: str,
    *,
    count: int | None = None,
    level_id: int = 100,
    name: str | None = None,
) -> Level:
    config = DIFFICULTIES[difficulty]
    base_rng = random.Random(seed)
    target = count or base_rng.randint(config.min_arrows, config.max_arrows)
    fallback: Level | None = None

    for attempt in range(100):
        rng = random.Random(f"{seed}:{difficulty}:{attempt}")
        constructed = _construct(rng, config.rows, config.cols, target)
        if constructed is None:
            continue
        arrows, solution = constructed
        level = Level(
            id=level_id,
            name=name or f"随机{config.name}",
            rows=config.rows,
            cols=config.cols,
            arrows=arrows,
            solution_order=solution,
            par_seconds=config.par_seconds,
            difficulty=config.name,
            pack="random",
        )
        if validate_solution(level):
            continue
        initial, _, depth = dependency_metrics(level)
        direction_set = {arrow.direction for arrow in level.arrows}
        if len(direction_set) == 4:
            fallback = level
        if (
            config.min_initial <= initial <= config.max_initial
            and depth >= config.min_depth
            and len(direction_set) == 4
        ):
            return level

    if fallback is not None:
        return fallback
    raise RuntimeError("unable to generate a solvable level")
