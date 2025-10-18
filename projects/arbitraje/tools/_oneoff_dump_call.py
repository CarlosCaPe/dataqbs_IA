import json
from pathlib import Path
from arbitraje.engine_techniques import _tech_bellman_ford
SNAP = Path(__file__).resolve().parents[1] / 'artifacts' / 'arbitraje' / 'offline_snapshot_profitable.json'
raw = json.loads(SNAP.read_text(encoding='utf-8'))
ex = 'binance' if 'binance' in raw else next(iter(raw.keys()))
ex_data = raw[ex]
markets = ex_data.get('markets') or {}

# build tickers and tokens
tokens = set()
for sym, m in markets.items():
    b = m.get('base')
    q = m.get('quote')
    if b:
        tokens.add(str(b))
    if q:
        tokens.add(str(q))

payload = {
    'ex_id': ex,
    'ts': 'oneoff-dump',
    'tokens': list(tokens),
    'tickers': ex_data.get('tickers') or {},
    'fee': 0.10,
    'min_quote_vol': 0.0,
    'min_net': 0.0,
}
print('Calling _tech_bellman_ford with dump_graph True')
res = _tech_bellman_ford('oneoff-dump', payload, {'techniques': {'dump_graph': True, 'use_numba': False}})
print('Done. results:', len(res))
