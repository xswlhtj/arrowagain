"""Pure game rules with no dependency on Pygame."""

from __future__ import annotations

from game.models import (
    MAX_MISTAKES,
    Arrow,
    ArrowState,
    ClickResult,
    Direction,
    GameSession,
    Level,
    ScreenState,
    runtime_arrows,
)


def direction_vector(direction: Direction) -> tuple[int, int]:
    return direction.vector


def is_blocked(
    arrow: Arrow,
    occupied: set[tuple[int, int]],
    rows: int,
    cols: int,
) -> bool:
    """Return whether another arrow exists ahead before the board boundary."""

    dr, dc = direction_vector(arrow.direction)
    row, col = arrow.row + dr, arrow.col + dc
    while 0 <= row < rows and 0 <= col < cols:
        if (row, col) in occupied:
            return True
        row += dr
        col += dc
    return False


def find_arrow_at(arrows: list[Arrow], row: int, col: int) -> Arrow | None:
    return next(
        (arrow for arrow in arrows if arrow.row == row and arrow.col == col),
        None,
    )


def find_arrow_by_id(arrows: list[Arrow], arrow_id: str) -> Arrow | None:
    return next((arrow for arrow in arrows if arrow.id == arrow_id), None)


def start_level(session: GameSession, level_index: int, level: Level) -> None:
    session.current_level_index = level_index
    session.remaining_mistakes = MAX_MISTAKES
    session.arrows = runtime_arrows(level)
    session.screen_state = ScreenState.PLAYING
    session.message = "请选择一支箭头"
    session.elapsed_seconds = 0.0
    session.successful_moves = 0
    session.collision_count = 0
    session.hints_used = 0
    session.hint_arrow_id = None


def attempt_arrow_click(
    session: GameSession,
    level: Level,
    arrow_id: str,
) -> ClickResult:
    """Resolve a click and mark the arrow for animation.

    Removal and result-screen transitions happen in the finalize functions so
    the UI can finish the visual feedback first.
    """

    if session.screen_state is not ScreenState.PLAYING:
        return ClickResult.IGNORED

    arrow = find_arrow_by_id(session.arrows, arrow_id)
    if arrow is None or arrow.state is not ArrowState.IDLE:
        return ClickResult.IGNORED

    occupied = {(item.row, item.col) for item in session.arrows}
    if is_blocked(arrow, occupied, level.rows, level.cols):
        arrow.state = ArrowState.COLLIDING
        session.remaining_mistakes = max(0, session.remaining_mistakes - 1)
        session.message = "路径被阻挡，失误 -1"
        return ClickResult.COLLIDE

    arrow.state = ArrowState.FLYING
    session.message = "成功飞出！"
    return ClickResult.FLY


def finalize_collision(session: GameSession, arrow_id: str) -> None:
    arrow = find_arrow_by_id(session.arrows, arrow_id)
    if arrow is not None:
        arrow.state = ArrowState.IDLE
        session.collision_count += 1
    if session.remaining_mistakes == 0:
        session.screen_state = ScreenState.FAILED


def finalize_flight(
    session: GameSession,
    arrow_id: str,
    *,
    is_last_level: bool,
) -> None:
    if find_arrow_by_id(session.arrows, arrow_id) is not None:
        session.successful_moves += 1
    session.arrows = [arrow for arrow in session.arrows if arrow.id != arrow_id]
    if session.arrows:
        return
    session.screen_state = (
        ScreenState.ALL_CLEAR if is_last_level else ScreenState.LEVEL_CLEAR
    )


def screen_to_cell(
    x: int,
    y: int,
    board_rect: tuple[int, int, int, int],
    cell_size: int,
) -> tuple[int, int] | None:
    left, top, width, height = board_rect
    if not (left <= x < left + width and top <= y < top + height):
        return None
    return (y - top) // cell_size, (x - left) // cell_size


def validate_level(level: Level) -> list[str]:
    errors: list[str] = []
    if level.rows <= 0 or level.cols <= 0:
        errors.append("board dimensions must be positive")

    ids: set[str] = set()
    positions: set[tuple[int, int]] = set()
    for arrow in level.arrows:
        if arrow.id in ids:
            errors.append(f"duplicate arrow id: {arrow.id}")
        ids.add(arrow.id)
        if not (0 <= arrow.row < level.rows and 0 <= arrow.col < level.cols):
            errors.append(f"arrow {arrow.id} is outside the board")
        if (arrow.row, arrow.col) in positions:
            errors.append(f"duplicate position: ({arrow.row}, {arrow.col})")
        positions.add((arrow.row, arrow.col))

    if set(level.solution_order) != ids or len(level.solution_order) != len(ids):
        errors.append("solution order must contain every arrow exactly once")
    return errors


def validate_solution(level: Level) -> list[str]:
    """Check that every step in the documented solution can fly."""

    errors = validate_level(level)
    if errors:
        return errors

    session = GameSession()
    start_level(session, 0, level)
    for arrow_id in level.solution_order:
        result = attempt_arrow_click(session, level, arrow_id)
        if result is not ClickResult.FLY:
            errors.append(f"arrow {arrow_id} is blocked in the solution order")
            break
        finalize_flight(session, arrow_id, is_last_level=False)
        if session.screen_state is ScreenState.LEVEL_CLEAR and session.arrows:
            errors.append("level cleared before all arrows were removed")
            break
        if session.arrows:
            session.screen_state = ScreenState.PLAYING

    if not errors and session.arrows:
        errors.append("solution order did not clear the board")
    return errors
