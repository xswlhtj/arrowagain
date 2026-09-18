"""Resource and writable-data paths for source and packaged builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    base = Path(bundled_root) if bundled_root else Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def default_progress_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / ".arrow_escape"
    if local_app_data:
        base /= "ArrowEscape"
    return base / "progress.json"
