"""Core data models shared by the rules and UI layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


MAX_MISTAKES = 3


class Direction(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

    @property
    def vector(self) -> tuple[int, int]:
        return {
            Direction.UP: (-1, 0),
            Direction.DOWN: (1, 0),
            Direction.LEFT: (0, -1),
            Direction.RIGHT: (0, 1),
        }[self]


class ArrowState(str, Enum):
    IDLE = "IDLE"
    FLYING = "FLYING"
    COLLIDING = "COLLIDING"


class ScreenState(str, Enum):
    START = "START"
    LEVEL_SELECT = "LEVEL_SELECT"
    PLAYING = "PLAYING"
    LEVEL_CLEAR = "LEVEL_CLEAR"
    FAILED = "FAILED"
    ALL_CLEAR = "ALL_CLEAR"


class ClickResult(str, Enum):
    FLY = "FLY"
    COLLIDE = "COLLIDE"
    IGNORED = "IGNORED"


@dataclass(frozen=True)
class ArrowSpec:
    id: str
    row: int
    col: int
    direction: Direction


@dataclass
class Arrow:
    id: str
    row: int
    col: int
    direction: Direction
    state: ArrowState = ArrowState.IDLE


@dataclass(frozen=True)
class Level:
    id: int
    name: str
    rows: int
    cols: int
    arrows: tuple[ArrowSpec, ...]
    solution_order: tuple[str, ...]
    par_seconds: int = 90
    difficulty: str = "普通"
    pack: str = "classic"


@dataclass
class GameSession:
    current_level_index: int = 0
    remaining_mistakes: int = MAX_MISTAKES
    arrows: list[Arrow] = field(default_factory=list)
    screen_state: ScreenState = ScreenState.START
    message: str = ""
    elapsed_seconds: float = 0.0
    successful_moves: int = 0
    collision_count: int = 0
    hints_used: int = 0
    hint_arrow_id: str | None = None


def runtime_arrows(level: Level) -> list[Arrow]:
    """Create mutable runtime arrows from an immutable level template."""

    return [
        Arrow(spec.id, spec.row, spec.col, spec.direction)
        for spec in level.arrows
    ]
