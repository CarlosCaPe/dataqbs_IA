from __future__ import annotations

import argparse
import time
from arbitraje.swapper import Swapper, SwapHop, SwapPlan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, required=True)
    ap.add_argument("--exchange", type=str, required=True)
    ap.add_argument("--path", type=str, required=True)
    ap.add_argument("--anchor", type=str, default="USDT")
    ap.add_argument("--amount", type=float, default=1.0)
    args = ap.parse_args()

    sw = Swapper(config_path=args.config)
    nodes = args.path.split("->")
    hops = [SwapHop(base=p, quote=q) for p, q in zip(nodes, nodes[1:])]
    plan = SwapPlan(exchange=args.exchange, hops=hops, anchor=args.anchor, amount=args.amount)

    t0 = time.perf_counter()
    res = sw.run(plan)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    print({
        "elapsed_ms": elapsed_ms,
        "ok": res.ok,
        "status": res.status,
        "delta": res.delta,
        "amount_in": res.amount_in,
        "amount_out": res.amount_out,
    })


if __name__ == "__main__":
    main()
