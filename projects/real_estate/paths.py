"""Path helpers for real_estate project.
This project not yet migrated to src/ layout; adjust once refactored.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
MONOREPO_ROOT = PROJECT_ROOT.parents[1]
ARTIFACTS_ROOT = MONOREPO_ROOT / "artifacts" / "real_estate"
DATA_DIR = ARTIFACTS_ROOT / "data"
IMAGES_DIR = ARTIFACTS_ROOT / "images"
SCREENSHOTS_DIR = ARTIFACTS_ROOT / "screenshots"
LOGS_DIR = ARTIFACTS_ROOT / "logs"

for _p in (DATA_DIR, IMAGES_DIR, SCREENSHOTS_DIR, LOGS_DIR):
    _p.mkdir(parents=True, exist_ok=True)

__all__ = [
    "PROJECT_ROOT",
    "MONOREPO_ROOT",
    "ARTIFACTS_ROOT",
    "DATA_DIR",
    "IMAGES_DIR",
    "SCREENSHOTS_DIR",
    "LOGS_DIR",
]
