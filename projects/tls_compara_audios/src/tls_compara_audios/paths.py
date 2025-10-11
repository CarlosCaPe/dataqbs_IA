"""Path helpers for tls_compara_audios (src layout).

Includes a lightweight migration shim: if an old artifact root
`artifacts/telus_compara_audios` exists and the new one does not yet contain
data, it will be moved automatically to preserve history.
"""
from __future__ import annotations
from pathlib import Path
import shutil

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[2]
MONOREPO_ROOT = PROJECT_ROOT.parent.parent

ARTIFACTS_ROOT = MONOREPO_ROOT / "artifacts" / "tls_compara_audios"
OLD_ARTIFACTS_ROOT = MONOREPO_ROOT / "artifacts" / "telus_compara_audios"

OUTPUTS_DIR = ARTIFACTS_ROOT / "outputs"
LOGS_DIR = ARTIFACTS_ROOT / "logs"
USER_DATA_DIR = ARTIFACTS_ROOT / "user_data"

# Attempt automatic migration of legacy artifact directory.
if OLD_ARTIFACTS_ROOT.exists() and not ARTIFACTS_ROOT.exists():
    try:
        OLD_ARTIFACTS_ROOT.rename(ARTIFACTS_ROOT)
    except Exception:
        # Fallback: copy tree then leave old in place for manual cleanup.
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
