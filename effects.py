"""Small time-based particles that never affect game-state coordinates."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    lifetime: float
    size: float
    elapsed: float = 0.0

    @property
    def done(self) -> bool:
        return self.elapsed >= self.lifetime


class ParticleSystem:
    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self._rng = random.Random(20260917)

    def clear(self) -> None:
        self.particles.clear()

    def emit(
        self,
        position: tuple[float, float],
        color: tuple[int, int, int],
        *,
        count: int = 8,
    ) -> None:
        for _ in range(count):
            angle = self._rng.random() * math.tau
            speed = self._rng.uniform(28.0, 78.0)
            self.particles.append(
                Particle(
                    position[0],
                    position[1],
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    color,
                    self._rng.uniform(0.28, 0.52),
                    self._rng.uniform(2.0, 5.0),
                )
            )
        if len(self.particles) > 120:
            self.particles = self.particles[-120:]

    def update(self, dt: float) -> None:
        for particle in self.particles:
            particle.elapsed += dt
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vx *= 0.96
            particle.vy *= 0.96
        self.particles = [item for item in self.particles if not item.done]

    def draw(self, surface: pygame.Surface) -> None:
        for particle in self.particles:
            progress = min(1.0, particle.elapsed / particle.lifetime)
            alpha = int(220 * (1.0 - progress))
            radius = max(1, int(particle.size * (1.0 - progress * 0.5)))
            canvas = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(
                canvas,
                (*particle.color, alpha),
                (radius + 1, radius + 1),
                radius,
            )
            surface.blit(canvas, (int(particle.x) - radius, int(particle.y) - radius))
