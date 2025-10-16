"""Copy known logs into artifacts/arbitraje/logs for easy collection.
This is non-destructive: it copies files, doesn't move them.
"""
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_LOG_DIR = PROJECT_ROOT / "artifacts" / "arbitraje" / "logs"
ARTIFACTS_LOG_DIR.mkdir(parents=True, exist_ok=True)

# heuristics: gather common logs from known locations
candidates = []
# logs produced by source modules
for p in (PROJECT_ROOT / "src").rglob("*.py"):
    # look for references to LOGS_DIR or log filenames
    pass

# Common paths we know
known_files = [
    PROJECT_ROOT / "artifacts" / "arbitraje" / "arbitraje_ccxt.log",
    PROJECT_ROOT / "artifacts" / "arbitraje" / "techniques_telemetry.log",
    PROJECT_ROOT / "artifacts" / "arbitraje" / "techniques_telemetry_relax.log",
    PROJECT_ROOT / "artifacts" / "arbitraje" / "radar_dryrun_1000.log",
    PROJECT_ROOT / "artifacts" / "arbitraje" / "radar_dryrun_2500.log",
]

copied = 0
for f in known_files:
    if f.exists():
        dest = ARTIFACTS_LOG_DIR / f.name
        try:
            shutil.copy2(f, dest)
            copied += 1
        except Exception as e:
            print(f"Failed to copy {f}: {e}")

print(f"Copied {copied} known logs to {ARTIFACTS_LOG_DIR}")
