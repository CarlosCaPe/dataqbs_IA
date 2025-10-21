import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


LINE_RE = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2}[^-]+)- INFO - (?P<body>.*)$")
KV_RE = re.compile(r"(\w+)=([^|]+)")


def parse_kv(body: str) -> dict:
    out = {}
    for m in KV_RE.finditer(body):
        k = m.group(1).strip()
        v = m.group(2).strip().strip()
        out[k] = v
    return out


def analyze_log(path: Path) -> None:
    if not path.exists():
        print(f"File not found: {path}")
        return

    status_counter = Counter()
    exchange_counter = Counter()
    error_counter = Counter()
    symbol_counter = Counter()
    mirror_events = Counter()
    tiny_start_counter = Counter()  # starts with tiny balance_free per asset

    # Heuristics for tiny thresholds (base units)
    tiny_thresholds = {
        ("binance", "ZEC"): 0.001,  # min amount precision
        ("bitget", "COAI"): 0.01,
    }

    # track last start per exchange to associate tiny starts
    last_start = []  # list of dicts for recent "start" lines

    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            m = LINE_RE.match(raw)
            if not m:
                continue
            body = m.group("body")

            if " - INFO - start |" in raw:
                kv = parse_kv(body)
                ex = kv.get("exchange", "").strip().lower()
                p = kv.get("path", "")
                asset = p.split("->")[0].strip().upper() if "->" in p else ""
                bf = kv.get("balance_free", "")
                try:
                    balance_free = float(bf.split()[0]) if bf else None
                except Exception:
                    balance_free = None
                last_start.append({
                    "exchange": ex,
                    "asset": asset,
                    "balance_free": balance_free,
                })
                continue

            if "mirror_placed" in body:
                mirror_events["placed"] += 1
                # try to attribute symbol
                kv = parse_kv(body)
                sym = kv.get("symbol") or ""
                if sym:
                    symbol_counter[sym.strip()] += 1
                continue

            if "mirror_reemit" in body:
                mirror_events["reemit"] += 1
                continue

            if "mirror_forced_close" in body:
                mirror_events["forced_close"] += 1
                continue

            if " - INFO - result |" in raw:
                kv = parse_kv(body)
                status = (kv.get("status") or "").strip()
                status_counter[status] += 1
                ex = (kv.get("exchange") or "").strip().lower()
                if ex:
                    exchange_counter[ex] += 1
                # error bucket
                err = (kv.get("error") or "").strip()
                if err:
                    # normalize error messages a bit
                    key = err
                    if "minimum amount precision" in err:
                        key = "min amount precision"
                    error_counter[key] += 1
                # symbol from mirror field
                mir = kv.get("mirror:") or kv.get("mirror") or ""
                if mir:
                    # e.g., "ZEC/USDT buy limit=..."
                    sym = mir.split()[0].strip()
                    if sym:
                        symbol_counter[sym] += 1

                # attribute tiny starts to failures quickly following
                if last_start:
                    start = last_start[-1]
                    ex0 = start.get("exchange")
                    asset0 = start.get("asset")
                    bf0 = start.get("balance_free")
                    th = tiny_thresholds.get((ex0, asset0))
                    if th is not None and bf0 is not None and bf0 < th:
                        tiny_start_counter[(ex0, asset0)] += 1
                continue

    print("=== Status counts ===")
    for k, v in status_counter.most_common():
        print(f"{k:16s} {v}")

    print("\n=== Exchanges seen (in results) ===")
    for k, v in exchange_counter.most_common():
        print(f"{k:16s} {v}")

    print("\n=== Mirror events ===")
    for k, v in mirror_events.most_common():
        print(f"{k:16s} {v}")

    print("\n=== Symbols (from mirror/result) ===")
    for k, v in symbol_counter.most_common(10):
        print(f"{k:12s} {v}")

    print("\n=== Common errors ===")
    for k, v in error_counter.most_common(10):
        print(f"{k:40s} {v}")

    print("\n=== Tiny starts (by exchange, asset) ===")
    for (ex, asset), v in tiny_start_counter.most_common():
        print(f"{ex}/{asset}: {v}")


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        # default path seen in this repo structure
        path = Path("c:/Users/Lenovo/Guillermo/guillermo/artifacts/arbitraje/logs/swapper.log")
    analyze_log(path)


if __name__ == "__main__":
    main()
