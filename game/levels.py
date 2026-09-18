"""Built-in level templates.

The solution order is retained for automated verification and is never shown
to the player by the base game.
"""

from game.models import ArrowSpec, Direction, Level


def arrow(arrow_id: str, row: int, col: int, direction: Direction) -> ArrowSpec:
    return ArrowSpec(arrow_id, row, col, direction)


LEVELS: tuple[Level, ...] = (
    Level(
        id=1,
        name="方向热身",
        rows=6,
        cols=6,
        arrows=(
            arrow("A", 4, 4, Direction.DOWN),
            arrow("B", 3, 5, Direction.LEFT),
            arrow("C", 3, 1, Direction.DOWN),
            arrow("D", 2, 1, Direction.DOWN),
            arrow("E", 5, 4, Direction.DOWN),
            arrow("F", 4, 3, Direction.RIGHT),
            arrow("G", 2, 3, Direction.RIGHT),
            arrow("H", 5, 3, Direction.RIGHT),
            arrow("I", 1, 4, Direction.RIGHT),
            arrow("J", 4, 0, Direction.DOWN),
            arrow("K", 1, 3, Direction.DOWN),
            arrow("L", 0, 4, Direction.UP),
        ),
        solution_order=tuple("CEGIJLBDAHFK"),
        par_seconds=60,
        difficulty="入门",
    ),
    Level(
        id=2,
        name="多链汇合",
        rows=7,
        cols=7,
        arrows=(
            arrow("A", 6, 0, Direction.UP),
            arrow("B", 6, 6, Direction.UP),
            arrow("C", 0, 3, Direction.RIGHT),
            arrow("D", 2, 3, Direction.DOWN),
            arrow("E", 0, 2, Direction.UP),
            arrow("F", 4, 5, Direction.LEFT),
            arrow("G", 5, 3, Direction.RIGHT),
            arrow("H", 1, 6, Direction.LEFT),
            arrow("I", 5, 0, Direction.UP),
            arrow("J", 4, 0, Direction.LEFT),
            arrow("K", 1, 3, Direction.DOWN),
            arrow("L", 6, 1, Direction.RIGHT),
            arrow("M", 3, 2, Direction.UP),
            arrow("N", 0, 5, Direction.RIGHT),
            arrow("O", 0, 6, Direction.RIGHT),
            arrow("P", 5, 1, Direction.RIGHT),
        ),
        solution_order=tuple("EGJOMDPFINKACHBL"),
        par_seconds=90,
        difficulty="进阶",
    ),
    Level(
        id=3,
        name="密集联锁",
        rows=7,
        cols=7,
        arrows=(
            arrow("A", 3, 4, Direction.RIGHT),
            arrow("B", 0, 6, Direction.LEFT),
            arrow("C", 2, 5, Direction.DOWN),
            arrow("D", 6, 6, Direction.RIGHT),
            arrow("E", 1, 5, Direction.DOWN),
            arrow("F", 3, 5, Direction.DOWN),
            arrow("G", 0, 5, Direction.UP),
            arrow("H", 6, 0, Direction.RIGHT),
            arrow("I", 2, 6, Direction.DOWN),
            arrow("J", 2, 2, Direction.UP),
            arrow("K", 1, 4, Direction.LEFT),
            arrow("L", 5, 4, Direction.DOWN),
            arrow("M", 4, 6, Direction.DOWN),
            arrow("N", 6, 5, Direction.RIGHT),
            arrow("O", 6, 1, Direction.RIGHT),
            arrow("P", 6, 4, Direction.RIGHT),
            arrow("Q", 0, 0, Direction.DOWN),
            arrow("R", 6, 2, Direction.RIGHT),
            arrow("S", 5, 2, Direction.UP),
            arrow("T", 2, 4, Direction.DOWN),
        ),
        solution_order=tuple("DGJKMNSIFPACLRETOHQB"),
        par_seconds=120,
        difficulty="困难",
    ),
)
