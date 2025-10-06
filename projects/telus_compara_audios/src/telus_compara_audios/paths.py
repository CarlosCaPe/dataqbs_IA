"""Path helpers for telus_compara_audios (src layout)."""
from __future__ import annotations
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[2]
MONOREPO_ROOT = PROJECT_ROOT.parent.parent
ARTIFACTS_ROOT = MONOREPO_ROOT / "artifacts" / "telus_compara_audios"
OUTPUTS_DIR = ARTIFACTS_ROOT / "outputs"
LOGS_DIR = ARTIFACTS_ROOT / "logs"
USER_DATA_DIR = ARTIFACTS_ROOT / "user_data"

for _p in (OUTPUTS_DIR, LOGS_DIR, USER_DATA_DIR):
    _p.mkdir(parents=True, exist_ok=True)

__all__ = [
    "PACKAGE_ROOT",
    "PROJECT_ROOT",
    "MONOREPO_ROOT",
    "ARTIFACTS_ROOT",
    "OUTPUTS_DIR",
    "LOGS_DIR",
    "USER_DATA_DIR",
]
