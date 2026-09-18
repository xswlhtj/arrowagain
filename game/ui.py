"""Reusable Pygame drawing helpers for the dark glass UI theme."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

import pygame

from game.models import Direction


Color = tuple[int, int, int]

BACKGROUND: Color = (5, 13, 35)
PANEL: Color = (13, 29, 61)
PANEL_LIGHT: Color = (19, 42, 82)
TEXT: Color = (238, 246, 255)
MUTED: Color = (154, 178, 211)
BLUE: Color = (77, 132, 255)
BLUE_DARK: Color = (42, 91, 217)
BLUE_PALE: Color = (31, 62, 118)
CYAN: Color = (66, 220, 255)
GREEN: Color = (57, 220, 156)
RED: Color = (255, 91, 116)
GOLD: Color = (255, 190, 76)
VIOLET: Color = (172, 119, 255)
HEART_RED: Color = (255, 91, 116)
GRID_LIGHT: Color = (21, 48, 91)
GRID_DARK: Color = (14, 36, 73)
BORDER: Color = (74, 126, 207)
DISABLED: Color = (77, 94, 125)

DIRECTION_COLORS: dict[Direction, Color] = {
    Direction.UP: CYAN,
    Direction.DOWN: VIOLET,
    Direction.LEFT: GOLD,
    Direction.RIGHT: BLUE,
}


@dataclass
class FontBook:
    _cache: dict[tuple[int, bool], pygame.font.Font] = field(default_factory=dict)
    font_path: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.font_path = pygame.font.match_font(
            "microsoftyahei,notosanscjk,simhei,segoeui,arial"
        )

    def get(self, size: int, *, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._cache:
            font = (
                pygame.font.Font(self.font_path, size)
                if self.font_path
                else pygame.font.Font(None, size)
            )
            font.set_bold(bold)
            self._cache[key] = font
        return self._cache[key]


@dataclass
class Button:
    rect: pygame.Rect
    text: str
    primary: bool = True
    enabled: bool = True

    def contains(self, position: tuple[int, int]) -> bool:
        return self.enabled and self.rect.collidepoint(position)

    def draw(
        self,
        surface: pygame.Surface,
        fonts: FontBook,
        mouse_position: tuple[int, int],
    ) -> None:
        hovered = self.contains(mouse_position)
        pressed = hovered and pygame.mouse.get_pressed(num_buttons=3)[0]
        rect = self.rect.move(0, 2) if pressed else self.rect

        if not self.enabled:
            fill = DISABLED
            text_color = MUTED
            border = DISABLED
        elif self.primary:
            fill = BLUE_DARK if pressed else (BLUE if hovered else (49, 101, 225))
            text_color = TEXT
            border = CYAN if hovered else (91, 145, 255)
        else:
            fill = (29, 57, 104) if hovered else (17, 38, 76)
            text_color = TEXT if hovered else (200, 220, 244)
            border = CYAN if hovered else BORDER

        if hovered and self.enabled:
            glow = rect.inflate(10, 10)
            pygame.draw.rect(surface, (25, 67, 139), glow, border_radius=17)
        pygame.draw.rect(surface, fill, rect, border_radius=13)
        pygame.draw.rect(surface, border, rect, width=2, border_radius=13)
        if self.primary and self.enabled:
            pygame.draw.line(
                surface,
                (124, 176, 255),
                (rect.left + 16, rect.top + 2),
                (rect.right - 16, rect.top + 2),
                2,
            )
        draw_text(
            surface,
            self.text,
            fonts.get(22, bold=True),
            text_color,
            center=rect.center,
        )


def draw_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: Color,
    *,
    center: tuple[int, int] | None = None,
    topleft: tuple[int, int] | None = None,
    shadow: bool = False,
) -> pygame.Rect:
    image = font.render(text, True, color)
    rect = image.get_rect()
    if center is not None:
        rect.center = center
    elif topleft is not None:
        rect.topleft = topleft
    if shadow:
        shadow_image = font.render(text, True, (2, 8, 24))
        surface.blit(shadow_image, rect.move(0, 3))
    surface.blit(image, rect)
    return rect


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    radius: int = 18,
    *,
    accent: Color = BORDER,
    fill: Color = PANEL,
) -> None:
    shadow = rect.move(0, 7).inflate(8, 8)
    pygame.draw.rect(surface, (2, 9, 28), shadow, border_radius=radius + 4)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, (31, 65, 119), rect, width=3, border_radius=radius)
    highlight = pygame.Rect(rect.left + 18, rect.top + 1, rect.width - 36, 2)
    pygame.draw.rect(surface, accent, highlight, border_radius=1)


def draw_arrow(
    surface: pygame.Surface,
    center: tuple[float, float],
    size: float,
    direction: Direction,
    color: Color | None = None,
    *,
    scale: float = 1.0,
) -> None:
    """Draw a crisp vector arrow with a small shadow and edge highlight."""

    arrow_color = color or DIRECTION_COLORS[direction]
    unit_points = (
        (-0.32, -0.10),
        (0.05, -0.10),
        (0.05, -0.25),
        (0.35, 0.00),
        (0.05, 0.25),
        (0.05, 0.10),
        (-0.32, 0.10),
    )

    def rotate(x: float, y: float) -> tuple[float, float]:
        if direction is Direction.RIGHT:
            return x, y
        if direction is Direction.DOWN:
            return -y, x
        if direction is Direction.LEFT:
            return -x, -y
        return y, -x

    cx, cy = center
    points: list[tuple[float, float]] = []
    for x, y in unit_points:
        rx, ry = rotate(x, y)
        points.append((cx + rx * size * scale, cy + ry * size * scale))

    shadow_points = [(x + 2, y + 4) for x, y in points]
    pygame.draw.polygon(surface, (4, 13, 35), shadow_points)
    pygame.draw.polygon(surface, arrow_color, points)
    pygame.draw.lines(surface, (211, 239, 255), True, points, width=2)


def draw_heart(
    surface: pygame.Surface,
    center: tuple[int, int],
    size: int,
    *,
    filled: bool,
) -> None:
    color = HEART_RED if filled else DISABLED
    cx, cy = center
    radius = max(3, int(size * 0.23))
    left = (cx - radius, cy - radius // 2)
    right = (cx + radius, cy - radius // 2)
    bottom = (cx, cy + int(size * 0.48))

    if filled:
        pygame.draw.circle(surface, color, left, radius)
        pygame.draw.circle(surface, color, right, radius)
        pygame.draw.polygon(
            surface,
            color,
            ((cx - radius * 2, cy), (cx + radius * 2, cy), bottom),
        )
        pygame.draw.circle(surface, (255, 177, 187), (cx - radius, cy - radius), 2)
    else:
        pygame.draw.circle(surface, color, left, radius, width=2)
        pygame.draw.circle(surface, color, right, radius, width=2)
        pygame.draw.lines(
            surface,
            color,
            False,
            ((cx - radius * 2, cy), bottom, (cx + radius * 2, cy)),
            width=2,
        )


def draw_star(
    surface: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    *,
    filled: bool,
) -> None:
    points: list[tuple[float, float]] = []
    for index in range(10):
        angle = -math.pi / 2 + index * math.pi / 5
        distance = radius if index % 2 == 0 else radius * 0.44
        points.append(
            (
                center[0] + math.cos(angle) * distance,
                center[1] + math.sin(angle) * distance,
            )
        )
    color = GOLD if filled else DISABLED
    pygame.draw.polygon(surface, color if filled else (24, 48, 88), points)
    pygame.draw.lines(surface, color, True, points, width=2)
