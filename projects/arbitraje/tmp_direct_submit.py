import json
import time
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from arbitraje.engine_techniques import _TECHS


def make_synthetic_tickers():
    tickers = {}
    pairs = ["A/USDT", "B/USDT", "C/USDT", "A/B", "B/C", "C/A"]
    for p in pairs:
        tickers[p] = {"bid": 1.0, "ask": 1.0, "last": 1.0, "quoteVolume": 1000}
    tickers["A/B"]["bid"] = 1.02
    tickers["B/C"]["bid"] = 1.02
    tickers["C/A"]["bid"] = 1.02
    return tickers


def run():
    tickers = make_synthetic_tickers()
    payload = {
        "ex_id": "testex",
        "quote": "USDT",
        "tokens": ["A", "B", "C"],
        "tickers": tickers,
        "fee": 0.10,
        "min_quote_vol": 0.0,
        "min_net": 0.0,
        "ts": "tst",
    }

    func = _TECHS.get("bellman_ford")
    if func is None:
        print("bellman_ford not found in _TECHS")
        return

    payload_str = json.dumps({
        "ex_id": payload.get("ex_id"),
        "ts": payload.get("ts"),
        "tokens": payload.get("tokens"),
        "tickers": payload.get("tickers"),
        "fee": float(payload.get("fee") or 0.0),
    })

    with ProcessPoolExecutor(max_workers=1) as p:
        f = p.submit(func, "snap-test-dir", payload_str, {})
        print("submitted future repr:", repr(f))
        done, pending = wait({f}, timeout=5.0, return_when=FIRST_COMPLETED)
        print("done set:", done)
        for fut in done:
            try:
                print("fut.done()", fut.done())
                print("fut.cancelled()", fut.cancelled())
                try:
                    exc = fut.exception(timeout=0)
                except Exception as e:
                    exc = str(e)
                print("fut.exception:", exc)
                try:
                    res = fut.result()
                    print("res type/len:", type(res), len(res) if res else 0)
                    try:
                        print(json.dumps(res[:3], indent=2))
                    except Exception:
                        print(res)
                except Exception as e:
                    print("result() raised:", e)
            except Exception as e:
                print("error processing future:", e)


if __name__ == '__main__':
    run()
