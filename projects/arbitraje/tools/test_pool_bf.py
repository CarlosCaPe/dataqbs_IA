import time
import json
from concurrent.futures import ProcessPoolExecutor

# Run from projects/arbitraje
from arbitraje import engine_techniques

if __name__ == '__main__':
    pw = {
        "ex_id": "test_ex",
        "ts": time.time(),
        "tokens": ["A", "B"],
        "tickers": {"A/B": {"bid": 1.0, "ask": 1.0, "last": 1.0, "quoteVolume": 100.0}},
        "fee": 0.1,
    }
    print("Submitting to ProcessPoolExecutor...")
    with ProcessPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(engine_techniques._tech_bellman_ford, "test_snapshot", pw, {})
        try:
            res = fut.result(timeout=20)
            print("Worker result:", res)
        except Exception as e:
            print("Worker exception:", e)
    # Try to print artifacts files
    try:
        with open('artifacts/arbitraje/diag_paths.jsonl', 'r', encoding='utf-8') as f:
            print('--- diag_paths.jsonl ---')
            for line in f:
                print(line.strip())
    except Exception as e:
        print('diag_paths.jsonl missing or unreadable:', e)
    try:
        with open('artifacts/arbitraje/diagnostics.log', 'r', encoding='utf-8') as f:
            print('--- diagnostics.log ---')
            for line in f:
                print(line.strip())
    except Exception as e:
        print('diagnostics.log missing or unreadable:', e)
