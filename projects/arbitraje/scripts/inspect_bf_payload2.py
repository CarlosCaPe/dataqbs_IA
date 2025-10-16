import json, pathlib, math, importlib.util, sys
from pprint import pprint

# load bf_numba_impl from tools path
bf_path = pathlib.Path(__file__).resolve().parents[1] / "tools" / "bf_numba_impl.py"
if not bf_path.exists():
    print("bf_numba_impl.py not found at", bf_path)
    sys.exit(1)
spec = importlib.util.spec_from_file_location("bf_numba_impl", str(bf_path))
bf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bf)

p = (
    pathlib.Path(__file__).resolve().parents[1]
    / "artifacts"
    / "arbitraje"
    / "offline_snapshot_profitable.json"
)
if not p.exists():
    print("snapshot not found:", p)
    sys.exit(1)

data = json.load(p.open("r", encoding="utf-8"))
for ex, payload in data.items():
    print("\n=== EXCHANGE:", ex)
    nodes, u_arr, v_arr, w_arr = bf.build_arrays_from_payload(payload)
    print("nodes:", nodes)
    print("len edges:", len(u_arr))
    for i, (u, v, w) in enumerate(zip(u_arr, v_arr, w_arr)):
        print(i, nodes[u], "->", nodes[v], "w=", w, "rate=", math.exp(-w))
    cycles = bf.bellman_ford_array(len(nodes), u_arr, v_arr, w_arr)
    print("cycles found:", len(cycles))
    for cyc in cycles:
        prod = 1.0
        # ensure closed
        if cyc[0] != cyc[-1]:
            closed = cyc + [cyc[0]]
        else:
            closed = cyc
        for i in range(len(closed) - 1):
            a = closed[i]
            b = closed[i + 1]
            rate = None
            for k, (uu, vv, ww) in enumerate(zip(u_arr, v_arr, w_arr)):
                if uu == a and vv == b:
                    rate = math.exp(-ww)
                    break
            print("edge", nodes[a], "->", nodes[b], "rate", rate)
            prod *= rate if rate else 1.0
        print("cycle nodes indices:", cyc, "prod=", prod)
