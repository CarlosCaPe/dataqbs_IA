"""Path helpers for telus_compara_imagenes.
Central artifact root: artifacts/telus_compara_imagenes
"""
from __future__ import annotations
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
MONOREPO_ROOT = PROJECT_ROOT.parents[1]
ARTIFACTS_ROOT = MONOREPO_ROOT / "artifacts" / "telus_compara_imagenes"
USER_DATA_DIR = ARTIFACTS_ROOT / "user_data"

USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

__all__ = [
    "PACKAGE_ROOT",
    "PROJECT_ROOT",
    "MONOREPO_ROOT",
    "ARTIFACTS_ROOT",
    "USER_DATA_DIR",
]
