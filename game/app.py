"""Pygame application, rendering, interaction, and screen flow."""

from __future__ import annotations

import os
import sys
import math
import secrets
from dataclasses import dataclass

# SDL must know about Windows high-DPI mode before Pygame creates the window.
if sys.platform == "win32":
    os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

import pygame

from game.audio import AudioManager
from game.animation import AnimationKind, ArrowAnimation
from game.effects import ParticleSystem
from game.extra_levels import EXTRA_LEVELS
from game.generator import DIFFICULTIES, generate_level
from game.hints import choose_hint
from game.levels import LEVELS
from game.models import (
    MAX_MISTAKES,
    ArrowState,
    ClickResult,
    Direction,
    GameSession,
    ScreenState,
)
from game.progress import ProgressData, load_progress, save_progress, update_record
from game.resources import default_progress_path, resource_path
from game.rules import (
    attempt_arrow_click,
    finalize_collision,
    finalize_flight,
    find_arrow_at,
    screen_to_cell,
    start_level,
)
from game.scoring import calculate_score, calculate_stars, format_time
from game.ui import (
    BACKGROUND,
    BLUE,
    BORDER,
    CYAN,
    DIRECTION_COLORS,
    GOLD,
    GREEN,
    GRID_DARK,
    GRID_LIGHT,
    MUTED,
    PANEL_LIGHT,
    RED,
    TEXT,
    Button,
    FontBook,
    draw_arrow,
    draw_heart,
    draw_panel,
    draw_star,
    draw_text,
)


WINDOW_SIZE = (1200, 800)
BOARD_PANEL = pygame.Rect(48, 128, 664, 576)
SIDE_PANEL = pygame.Rect(744, 128, 408, 576)
ALL_FIXED_LEVELS = LEVELS + EXTRA_LEVELS


@dataclass
class ClickRipple:
    position: tuple[int, int]
    color: tuple[int, int, int] = CYAN
    elapsed: float = 0.0
    duration: float = 0.38

    @property
    def done(self) -> bool:
        return self.elapsed >= self.duration

    def update(self, dt: float) -> None:
        self.elapsed = min(self.duration, self.elapsed + dt)

    def draw(self, surface: pygame.Surface) -> None:
        progress = self.elapsed / self.duration
        radius = int(8 + 30 * progress)
        alpha = int(190 * (1.0 - progress))
        canvas = pygame.Surface((radius * 2 + 6, radius * 2 + 6), pygame.SRCALPHA)
        pygame.draw.circle(
            canvas,
            (*self.color, alpha),
            (radius + 3, radius + 3),
            radius,
            width=2,
        )
        surface.blit(
            canvas,
            (self.position[0] - radius - 3, self.position[1] - radius - 3),
        )


class GameApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode(WINDOW_SIZE, pygame.DOUBLEBUF)
        pygame.display.set_caption("箭途 - 一箭又一箭")
        self.clock = pygame.time.Clock()
        self.fonts = FontBook()
        self.background = self._load_background(
            "start_background.png"
        ) or self._load_background("ui_background.png")
        self.progress_path = (
            None
            if os.environ.get("SDL_VIDEODRIVER") == "dummy"
            else default_progress_path()
        )
        self.progress = (
            load_progress(self.progress_path)
            if self.progress_path is not None
            else ProgressData()
        )
        self.audio = AudioManager(self.progress.sound_enabled)
        self.particles = ParticleSystem()
        self.session = GameSession()
        self.playlist = LEVELS
        self.random_seed: int | None = None
        self.random_difficulty: str | None = None
        self.animation: ArrowAnimation | None = None
        self.ripples: list[ClickRipple] = []
        self.message_timer = 0.0
        self.hint_timer = 0.0
        self.help_open = False
        self.window_active = True
        self.running = True
        self.buttons = self._create_buttons()

    def _load_background(self, filename: str) -> pygame.Surface | None:
        path = resource_path("assets", filename)
        try:
            source = pygame.image.load(path).convert()
        except (FileNotFoundError, pygame.error):
            return None
        return pygame.transform.smoothscale(source, WINDOW_SIZE)

    @staticmethod
    def _create_buttons() -> dict[str, Button]:
        return {
            "start": Button(pygame.Rect(438, 438, 324, 52), "开始游戏"),
            "level_select": Button(
                pygame.Rect(438, 502, 324, 48), "关卡选择", primary=False
            ),
            "start_help": Button(
                pygame.Rect(438, 562, 324, 48), "玩法说明", primary=False
            ),
            "exit": Button(
                pygame.Rect(438, 622, 324, 48), "退出游戏", primary=False
            ),
            "sound": Button(
                pygame.Rect(1008, 42, 144, 42), "音效：开", primary=False
            ),
            "hint": Button(pygame.Rect(796, 468, 304, 46), "提示  H"),
            "restart": Button(
                pygame.Rect(796, 532, 94, 48), "重开", primary=False
            ),
            "game_help": Button(
                pygame.Rect(901, 532, 94, 48), "说明", primary=False
            ),
            "home": Button(
                pygame.Rect(1006, 532, 94, 48), "保存", primary=False
            ),
            "result_primary": Button(
                pygame.Rect(440, 530, 320, 50), "下一关"
            ),
            "result_select": Button(
                pygame.Rect(440, 592, 154, 48), "关卡选择", primary=False
            ),
            "result_home": Button(
                pygame.Rect(606, 592, 154, 48), "返回首页", primary=False
            ),
            "help_close": Button(pygame.Rect(440, 604, 320, 52), "我知道了"),
            "select_home": Button(
                pygame.Rect(48, 724, 184, 48), "返回首页", primary=False
            ),
            "random_casual": Button(
                pygame.Rect(520, 724, 170, 48), "休闲随机", primary=False
            ),
            "random_standard": Button(
                pygame.Rect(704, 724, 170, 48), "标准随机", primary=False
            ),
            "random_hard": Button(
                pygame.Rect(888, 724, 170, 48), "困难随机", primary=False
            ),
        }

    @property
    def level(self):
        return self.playlist[self.session.current_level_index]

    @property
    def level_key(self) -> str:
        if self.level.pack == "random":
            return f"random:{self.random_difficulty}:{self.random_seed}"
        return f"{self.level.pack}:{self.level.id}"

    @property
    def score(self) -> int:
        return calculate_score(
            self.session.successful_moves,
            self.session.remaining_mistakes,
            self.session.elapsed_seconds,
            self.level.par_seconds,
            self.session.hints_used,
            cleared=self.session.screen_state in (
                ScreenState.LEVEL_CLEAR,
                ScreenState.ALL_CLEAR,
            ),
        )

    @property
    def stars(self) -> int:
        return calculate_stars(
            self.session.remaining_mistakes,
            self.session.elapsed_seconds,
            self.level.par_seconds,
            self.session.hints_used,
            cleared=self.session.screen_state in (
                ScreenState.LEVEL_CLEAR,
                ScreenState.ALL_CLEAR,
            ),
        )

    def start_game(
        self,
        level_index: int = 0,
        *,
        playlist=None,
        random_seed: int | None = None,
        random_difficulty: str | None = None,
    ) -> None:
        if playlist is not None:
            self.playlist = playlist
            self.random_seed = random_seed
            self.random_difficulty = random_difficulty
        start_level(self.session, level_index, self.playlist[level_index])
        self.animation = None
        self.ripples.clear()
        self.particles.clear()
        self.message_timer = 0.0
        self.hint_timer = 0.0
        self.help_open = False

    def _save_progress(self) -> None:
        if self.progress_path is not None:
            save_progress(self.progress_path, self.progress)

    def _fixed_level(self, pack: str, level_id: int):
        return next(
            (
                level
                for level in ALL_FIXED_LEVELS
                if level.pack == pack and level.id == level_id
            ),
            None,
        )

    def _is_unlocked(self, level) -> bool:
        if level.pack == "classic":
            return True
        if level.id == 4:
            return self.progress.records.get(
                "classic:3", None
            ) is not None and self.progress.records["classic:3"].cleared
        previous = self.progress.records.get(f"challenge:{level.id - 1}")
        return previous is not None and previous.cleared

    def _start_fixed_level(self, level) -> None:
        playlist = LEVELS if level.pack == "classic" else EXTRA_LEVELS
        level_index = next(
            index for index, item in enumerate(playlist) if item.id == level.id
        )
        self.start_game(level_index, playlist=playlist)

    def _start_random_level(self, difficulty: str, seed: int | None = None) -> None:
        actual_seed = seed if seed is not None else secrets.randbelow(1_000_000_000)
        level = generate_level(
            actual_seed,
            difficulty,
            level_id=100,
        )
        self.start_game(
            0,
            playlist=(level,),
            random_seed=actual_seed,
            random_difficulty=difficulty,
        )

    def _save_resume(self) -> None:
        if self.session.screen_state is not ScreenState.PLAYING:
            return
        self.progress.resume = {
            "pack": self.level.pack,
            "level_id": self.level.id,
            "random_seed": self.random_seed,
            "random_difficulty": self.random_difficulty,
            "remaining_arrow_ids": [arrow.id for arrow in self.session.arrows],
            "remaining_mistakes": self.session.remaining_mistakes,
            "elapsed_ms": int(self.session.elapsed_seconds * 1000),
            "successful_moves": self.session.successful_moves,
            "collision_count": self.session.collision_count,
            "hints_used": self.session.hints_used,
        }
        self._save_progress()

    def _resume_game(self) -> bool:
        data = self.progress.resume
        if not isinstance(data, dict):
            return False
        try:
            pack = str(data["pack"])
            if pack == "random":
                difficulty = str(data["random_difficulty"])
                seed = int(data["random_seed"])
                if difficulty not in DIFFICULTIES:
                    return False
                self._start_random_level(difficulty, seed)
            else:
                level = self._fixed_level(pack, int(data["level_id"]))
                if level is None:
                    return False
                self._start_fixed_level(level)

            remaining_ids = data.get("remaining_arrow_ids")
            valid_ids = {arrow.id for arrow in self.session.arrows}
            if (
                not isinstance(remaining_ids, list)
                or not remaining_ids
                or not set(remaining_ids) <= valid_ids
            ):
                return False
            remaining = set(remaining_ids)
            self.session.arrows = [
                arrow for arrow in self.session.arrows if arrow.id in remaining
            ]
            self.session.remaining_mistakes = min(
                MAX_MISTAKES,
                max(0, int(data.get("remaining_mistakes", MAX_MISTAKES))),
            )
            self.session.elapsed_seconds = max(
                0.0, int(data.get("elapsed_ms", 0)) / 1000.0
            )
            self.session.successful_moves = max(
                0, int(data.get("successful_moves", 0))
            )
            self.session.collision_count = max(
                0, int(data.get("collision_count", 0))
            )
            self.session.hints_used = max(0, int(data.get("hints_used", 0)))
            self.session.message = "已恢复上次游戏"
            self.message_timer = 1.2
            return True
        except (KeyError, TypeError, ValueError, RuntimeError):
            return False

    def _start_or_resume(self) -> None:
        if self._resume_game():
            return
        if self.progress.resume is not None:
            self.progress.resume = None
            self._save_progress()
        self.start_game(0, playlist=LEVELS)

    def _finish_level(self) -> None:
        self.progress.resume = None
        if self.level.pack != "random":
            update_record(
                self.progress,
                self.level_key,
                score=self.score,
                elapsed_seconds=self.session.elapsed_seconds,
                stars=self.stars,
            )
        self._save_progress()
        self.audio.play("clear")

    def _toggle_sound(self) -> None:
        self.progress.sound_enabled = not self.progress.sound_enabled
        self.audio.set_enabled(self.progress.sound_enabled)
        self._save_progress()

    def run(self, max_frames: int | None = None) -> None:
        frames = 0
        try:
            while self.running:
                dt = min(self.clock.tick(60) / 1000.0, 0.05)
                self._handle_events()
                self.update(dt)
                self.draw()
                pygame.display.flip()
                frames += 1
                if max_frames is not None and frames >= max_frames:
                    self.running = False
        finally:
            pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                self.window_active = False
            elif event.type == pygame.WINDOWFOCUSGAINED:
                self.window_active = True
            elif event.type == pygame.KEYDOWN:
                self._handle_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _handle_key(self, key: int) -> None:
        if self.help_open:
            if key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.help_open = False
            return

        if key == pygame.K_ESCAPE:
            if self.session.screen_state is ScreenState.START:
                self.running = False
            elif self.session.screen_state is ScreenState.LEVEL_SELECT:
                self._go_home()
            else:
                self._save_resume()
                self._go_home()
        elif key == pygame.K_RETURN:
            if self.session.screen_state is ScreenState.START:
                self._start_or_resume()
            elif self.session.screen_state in (
                ScreenState.LEVEL_CLEAR,
                ScreenState.FAILED,
                ScreenState.ALL_CLEAR,
            ):
                self._activate_result_primary()
        elif (
            self.session.screen_state is ScreenState.PLAYING
            and self.animation is None
        ):
            if key == pygame.K_h:
                self._show_hint()
            elif key == pygame.K_r:
                self.start_game(self.session.current_level_index)

    def _handle_click(self, position: tuple[int, int]) -> None:
        self.ripples.append(ClickRipple(position))
        if self.help_open:
            if self.buttons["help_close"].contains(position):
                self.help_open = False
            return

        state = self.session.screen_state
        if state is ScreenState.START:
            if self.buttons["start"].contains(position):
                self.audio.play("click")
                self._start_or_resume()
            elif self.buttons["level_select"].contains(position):
                self.audio.play("click")
                self.session.screen_state = ScreenState.LEVEL_SELECT
            elif self.buttons["start_help"].contains(position):
                self.audio.play("click")
                self.help_open = True
            elif self.buttons["sound"].contains(position):
                self._toggle_sound()
            elif self.buttons["exit"].contains(position):
                self.running = False
            return

        if state is ScreenState.LEVEL_SELECT:
            self._handle_level_select_click(position)
            return

        if state in (
            ScreenState.LEVEL_CLEAR,
            ScreenState.FAILED,
            ScreenState.ALL_CLEAR,
        ):
            if self.buttons["result_primary"].contains(position):
                self.audio.play("click")
                self._activate_result_primary()
            elif self.buttons["result_select"].contains(position):
                self.audio.play("click")
                self.session = GameSession(screen_state=ScreenState.LEVEL_SELECT)
            elif self.buttons["result_home"].contains(position):
                self.audio.play("click")
                self._go_home()
            return

        if self.buttons["hint"].contains(position):
            self.audio.play("click")
            self._show_hint()
            return
        if self.buttons["restart"].contains(position):
            self.audio.play("click")
            self.start_game(self.session.current_level_index)
            return
        if self.buttons["game_help"].contains(position):
            self.audio.play("click")
            self.help_open = True
            return
        if self.buttons["home"].contains(position):
            self.audio.play("click")
            self._save_resume()
            self._go_home()
            return

        if self.animation is not None:
            return

        board_rect, cell_size = self._board_layout()
        cell = screen_to_cell(
            *position,
            (board_rect.left, board_rect.top, board_rect.width, board_rect.height),
            cell_size,
        )
        if cell is None:
            return
        arrow = find_arrow_at(self.session.arrows, *cell)
        if arrow is None:
            return

        result = attempt_arrow_click(self.session, self.level, arrow.id)
        if result is ClickResult.FLY:
            self.session.hint_arrow_id = None
            self.hint_timer = 0.0
            self.ripples[-1].color = GREEN
            self.particles.emit(
                position,
                DIRECTION_COLORS[arrow.direction],
                count=8,
            )
            self.audio.play("fly")
            self.animation = ArrowAnimation(
                arrow.id,
                arrow.direction,
                AnimationKind.FLY,
                duration=0.4,
                distance=620.0,
            )
            self.message_timer = 0.8
        elif result is ClickResult.COLLIDE:
            self.ripples[-1].color = RED
            self.particles.emit(position, RED, count=10)
            self.audio.play("collide")
            self.animation = ArrowAnimation(
                arrow.id,
                arrow.direction,
                AnimationKind.COLLIDE,
                duration=0.28,
                distance=11.0,
            )
            self.message_timer = 0.8

    def _handle_level_select_click(self, position: tuple[int, int]) -> None:
        if self.buttons["select_home"].contains(position):
            self.audio.play("click")
            self._go_home()
            return
        if self.buttons["sound"].contains(position):
            self._toggle_sound()
            return
        for difficulty in DIFFICULTIES:
            if self.buttons[f"random_{difficulty}"].contains(position):
                self.audio.play("click")
                self._start_random_level(difficulty)
                return
        for level, rect in self._level_card_rects():
            if rect.collidepoint(position) and self._is_unlocked(level):
                self.audio.play("click")
                self._start_fixed_level(level)
                return

    def _show_hint(self) -> None:
        if (
            self.session.screen_state is not ScreenState.PLAYING
            or self.animation is not None
        ):
            return
        hint = choose_hint(self.session.arrows, self.level.rows, self.level.cols)
        if hint is None:
            self.session.message = "当前布局没有可飞出的箭头"
            self.message_timer = 1.2
            return
        if self.session.hint_arrow_id != hint or self.hint_timer <= 0:
            self.session.hints_used += 1
        self.session.hint_arrow_id = hint
        self.hint_timer = 2.5
        self.session.message = "提示：金色光圈中的箭头可以飞出"
        self.message_timer = 2.5

    def _activate_result_primary(self) -> None:
        state = self.session.screen_state
        if state is ScreenState.LEVEL_CLEAR:
            self.start_game(self.session.current_level_index + 1)
        elif state is ScreenState.FAILED:
            self.start_game(self.session.current_level_index)
        elif state is ScreenState.ALL_CLEAR:
            if self.level.pack == "random":
                self._start_random_level(
                    self.random_difficulty or "standard",
                    self.random_seed,
                )
            else:
                self.start_game(0)

    def _go_home(self) -> None:
        self.session = GameSession()
        self.playlist = LEVELS
        self.random_seed = None
        self.random_difficulty = None
        self.animation = None
        self.ripples.clear()
        self.particles.clear()
        self.message_timer = 0.0
        self.hint_timer = 0.0
        self.help_open = False

    def update(self, dt: float) -> None:
        if (
            self.session.screen_state is ScreenState.PLAYING
            and not self.help_open
            and self.window_active
        ):
            self.session.elapsed_seconds += dt
        for ripple in self.ripples:
            ripple.update(dt)
        self.ripples = [ripple for ripple in self.ripples if not ripple.done]
        self.particles.update(dt)
        self.message_timer = max(0.0, self.message_timer - dt)
        self.hint_timer = max(0.0, self.hint_timer - dt)
        if self.hint_timer == 0:
            self.session.hint_arrow_id = None
        if self.animation is None:
            if (
                self.session.screen_state is ScreenState.PLAYING
                and self.message_timer == 0
            ):
                self.session.message = "请选择一支箭头"
            return

        self.animation.advance(dt)
        if not self.animation.done:
            return

        completed = self.animation
        self.animation = None
        if completed.kind is AnimationKind.FLY:
            previous_state = self.session.screen_state
            finalize_flight(
                self.session,
                completed.arrow_id,
                is_last_level=self.session.current_level_index == len(self.playlist) - 1,
            )
            if (
                previous_state is ScreenState.PLAYING
                and self.session.screen_state
                in (ScreenState.LEVEL_CLEAR, ScreenState.ALL_CLEAR)
            ):
                self._finish_level()
        else:
            finalize_collision(self.session, completed.arrow_id)
            if self.session.screen_state is ScreenState.FAILED:
                self.progress.resume = None
                self._save_progress()
                self.audio.play("fail")

    def _board_layout(self) -> tuple[pygame.Rect, int]:
        max_dimension = max(self.level.rows, self.level.cols)
        cell_size = min(84, 504 // max_dimension)
        width = self.level.cols * cell_size
        height = self.level.rows * cell_size
        rect = pygame.Rect(0, 0, width, height)
        rect.center = BOARD_PANEL.center
        return rect, cell_size

    def draw(self) -> None:
        if self.background is None:
            self.screen.fill(BACKGROUND)
            for x in range(0, WINDOW_SIZE[0], 80):
                pygame.draw.line(self.screen, (10, 30, 68), (x, 0), (x, 800))
            for y in range(0, WINDOW_SIZE[1], 80):
                pygame.draw.line(self.screen, (10, 30, 68), (0, y), (1200, y))
        else:
            self.screen.blit(self.background, (0, 0))
        if self.session.screen_state is ScreenState.START:
            self._draw_start()
        elif self.session.screen_state is ScreenState.LEVEL_SELECT:
            self._draw_level_select()
        else:
            self._draw_game()
            self.particles.draw(self.screen)
            if self.session.screen_state is not ScreenState.PLAYING:
                self._draw_result()
        if self.help_open:
            self._draw_help()
        for ripple in self.ripples:
            ripple.draw(self.screen)

    def _draw_start(self) -> None:
        draw_text(
            self.screen,
            "ARROW LOGIC PUZZLE",
            self.fonts.get(16, bold=True),
            CYAN,
            center=(600, 55),
        )
        draw_text(
            self.screen,
            "箭 途",
            self.fonts.get(68, bold=True),
            TEXT,
            center=(600, 112),
            shadow=True,
        )
        pygame.draw.line(self.screen, CYAN, (548, 154), (652, 154), 3)
        draw_text(
            self.screen,
            "观察方向，按正确顺序让箭头全部离场",
            self.fonts.get(22),
            MUTED,
            center=(600, 181),
        )

        demo = pygame.Rect(306, 212, 588, 212)
        draw_panel(self.screen, demo, accent=CYAN, fill=(12, 30, 66))
        draw_text(
            self.screen,
            "前方有箭头会受阻；路径为空即可飞出",
            self.fonts.get(21, bold=True),
            TEXT,
            center=(600, 252),
        )
        cell = 68
        start_x, start_y = 464, 298
        for col in range(4):
            rect = pygame.Rect(start_x + col * cell, start_y, cell - 4, cell - 4)
            pygame.draw.rect(
                self.screen,
                GRID_LIGHT if col % 2 == 0 else GRID_DARK,
                rect,
                border_radius=10,
            )
            pygame.draw.rect(self.screen, BORDER, rect, width=2, border_radius=10)
        draw_arrow(
            self.screen,
            (start_x + 32, start_y + 32),
            58,
            Direction.RIGHT,
        )
        draw_arrow(
            self.screen,
            (start_x + 3 * cell + 32, start_y + 32),
            58,
            Direction.UP,
            GREEN,
        )
        pygame.draw.line(
            self.screen,
            (54, 103, 179),
            (start_x + 62, start_y + 32),
            (start_x + 3 * cell - 2, start_y + 32),
            2,
        )

        self.buttons["start"].text = (
            "继续游戏" if self.progress.resume is not None else "开始游戏"
        )
        self.buttons["sound"].text = (
            "音效：开" if self.progress.sound_enabled else "音效：关"
        )
        mouse = pygame.mouse.get_pos()
        for key in ("start", "level_select", "start_help", "exit", "sound"):
            self.buttons[key].draw(self.screen, self.fonts, mouse)
        draw_text(
            self.screen,
            "鼠标左键操作  ·  每关只有 3 次失误机会",
            self.fonts.get(18),
            MUTED,
            center=(600, 742),
        )

    def _level_card_rects(self):
        cards = []
        for index, level in enumerate(ALL_FIXED_LEVELS):
            row, col = divmod(index, 3)
            cards.append(
                (
                    level,
                    pygame.Rect(88 + col * 352, 176 + row * 214, 320, 184),
                )
            )
        return cards

    def _draw_level_select(self) -> None:
        draw_text(
            self.screen,
            "选择关卡",
            self.fonts.get(48, bold=True),
            TEXT,
            center=(600, 70),
            shadow=True,
        )
        draw_text(
            self.screen,
            "经典关卡随时可玩，完成第 3 关后依次解锁挑战关卡",
            self.fonts.get(19),
            MUTED,
            center=(600, 118),
        )
        mouse = pygame.mouse.get_pos()
        for level, rect in self._level_card_rects():
            unlocked = self._is_unlocked(level)
            hovered = unlocked and rect.collidepoint(mouse)
            fill = (18, 45, 87) if hovered else (12, 29, 62)
            if not unlocked:
                fill = (15, 24, 44)
            draw_panel(
                self.screen,
                rect,
                radius=18,
                accent=CYAN if hovered else BORDER,
                fill=fill,
            )
            draw_text(
                self.screen,
                f"第 {level.id} 关",
                self.fonts.get(18, bold=True),
                CYAN if unlocked else MUTED,
                topleft=(rect.left + 20, rect.top + 18),
            )
            draw_text(
                self.screen,
                level.name if unlocked else "尚未解锁",
                self.fonts.get(27, bold=True),
                TEXT if unlocked else MUTED,
                center=(rect.centerx, rect.top + 72),
            )
            draw_text(
                self.screen,
                f"{level.rows}×{level.cols}  ·  {len(level.arrows)} 支箭  ·  {level.difficulty}",
                self.fonts.get(16),
                MUTED,
                center=(rect.centerx, rect.top + 112),
            )
            record = self.progress.records.get(f"{level.pack}:{level.id}")
            stars = record.best_stars if record is not None else 0
            for index in range(3):
                draw_star(
                    self.screen,
                    (rect.centerx - 34 + index * 34, rect.top + 148),
                    13,
                    filled=index < stars,
                )

        draw_text(
            self.screen,
            "随机挑战",
            self.fonts.get(21, bold=True),
            TEXT,
            center=(384, 748),
        )
        self.buttons["sound"].text = (
            "音效：开" if self.progress.sound_enabled else "音效：关"
        )
        for key in (
            "select_home",
            "random_casual",
            "random_standard",
            "random_hard",
            "sound",
        ):
            self.buttons[key].draw(self.screen, self.fonts, mouse)

    def _draw_game(self) -> None:
        draw_text(
            self.screen,
            "箭途",
            self.fonts.get(34, bold=True),
            TEXT,
            topleft=(48, 42),
            shadow=True,
        )
        pygame.draw.line(self.screen, CYAN, (49, 84), (120, 84), 3)
        draw_text(
            self.screen,
            (
                f"随机挑战 · 种子 {self.random_seed}"
                if self.level.pack == "random"
                else f"第 {self.level.id} 关 · {self.level.difficulty}"
            ),
            self.fonts.get(26, bold=True),
            TEXT,
            center=(600, 62),
        )
        draw_text(
            self.screen,
            "失误机会",
            self.fonts.get(19),
            MUTED,
            topleft=(929, 48),
        )
        for index in range(MAX_MISTAKES):
            draw_heart(
                self.screen,
                (1065 + index * 34, 62),
                24,
                filled=index < self.session.remaining_mistakes,
            )

        draw_panel(self.screen, BOARD_PANEL, accent=CYAN)
        draw_panel(self.screen, SIDE_PANEL, accent=BLUE)
        board_rect, cell_size = self._board_layout()
        self._draw_board(board_rect, cell_size)
        self._draw_side_panel()

        toast_rect = pygame.Rect(48, 724, 1104, 52)
        pygame.draw.rect(self.screen, (10, 28, 62), toast_rect, border_radius=13)
        pygame.draw.rect(self.screen, (36, 81, 143), toast_rect, 2, border_radius=13)
        message_color = RED if "阻挡" in self.session.message else GREEN
        if self.session.message == "请选择一支箭头":
            message_color = MUTED
        draw_text(
            self.screen,
            self.session.message,
            self.fonts.get(20, bold=self.message_timer > 0),
            message_color,
            center=toast_rect.center,
        )

    def _draw_board(self, board_rect: pygame.Rect, cell_size: int) -> None:
        mouse = pygame.mouse.get_pos()
        hover_cell = screen_to_cell(
            *mouse,
            (board_rect.left, board_rect.top, board_rect.width, board_rect.height),
            cell_size,
        )
        board_frame = board_rect.inflate(18, 18)
        pygame.draw.rect(self.screen, (7, 20, 48), board_frame, border_radius=16)
        pygame.draw.rect(self.screen, (42, 101, 181), board_frame, 2, border_radius=16)
        for row in range(self.level.rows):
            for col in range(self.level.cols):
                rect = pygame.Rect(
                    board_rect.left + col * cell_size,
                    board_rect.top + row * cell_size,
                    cell_size,
                    cell_size,
                ).inflate(-4, -4)
                fill = GRID_LIGHT if (row + col) % 2 == 0 else GRID_DARK
                pygame.draw.rect(self.screen, fill, rect, border_radius=7)
                border = CYAN if hover_cell == (row, col) else BORDER
                width = 2 if hover_cell == (row, col) else 1
                pygame.draw.rect(self.screen, border, rect, width=width, border_radius=7)

        for arrow in self.session.arrows:
            center_x = board_rect.left + (arrow.col + 0.5) * cell_size
            center_y = board_rect.top + (arrow.row + 0.5) * cell_size
            offset_x = offset_y = 0.0
            color = DIRECTION_COLORS[arrow.direction]
            if arrow.id == self.session.hint_arrow_id and self.hint_timer > 0:
                pulse = 0.5 + 0.5 * math.sin(self.hint_timer * math.tau * 2.0)
                radius = int(cell_size * (0.38 + pulse * 0.06))
                pygame.draw.circle(
                    self.screen,
                    GOLD,
                    (int(center_x), int(center_y)),
                    radius,
                    width=4,
                )
            if self.animation is not None and self.animation.arrow_id == arrow.id:
                offset_x, offset_y = self.animation.offset()
                if self.animation.kind is AnimationKind.COLLIDE:
                    color = RED
                    pygame.draw.circle(
                        self.screen,
                        (119, 34, 61),
                        (int(center_x), int(center_y)),
                        int(cell_size * 0.38),
                        width=3,
                    )
                elif offset_x or offset_y:
                    end_x = center_x + offset_x
                    end_y = center_y + offset_y
                    travelled = (offset_x**2 + offset_y**2) ** 0.5
                    trail_length = min(cell_size * 0.38, travelled)
                    start_x = end_x - offset_x / travelled * trail_length
                    start_y = end_y - offset_y / travelled * trail_length
                    pygame.draw.line(
                        self.screen,
                        color,
                        (int(start_x), int(start_y)),
                        (int(end_x), int(end_y)),
                        width=max(3, cell_size // 12),
                    )

            hovered = (
                hover_cell == (arrow.row, arrow.col)
                and arrow.state is ArrowState.IDLE
                and self.animation is None
            )
            if hovered:
                pygame.draw.circle(
                    self.screen,
                    (29, 74, 135),
                    (int(center_x), int(center_y)),
                    int(cell_size * 0.38),
                )
                pygame.draw.circle(
                    self.screen,
                    CYAN,
                    (int(center_x), int(center_y)),
                    int(cell_size * 0.38),
                    width=2,
                )
            draw_arrow(
                self.screen,
                (center_x + offset_x, center_y + offset_y),
                cell_size * 0.88,
                arrow.direction,
                color,
                scale=1.04 if hovered else 1.0,
            )

    def _draw_side_panel(self) -> None:
        draw_text(
            self.screen,
            self.level.name,
            self.fonts.get(30, bold=True),
            TEXT,
            center=(948, 174),
            shadow=True,
        )
        segment_width = min(42, 252 // max(1, len(self.playlist)) - 8)
        start_x = 948 - (segment_width + 8) * len(self.playlist) // 2
        for index in range(len(self.playlist)):
            segment = pygame.Rect(start_x + index * (segment_width + 8), 205, segment_width, 5)
            pygame.draw.rect(
                self.screen,
                CYAN if index <= self.session.current_level_index else (42, 67, 106),
                segment,
                border_radius=3,
            )

        stats = (
            ("棋盘", f"{self.level.rows} × {self.level.cols}"),
            ("剩余箭头", str(len(self.session.arrows))),
            ("失误机会", f"{self.session.remaining_mistakes} / {MAX_MISTAKES}"),
            ("用时 / 分数", f"{format_time(self.session.elapsed_seconds)}  /  {self.score}"),
        )
        for index, (label, value) in enumerate(stats):
            rect = pygame.Rect(796, 226 + index * 54, 304, 42)
            pygame.draw.rect(self.screen, PANEL_LIGHT, rect, border_radius=10)
            pygame.draw.rect(self.screen, (38, 77, 133), rect, 1, border_radius=10)
            draw_text(
                self.screen,
                label,
                self.fonts.get(17),
                MUTED,
                topleft=(812, rect.top + 10),
            )
            value_image = self.fonts.get(20, bold=True).render(value, True, TEXT)
            self.screen.blit(
                value_image,
                value_image.get_rect(midright=(1082, rect.centery)),
            )

        pygame.draw.line(self.screen, (39, 78, 135), (804, 448), (1092, 448), 2)
        draw_text(
            self.screen,
            f"提示已使用 {self.session.hints_used} 次",
            self.fonts.get(18, bold=True),
            TEXT,
            center=(948, 608),
        )

        mouse = pygame.mouse.get_pos()
        self.buttons["hint"].enabled = self.animation is None
        for key in ("hint", "restart", "game_help", "home"):
            self.buttons[key].draw(self.screen, self.fonts, mouse)

    def _draw_result(self) -> None:
        overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
        overlay.fill((2, 7, 22, 205))
        self.screen.blit(overlay, (0, 0))
        card = pygame.Rect(330, 72, 540, 648)

        state = self.session.screen_state
        if state is ScreenState.LEVEL_CLEAR:
            title = f"第 {self.level.id} 关通过"
            subtitle = f"还剩 {self.session.remaining_mistakes} 次失误机会"
            primary = "下一关"
            color = GREEN
            symbol = "check"
        elif state is ScreenState.ALL_CLEAR:
            title = "随机挑战完成" if self.level.pack == "random" else "全部关卡完成"
            subtitle = (
                f"种子 {self.random_seed}"
                if self.level.pack == "random"
                else "你已经解开了这一组箭头联锁"
            )
            primary = "同种子重玩" if self.level.pack == "random" else "再玩一次"
            color = GREEN
            symbol = "check"
        else:
            title = "挑战失败"
            subtitle = "3 次失误机会已用完"
            primary = "重新挑战"
            color = RED
            symbol = "cross"

        draw_panel(self.screen, card, radius=24, accent=color, fill=(12, 28, 60))
        pygame.draw.circle(self.screen, (17, 42, 78), (600, 145), 42)
        pygame.draw.circle(self.screen, color, (600, 145), 42, width=4)
        if symbol == "check":
            pygame.draw.lines(
                self.screen,
                color,
                False,
                ((582, 145), (596, 159), (622, 130)),
                width=7,
            )
        else:
            pygame.draw.line(self.screen, color, (584, 129), (616, 161), 7)
            pygame.draw.line(self.screen, color, (616, 129), (584, 161), 7)
        self.buttons["result_primary"].text = primary
        draw_text(
            self.screen,
            title,
            self.fonts.get(40, bold=True),
            TEXT,
            center=(600, 222),
            shadow=True,
        )
        draw_text(
            self.screen,
            subtitle,
            self.fonts.get(22),
            MUTED,
            center=(600, 268),
        )
        for index in range(3):
            draw_star(
                self.screen,
                (556 + index * 44, 318),
                18,
                filled=index < self.stars,
            )
        stats = (
            ("本关得分", str(self.score)),
            ("用时", format_time(self.session.elapsed_seconds)),
            ("提示次数", str(self.session.hints_used)),
        )
        for index, (label, value) in enumerate(stats):
            y = 366 + index * 42
            draw_text(
                self.screen,
                label,
                self.fonts.get(18),
                MUTED,
                topleft=(440, y),
            )
            image = self.fonts.get(20, bold=True).render(value, True, TEXT)
            self.screen.blit(image, image.get_rect(midright=(760, y + 11)))

        record = self.progress.records.get(self.level_key)
        if record is not None and self.level.pack != "random":
            best_time = (
                format_time(record.best_time_ms / 1000)
                if record.best_time_ms is not None
                else "--:--"
            )
            record_text = f"最佳纪录  {record.best_score} 分  ·  {best_time}"
        elif self.level.pack == "random":
            record_text = "随机挑战不计入固定关卡纪录"
        else:
            record_text = "完成关卡后将保存最佳纪录"
        draw_text(
            self.screen,
            record_text,
            self.fonts.get(17),
            MUTED,
            center=(600, 500),
        )
        mouse = pygame.mouse.get_pos()
        self.buttons["result_primary"].draw(self.screen, self.fonts, mouse)
        self.buttons["result_select"].draw(self.screen, self.fonts, mouse)
        self.buttons["result_home"].draw(self.screen, self.fonts, mouse)

    def _draw_help(self) -> None:
        overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
        overlay.fill((2, 7, 22, 210))
        self.screen.blit(overlay, (0, 0))
        card = pygame.Rect(300, 108, 600, 576)
        draw_panel(self.screen, card, radius=22, accent=CYAN, fill=(12, 28, 60))
        draw_text(
            self.screen,
            "玩法说明",
            self.fonts.get(38, bold=True),
            TEXT,
            center=(600, 166),
            shadow=True,
        )
        pygame.draw.line(self.screen, CYAN, (548, 196), (652, 196), 3)
        lines = (
            "1. 用鼠标左键选择一支箭头。",
            "2. 箭头正前方没有其他箭头时，它会飞出棋盘。",
            "3. 前方被阻挡时，箭头会碰撞返回并扣 1 次失误。",
            "4. 每关只有 3 次失误机会，耗尽后需要重试。",
            "5. 清空当前棋盘即可进入下一关。",
            "6. 点击空白格不会扣除失误机会。",
        )
        for index, line in enumerate(lines):
            draw_text(
                self.screen,
                line,
                self.fonts.get(20),
                TEXT,
                topleft=(356, 226 + index * 48),
            )
        draw_text(
            self.screen,
            "提示：只看箭头朝向的一行或一列。",
            self.fonts.get(20, bold=True),
            GREEN,
            center=(600, 548),
        )
        self.buttons["help_close"].draw(
            self.screen, self.fonts, pygame.mouse.get_pos()
        )
