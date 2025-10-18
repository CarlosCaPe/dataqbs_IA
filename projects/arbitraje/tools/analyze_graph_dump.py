#!/usr/bin/env python3
import json
from pathlib import Path
from math import prod

p = Path(__file__).resolve().parents[1] / 'src' / 'artifacts' / 'arbitraje' / 'graph_debug_1760661188.jsonl'
if not p.exists():
    print('dump not found', p)
    raise SystemExit(1)
line = p.read_text(encoding='utf-8').strip()
if not line:
    print('empty')
    raise SystemExit(1)
obj = json.loads(line)
nodes = obj.get('nodes', [])
rate_map_raw = obj.get('rate_map', {})
# convert keys like 'A->B' to dict
rate = {}
for k,v in rate_map_raw.items():
    a,b = k.split('->')
    rate.setdefault(a, {})[b] = float(v)

# find all 3-cycles
cycles = []
for a in nodes:
    for b in nodes:
        if b==a: continue
        if b not in rate.get(a, {}): continue
        for c in nodes:
            if c==a or c==b: continue
            if c not in rate.get(b, {}): continue
            if a not in rate.get(c, {}): continue
            r1 = rate[a][b]; r2 = rate[b][c]; r3 = rate[c][a]
            prodv = r1 * r2 * r3
            cycles.append((prodv, [a,b,c], (r1,r2,r3)))

cycles_sorted = sorted(cycles, key=lambda x: x[0], reverse=True)
print('found', len(cycles_sorted), '3-cycles; top 10:')
for prodv, path, rates in cycles_sorted[:10]:
    net_pct = (prodv - 1.0) * 100.0
    net_bps = (prodv - 1.0) * 10000.0
    print(f"path: {'->'.join(path)} prod={prodv:.6g} net_pct={net_pct:.6f}% net_bps={net_bps:.3f} rates={rates}")

# show top positive
pos = [c for c in cycles_sorted if c[0] > 1.0]
print('\npositive cycles count', len(pos))
for prodv, path, rates in pos[:10]:
    print('POS', {'path': '->'.join(path), 'prod': prodv, 'net_pct': (prodv-1)*100})
