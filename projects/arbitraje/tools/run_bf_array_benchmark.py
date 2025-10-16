import time, json
from pathlib import Path
from bf_numba_impl import build_arrays_from_payload, bellman_ford_array

BASE = Path(__file__).resolve().parents[1]
p = BASE / "artifacts" / "arbitraje" / "offline_snapshot_synth_large.json"
with open(p, "r", encoding="utf-8") as fh:
    data = json.load(fh)
first = next(iter(data.keys()))
payload = data[first]
nodes, u_arr, v_arr, w_arr = build_arrays_from_payload(payload)
print("nodes, edges=", len(nodes), len(u_arr))
# run a few iterations
iters = 3
start = time.time()
for i in range(iters):
    _ = bellman_ford_array(len(nodes), u_arr, v_arr, w_arr)
elapsed = time.time() - start
print("total", elapsed, "s", "per=", elapsed / iters)
