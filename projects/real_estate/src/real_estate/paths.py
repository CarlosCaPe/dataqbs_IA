"""Path helpers for real_estate project (src layout)."""
from __future__ import annotations

from pathlib import Path

# Directory structure:
# projects/real_estate/
#   src/real_estate/paths.py  (this file)
#   config.json
#   artifacts stored in ../../../artifacts/real_estate

PACKAGE_DIR = Path(__file__).resolve().parent
# project root is two levels up from PACKAGE_DIR (.. / .. / real_estate)
PROJECT_ROOT = PACKAGE_DIR.parents[2]
MONOREPO_ROOT = PROJECT_ROOT.parent.parent
ARTIFACTS_ROOT = MONOREPO_ROOT / "artifacts" / "real_estate"
DATA_DIR = ARTIFACTS_ROOT / "data"
IMAGES_DIR = ARTIFACTS_ROOT / "images"
SCREENSHOTS_DIR = ARTIFACTS_ROOT / "screenshots"
LOGS_DIR = ARTIFACTS_ROOT / "logs"

for _p in (DATA_DIR, IMAGES_DIR, SCREENSHOTS_DIR, LOGS_DIR):
    _p.mkdir(parents=True, exist_ok=True)

__all__ = [
    "PACKAGE_DIR",
    "PROJECT_ROOT",
    "MONOREPO_ROOT",
    "ARTIFACTS_ROOT",
    "DATA_DIR",
    "IMAGES_DIR",
    "SCREENSHOTS_DIR",
    "LOGS_DIR",
]
