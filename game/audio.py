"""Optional synthesized sound effects with silent fallback."""

from __future__ import annotations

import array
import math

import pygame


class AudioManager:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.available = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=2)
            self.sounds = {
                "click": self._tone(620, 0.055, 0.18),
                "fly": self._tone(880, 0.12, 0.22, end_frequency=1320),
                "collide": self._tone(170, 0.14, 0.24, end_frequency=105),
                "clear": self._tone(740, 0.28, 0.24, end_frequency=1180),
                "fail": self._tone(320, 0.25, 0.22, end_frequency=180),
            }
            self.available = True
        except pygame.error:
            self.available = False

    @staticmethod
    def _tone(
        frequency: float,
        duration: float,
        volume: float,
        *,
        end_frequency: float | None = None,
    ) -> pygame.mixer.Sound:
        mixer_frequency, _, channels = pygame.mixer.get_init()
        frame_count = max(1, int(mixer_frequency * duration))
        samples = array.array("h")
        end = end_frequency or frequency
        phase = 0.0
        for index in range(frame_count):
            progress = index / frame_count
            current = frequency + (end - frequency) * progress
            phase += math.tau * current / mixer_frequency
            envelope = min(1.0, progress * 12.0) * (1.0 - progress) ** 2
            value = int(32767 * volume * envelope * math.sin(phase))
            for _ in range(channels):
                samples.append(value)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, name: str) -> None:
        if self.enabled and self.available and name in self.sounds:
            self.sounds[name].play()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled and self.available:
            pygame.mixer.stop()
