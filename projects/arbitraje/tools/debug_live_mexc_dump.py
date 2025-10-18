#!/usr/bin/env python3
import json
import time
from pathlib import Path
import ccxt

from arbitraje.engine_techniques import scan_arbitrage, _tech_bellman_ford

ART_DIR = Path(__file__).resolve().parents[1] / 'artifacts' / 'arbitraje'
ART_DIR.mkdir(parents=True, exist_ok=True)

ex_id = 'mexc'
print('Loading exchange', ex_id)
ex = getattr(ccxt, ex_id)({'enableRateLimit': True})
try:
    markets = ex.load_markets()
except Exception as e:
    print('load_markets failed', e)
    markets = {}
try:
    tickers = ex.fetch_tickers()
except Exception as e:
    print('fetch_tickers failed', e)
    tickers = {}

# compose tokens list
tokens = set()
for sym, m in (markets or {}).items():
    try:
        base = str(m.get('base') or '').upper()
        quote = str(m.get('quote') or '').upper()
        if base:
            tokens.add(base)
        if quote:
            tokens.add(quote)
    except Exception:
        continue

payload = {
    'ex_id': ex_id,
    'ts': time.strftime('%Y-%m-%dT%H:%M:%S'),
    # Limit tokens to top-N by quoteVolume to keep the graph small and ensure dump is produced
    'tokens': [],
    'tickers': {},
    'fee': 0.10,
    'min_quote_vol': 0.0,
    # override for diagnostic run: include negative nets so we capture loss-making cycles
    'min_net': -100.0,
    'min_net_per_hop': -100.0,
}

cfg = {
    'techniques': {
        'enabled': ['bellman_ford'],
        'inline': ['bellman_ford'],
        'dump_graph': True,
        'telemetry_file': str(ART_DIR / 'techniques_telemetry_live_test.log'),
    }
}

# Ensure BF-level diagnostic overrides are present so the engine picks them
cfg['bf'] = {
    'min_net': float(payload['min_net']),
    'min_net_per_hop': float(payload.get('min_net_per_hop', -100.0)),
    'log_all_cycles': True,
}

# Select top tokens by aggregated quoteVolume from fetched tickers
qvol_map = {}
for sym, t in (tickers or {}).items():
    try:
        # get quote volume from a few possible fields
        qv = t.get('quoteVolume') or t.get('quoteVolume24h') or t.get('volumeQuote') or 0.0
        qv_f = float(qv or 0.0)
    except Exception:
        qv_f = 0.0
    if '/' in sym:
        a, b = sym.split('/')
        qvol_map[a] = qvol_map.get(a, 0.0) + qv_f
        qvol_map[b] = qvol_map.get(b, 0.0) + qv_f

# pick top-N tokens
TOP_N = 30
sorted_tokens = sorted(list(qvol_map.keys()), key=lambda x: qvol_map.get(x, 0.0), reverse=True)
sel_tokens = sorted_tokens[:TOP_N]
sel_tokens = [t for t in sel_tokens if t]

# Build a filtered tickers dict keeping only pairs where both sides are in sel_tokens
filtered_tickers = {}
for sym, t in (tickers or {}).items():
    try:
        if '/' not in sym:
            continue
        a, b = sym.split('/')
        if a in sel_tokens and b in sel_tokens:
            filtered_tickers[sym] = t
    except Exception:
        continue

payload['tokens'] = sel_tokens
payload['tickers'] = filtered_tickers

print('Selected tokens:', len(payload['tokens']), 'Selected tickers:', len(payload['tickers']))
print('Calling _tech_bellman_ford directly (inline)...')
res = _tech_bellman_ford(payload['ts'], payload, cfg)
print('bf results count:', len(res))

files = sorted(ART_DIR.glob('graph_debug_*.jsonl'), key=lambda p: p.stat().st_mtime)
if files:
    latest = files[-1]
    print('Wrote graph debug:', latest)
    print(latest.read_text(encoding='utf-8').splitlines()[-1])
else:
    # engine may write to src/artifacts instead of project-level artifacts; check both
    alt_dir = Path(__file__).resolve().parents[1] / 'src' / 'artifacts' / 'arbitraje'
    alt_files = sorted(alt_dir.glob('graph_debug_*.jsonl'), key=lambda p: p.stat().st_mtime) if alt_dir.exists() else []
    if alt_files:
        latest = alt_files[-1]
        print('Wrote graph debug (alt):', latest)
        print(latest.read_text(encoding='utf-8').splitlines()[-1])
    else:
        print('No graph debug files found in either artifacts location')

print('Telemetry tail:')
try:
    print((ART_DIR / 'techniques_telemetry_live_test.log').read_text(encoding='utf-8').splitlines()[-5:])
except Exception:
    pass

# tail candidate and diagnostics logs from engine src artifacts path too
try:
    src_art = Path(__file__).resolve().parents[1] / 'src' / 'artifacts' / 'arbitraje'
    if src_art.exists():
        cand = src_art / 'candidate_cycles.log'
        diag = src_art / 'diagnostics.log'
        if cand.exists():
            print('\nLast candidate entries:')
            print('\n'.join(cand.read_text(encoding='utf-8').splitlines()[-5:]))
        if diag.exists():
            print('\nLast diagnostics entries:')
            print('\n'.join(diag.read_text(encoding='utf-8').splitlines()[-10:]))
except Exception:
    pass
