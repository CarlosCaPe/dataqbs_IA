"""Centralized path utilities for email_collector.

All runtime artifacts live under the monorepo-level `artifacts/email_collector` tree.
Import these constants instead of hard-coding relative paths.
"""
from __future__ import annotations

from pathlib import Path

# projects/email_collector/src/email_collector/paths.py -> src/email_collector -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MONOREPO_ROOT = PROJECT_ROOT.parents[1]
ARTIFACTS_ROOT = MONOREPO_ROOT / "artifacts" / "email_collector"
OUTPUTS_DIR = ARTIFACTS_ROOT / "outputs"
LOGS_DIR = ARTIFACTS_ROOT / "logs"

# Ensure directories exist at runtime (lightweight)
for _p in (OUTPUTS_DIR, LOGS_DIR):
    _p.mkdir(parents=True, exist_ok=True)

__all__ = [
    "PROJECT_ROOT",
    "MONOREPO_ROOT",
    "ARTIFACTS_ROOT",
    "OUTPUTS_DIR",
    "LOGS_DIR",
]
