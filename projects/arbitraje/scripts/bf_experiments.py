import json, pathlib, math
from itertools import product

p = (
    pathlib.Path(__file__).resolve().parents[1]
    / "artifacts"
    / "arbitraje"
    / "offline_snapshot_profitable.json"
)
if not p.exists():
    print("snapshot missing", p)
    raise SystemExit(1)

data = json.load(open(p, "r", encoding="utf-8"))

modes = ["bidask", "last", "mid"]
fee_options = [True, False]

results = []
for ex, payload in data.items():
    print("\n=== EXCHANGE", ex)
    tickers = payload.get("tickers") or {}

    # build helper to get rate for a->b under different modes
    def rate_ab(a, b, mode):
        sym = f"{a}/{b}"
        t = tickers.get(sym) or {}
        bid = t.get("bid")
        ask = t.get("ask")
        last = t.get("last")
        try:
            if mode == "bidask":
                # prefer bid for a->b, else last
                if bid is not None:
                    return float(bid)
                if last is not None:
                    return float(last)
                return None
            elif mode == "last":
                if last is not None:
                    return float(last)
                if bid is not None:
                    return float(bid)
                if ask is not None:
                    return float(1.0 / float(ask))
                return None
            elif mode == "mid":
                if bid is not None and ask is not None:
                    return (float(bid) + float(ask)) / 2.0
                if last is not None:
                    return float(last)
                return None
        except Exception:
            return None

    # get token set
    nodes = set()
    for sym in tickers.keys():
        if "/" in sym:
            a, b = sym.split("/")
            nodes.add(a)
            nodes.add(b)
    nodes = list(nodes)
    if len(nodes) < 2:
        print("not enough nodes")
        continue
    # enumerate all 3-cycles for simplicity
    nodes_list = nodes
    triplets = []
    for a in nodes_list:
        for b in nodes_list:
            for c in nodes_list:
                if a == b or b == c or c == a:
                    continue
                triplets.append((a, b, c))
    for mode, fee_apply in product(modes, fee_options):
        found_any = False
        best = None
        for a, b, c in triplets:
            r_ab = rate_ab(a, b, mode)
            r_bc = rate_ab(b, c, mode)
            r_ca = rate_ab(c, a, mode)
            if None in (r_ab, r_bc, r_ca):
                continue
            prod = r_ab * r_bc * r_ca
            if fee_apply:
                # apply fee 0.1% per hop from prod
                prod = prod * (1.0 - 0.001) ** 3
            net_pct = (prod - 1.0) * 100.0
            if best is None or prod > best[0]:
                best = (prod, net_pct, (a, b, c))
            if prod > 1.0:
                found_any = True
        print(f"mode={mode} fee_apply={fee_apply} best_prod={best}")
        results.append((ex, mode, fee_apply, best))

print("\nSummary:")
for r in results:
    print(r)
