"""Path helpers for telus_compara_audios.
Centralizes artifact locations under artifacts/telus_compara_audios
"""
from __future__ import annotations
from pathlib import Path

# projects/telus_compara_audios/telus_compara_audios/paths.py -> package root
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
MONOREPO_ROOT = PROJECT_ROOT.parents[1]
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
