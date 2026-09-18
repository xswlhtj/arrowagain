"""Time-based arrow animation helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from game.models import Direction


class AnimationKind(str, Enum):
    FLY = "FLY"
    COLLIDE = "COLLIDE"


@dataclass
class ArrowAnimation:
    arrow_id: str
    direction: Direction
    kind: AnimationKind
    duration: float
    distance: float
    elapsed: float = 0.0

    def advance(self, dt: float) -> None:
        self.elapsed = min(self.duration, self.elapsed + dt)

    @property
    def progress(self) -> float:
        return 1.0 if self.duration <= 0 else self.elapsed / self.duration

    @property
    def done(self) -> bool:
        return self.elapsed >= self.duration

    def offset(self) -> tuple[float, float]:
        dr, dc = self.direction.vector
        if self.kind is AnimationKind.FLY:
            eased = 1.0 - (1.0 - self.progress) ** 3
            amount = self.distance * eased
        else:
            amount = math.sin(self.progress * math.pi * 4.0) * self.distance
        return dc * amount, dr * amount

