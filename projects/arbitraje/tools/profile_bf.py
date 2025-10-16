"""Profile bellman_ford on an offline snapshot and print top hotspots.

Usage: python profile_bf.py [--iters N] [--snapshot path]

Saves cProfile output to profile_bf.prof and prints top callers.
"""

import argparse
import cProfile
import pstats
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "artifacts" / "arbitraje" / "offline_snapshot_profitable.json"

parser = argparse.ArgumentParser()
parser.add_argument("--iters", type=int, default=20)
parser.add_argument("--snapshot", type=str, default=str(SNAP))
args = parser.parse_args()

# Import the worker
import importlib.util
import sys

# Load the engine_techniques module directly by file path to avoid importing
# package-level dependencies (ccxt etc.) that aren't required for BF profiling.
ROOT_SRC = Path(__file__).resolve().parents[1] / "src"
mod_path = ROOT_SRC / "arbitraje" / "engine_techniques.py"
if not mod_path.exists():
    print("engine_techniques not found at", mod_path)
    raise SystemExit(2)
spec = importlib.util.spec_from_file_location("engine_techniques", str(mod_path))
engine_mod = importlib.util.module_from_spec(spec)
sys.modules["engine_techniques"] = engine_mod
spec.loader.exec_module(engine_mod)
# access the private function
bf = getattr(engine_mod, "_tech_bellman_ford")

# load snapshot
snap_path = Path(args.snapshot)
if not snap_path.exists():
    print("snapshot not found:", snap_path)
    raise SystemExit(2)
with open(snap_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

# pick first exchange payload as representative
first_ex = next(iter(data.keys()))
payload = data[first_ex]
# add minimal required keys
payload.setdefault("ex_id", first_ex)
payload.setdefault("tokens", ["A", "B", "C"])
payload.setdefault("fee", 0.1)

# Run cProfile across iterations
prof_file = Path("profile_bf.prof")
pr = cProfile.Profile()
pr.enable()
for i in range(args.iters):
    bf("test_snap", payload, {})
pr.disable()
pr.dump_stats(str(prof_file))

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats("cumtime")
ps.print_stats(40)
print(s.getvalue())

print("wrote:", prof_file)
print("Done")
