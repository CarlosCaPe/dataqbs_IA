"""Path helpers for tls_compara_imagenes (src layout).

Includes migration shim from legacy artifacts/telus_compara_imagenes -> artifacts/tls_compara_imagenes
"""
from __future__ import annotations
from pathlib import Path
import shutil

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[2]
MONOREPO_ROOT = PROJECT_ROOT.parent.parent

ARTIFACTS_ROOT = MONOREPO_ROOT / "artifacts" / "tls_compara_imagenes"
OLD_ARTIFACTS_ROOT = MONOREPO_ROOT / "artifacts" / "telus_compara_imagenes"

OUTPUTS_DIR = ARTIFACTS_ROOT / "outputs"
LOGS_DIR = ARTIFACTS_ROOT / "logs"
USER_DATA_DIR = ARTIFACTS_ROOT / "user_data"

if OLD_ARTIFACTS_ROOT.exists() and not ARTIFACTS_ROOT.exists():
    try:
        OLD_ARTIFACTS_ROOT.rename(ARTIFACTS_ROOT)
    except Exception:
        try:
            shutil.copytree(OLD_ARTIFACTS_ROOT, ARTIFACTS_ROOT, dirs_exist_ok=True)
        except Exception:
            pass

for _p in (OUTPUTS_DIR, LOGS_DIR, USER_DATA_DIR):
    try:
        _p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

__all__ = [
    "PACKAGE_ROOT",
    "PROJECT_ROOT",
    "MONOREPO_ROOT",
    "ARTIFACTS_ROOT",
    "OUTPUTS_DIR",
    "LOGS_DIR",
    "USER_DATA_DIR",
]
