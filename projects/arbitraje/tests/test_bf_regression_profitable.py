import pytest
from arbitraje.engine_techniques import _tech_bellman_ford
import json, pathlib

def test_bf_profitable_cycle_detected():
    # Load the offline profitable snapshot
    p = pathlib.Path(__file__).resolve().parents[1] / 'artifacts' / 'arbitraje' / 'offline_snapshot_profitable.json'
    data = json.load(open(p, 'r', encoding='utf-8'))
    # For each exchange, run the engine with relaxed config and check at least one cycle is found
    for ex, payload in data.items():
        payload2 = dict(payload)
        payload2.update({'fee': 0.10, 'min_net': 0.0, 'min_hops': 0, 'max_hops': 0, 'top': 10, 'latency_penalty': 0.0})
        res = _tech_bellman_ford(ex, payload2, {'techniques': {'use_numba': False}, 'bf': {}})
        assert len(res) > 0, f"No cycles detected for {ex}"
        # Optionally, check the net_bps_est is positive
        assert any(r.get('net_bps_est', 0) > 0 for r in res), f"No profitable cycle for {ex}"