import json, pathlib, math
from pprint import pprint

try:
    import bf_numba_impl as bf
except Exception as e:
    print("import bf_numba_impl failed:", e)
    raise
p = pathlib.Path("artifacts/arbitraje/offline_snapshot_profitable.json")
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
        for i in range(len(cyc) - 1):
            a = cyc[i]
            b = cyc[i + 1]
            # find rate
            rate = None
            for k, (uu, vv, ww) in enumerate(zip(u_arr, v_arr, w_arr)):
                if uu == a and vv == b:
                    rate = math.exp(-ww)
            print("edge", nodes[a], "->", nodes[b], "rate", rate)
            prod *= rate if rate else 1.0
        print("cycle nodes indices:", cyc, "prod=", prod)
