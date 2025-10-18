#!/usr/bin/env python3
import json
from pathlib import Path

# look in engine src artifacts first (where graph_debug was written)
base = Path(__file__).resolve().parents[1] / 'src' / 'artifacts' / 'arbitraje'
if not base.exists():
    base = Path(__file__).resolve().parents[1] / 'artifacts' / 'arbitraje'

files = sorted(base.glob('graph_debug_*.jsonl'), key=lambda p: p.stat().st_mtime)
if not files:
    print('No graph debug files found in', base)
    raise SystemExit(1)

p = files[-1]
print('Using graph dump:', p)
text = p.read_text(encoding='utf-8').strip().splitlines()[-1]
obj = json.loads(text)
nodes = obj.get('nodes', [])
rate_map = obj.get('rate_map', {})
# convert rate_map keys like 'A->B' to dict
edges = {}
for k, v in rate_map.items():
    if '->' in k:
        a, b = k.split('->', 1)
        edges.setdefault(a, {})[b] = float(v)

# find all distinct 3-cycles (a->b->c->a)
cycles = []
for a in nodes:
    for b in edges.get(a, {}).keys():
        for c in edges.get(b, {}).keys():
            if a in edges.get(c, {}):
                # canonical ordering to avoid duplicates: use tuple starting from smallest token
                cyc = (a, b, c)
                # Use sorted tuple key to deduplicate ignoring rotation
                key = tuple(sorted(cyc))
                prod = edges[a][b] * edges[b][c] * edges[c][a]
                cycles.append((prod, (a, b, c)))

if not cycles:
    print('No 3-cycles found')
    raise SystemExit(0)

# sort by product descending
cycles_sorted = sorted(cycles, key=lambda x: x[0], reverse=True)
print('\nTop 5 3-cycles by product (prod >1 means profitable):')
for prod, (a, b, c) in cycles_sorted[:5]:
    net_pct = (prod - 1.0) * 100.0
    print('\nCycle: {} -> {} -> {} -> {}'.format(a, b, c, a))
    print('  product = {:.12f}   net_pct = {:.6f}%'.format(prod, net_pct))
    # show each edge
    r1 = edges[a][b]
    r2 = edges[b][c]
    r3 = edges[c][a]
    print('  {}->{} rate = {:.12f}'.format(a, b, r1))
    print('  {}->{} rate = {:.12f}'.format(b, c, r2))
    print('  {}->{} rate = {:.12f}'.format(c, a, r3))

# print the single top cycle as an explicit step-by-step applied to 1 unit of a
prod_top, (a, b, c) = cycles_sorted[0]
print('\nDetailed step-by-step for top cycle:')
amount = 1.0
r1 = edges[a][b]
r2 = edges[b][c]
r3 = edges[c][a]
print(' Start with 1 {}.'.format(a))
am1 = amount * r1
print(' After {}->{} multiply by {:.12f} -> {:.12f} {}'.format(a, b, r1, am1, b))
am2 = am1 * r2
print(' After {}->{} multiply by {:.12f} -> {:.12f} {}'.format(b, c, r2, am2, c))
am3 = am2 * r3
print(' After {}->{} multiply by {:.12f} -> {:.12f} {}'.format(c, a, r3, am3, a))
print(' Final amount in {} = {:.12f} (net_pct = {:.6f}%)'.format(a, am3, (am3 - 1.0) * 100.0))
