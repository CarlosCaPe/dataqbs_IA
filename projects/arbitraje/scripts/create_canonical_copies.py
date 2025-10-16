"""Create canonical copies of important logs, diagnostics and tests for CI/docs.

This script non-destructively copies files into `projects/arbitraje/canonical/`
and writes a `manifest.json` containing metadata (size, mtime, sha256).
CI will fail if the canonical test is missing to enforce stronger policy.
"""
from pathlib import Path
import shutil
import sys
import hashlib
import json
import time


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "canonical"
CANONICAL_LOGS = CANONICAL / "logs"
CANONICAL_TESTS = CANONICAL / "tests"
CANONICAL_OTHER = CANONICAL / "other"

for d in (CANONICAL, CANONICAL_LOGS, CANONICAL_TESTS, CANONICAL_OTHER):
    d.mkdir(parents=True, exist_ok=True)

def sha256_of_file(p: Path, block_size: int = 65536) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            h.update(block)
    return h.hexdigest()

copied = 0
manifest = {"generated_at": time.time(), "files": []}

# Copy known arbitraje artifact logs and diagnostics JSON
artifacts_dir = ROOT / "artifacts" / "arbitraje"
if artifacts_dir.exists():
    for p in sorted(artifacts_dir.glob("**/*.*")):
        # include common extensions
        if p.suffix.lower() in {".log", ".txt", ".json", ".csv"}:
            dest = CANONICAL_LOGS / p.name
            try:
                shutil.copy2(p, dest)
                copied += 1
                manifest["files"].append({
                    "src": str(p.relative_to(ROOT)),
                    "dest": str(dest.relative_to(ROOT)),
                    "size": dest.stat().st_size,
                    "mtime": dest.stat().st_mtime,
                    "sha256": sha256_of_file(dest),
                })
            except Exception as e:
                print(f"Failed to copy {p}: {e}")

# Copy additional useful outputs (outputs/ and logs/)
outputs_dir = ROOT / "artifacts" / "arbitraje" / "outputs"
if outputs_dir.exists():
    for p in sorted(outputs_dir.glob("**/*.*")):
        if p.is_file():
            dest = CANONICAL_OTHER / p.name
            try:
                shutil.copy2(p, dest)
                copied += 1
                manifest["files"].append({
                    "src": str(p.relative_to(ROOT)),
                    "dest": str(dest.relative_to(ROOT)),
                    "size": dest.stat().st_size,
                    "mtime": dest.stat().st_mtime,
                    "sha256": sha256_of_file(dest),
                })
            except Exception as e:
                print(f"Failed to copy output {p}: {e}")

# Copy the canonical connector test into canonical tests
src_test = ROOT / "tests" / "scripts" / "test_connector_fetch.py"
if src_test.exists():
    try:
        dest = CANONICAL_TESTS / "test_connector_fetch.py"
        shutil.copy2(src_test, dest)
        copied += 1
        manifest["files"].append({
            "src": str(src_test.relative_to(ROOT)),
            "dest": str(dest.relative_to(ROOT)),
            "size": dest.stat().st_size,
            "mtime": dest.stat().st_mtime,
            "sha256": sha256_of_file(dest),
        })
    except Exception as e:
        print(f"Failed to copy test file: {e}")

# If diagnostics JSON already exists, copy it too
diag = ROOT / "artifacts" / "arbitraje" / "fetch_diagnostics.json"
if diag.exists():
    try:
        dest = CANONICAL_LOGS / diag.name
        shutil.copy2(diag, dest)
        copied += 1
        manifest["files"].append({
            "src": str(diag.relative_to(ROOT)),
            "dest": str(dest.relative_to(ROOT)),
            "size": dest.stat().st_size,
            "mtime": dest.stat().st_mtime,
            "sha256": sha256_of_file(dest),
        })
    except Exception as e:
        print(f"Failed to copy diagnostics {diag}: {e}")

# Write manifest
manifest_path = CANONICAL / "manifest.json"
with manifest_path.open("w", encoding="utf-8") as mf:
    json.dump(manifest, mf, indent=2)

print(f"Created canonical copies under {CANONICAL}. Total copied: {copied}")

if copied == 0:
    print("ERROR: no files were copied. Ensure artifacts exist and test script is present.")
    sys.exit(2)
