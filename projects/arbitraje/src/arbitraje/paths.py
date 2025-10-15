"""Path helpers for arbitraje (src layout) with centralized artifacts.

Creates artifacts/arbitraje/{outputs,logs} and supports future legacy migrations if needed.
"""
from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
MONOREPO_ROOT = PROJECT_ROOT.parent.parent

ARTIFACTS_ROOT = MONOREPO_ROOT / "artifacts" / "arbitraje"
OUTPUTS_DIR = ARTIFACTS_ROOT / "outputs"
LOGS_DIR = ARTIFACTS_ROOT / "logs"
SWAPS_LOG_DIR = LOGS_DIR / "swaps"

for _p in (OUTPUTS_DIR, LOGS_DIR, SWAPS_LOG_DIR):
    _p.mkdir(parents=True, exist_ok=True)

__all__ = [
    "PACKAGE_ROOT",
    "PROJECT_ROOT",
    "MONOREPO_ROOT",
    "ARTIFACTS_ROOT",
    "OUTPUTS_DIR",
    "LOGS_DIR",
    "SWAPS_LOG_DIR",
]
