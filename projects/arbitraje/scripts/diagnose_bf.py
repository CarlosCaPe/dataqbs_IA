import json, pathlib, sys
from pprint import pprint

try:
    from arbitraje import engine_techniques
except Exception as e:
    print("import error", e)
    sys.exit(1)

p = pathlib.Path("artifacts/arbitraje/offline_snapshot_profitable.json")
if not p.exists():
    print("snapshot not found:", p)
    sys.exit(1)

data = json.load(p.open("r", encoding="utf-8"))
for ex, payload in data.items():
    print("\n=== EXCHANGE:", ex)
    print("payload keys:", list(payload.keys()))
    tickers = payload.get("tickers")
    print("tickers count:", len(tickers) if tickers else 0)
    try:
        st = engine_techniques._tech_stat_triangles(ex, payload, {"techniques": {}})
        print("stat_tri results:", len(st))
        if st:
            pprint(st[:5])
    except Exception as e:
        print("stat_tri error", e)
    try:
        bf = engine_techniques._tech_bellman_ford(
            ex, payload, {"techniques": {"use_numba": False}}
        )
        print("bf results:", len(bf))
        if bf:
            pprint(bf[:5])
    except Exception as e:
        print("bf error", e)
