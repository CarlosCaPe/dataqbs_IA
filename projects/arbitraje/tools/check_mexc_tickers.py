import ccxt
import json
import sys

try:
    ex = ccxt.mexc({'enableRateLimit': True})
    ex.load_markets()
    try:
        tickers = ex.fetch_tickers()
    except Exception:
        # Some CCXT builds have fetch_tickers issues; fall back to iterating symbols
        tickers = {}
        for s in list(ex.symbols)[:500]:
            try:
                t = ex.fetch_ticker(s)
                tickers[s] = t
            except Exception:
                continue

    valid = {}
    for s, t in (tickers or {}).items():
        try:
            b = t.get('bid') if isinstance(t, dict) else None
            a = t.get('ask') if isinstance(t, dict) else None
            l = t.get('last') if isinstance(t, dict) else None
            if (b is not None and float(b) > 0) or (a is not None and float(a) > 0) or (l is not None and float(l) > 0):
                valid[s] = { 'bid': b, 'ask': a, 'last': l }
        except Exception:
            continue

    out = {
        'total_tickers_fetched': len(tickers or {}),
        'valid_tickers': len(valid),
        'samples': dict(list(valid.items())[:20])
    }
    print(json.dumps(out, indent=2))
except Exception as e:
    print(json.dumps({'error': str(e)}))
    sys.exit(1)
