import pytest

from arbitraje.engine_techniques import _tech_bellman_ford
import importlib.util
import sys
from pathlib import Path

# load tools/bf_numba_impl.py as a module (tests run with package root as projects/arbitraje)
_mod_path = Path(__file__).resolve().parents[1] / "tools" / "bf_numba_impl.py"
spec = importlib.util.spec_from_file_location("bf_numba_impl", str(_mod_path))
bf_mod = importlib.util.module_from_spec(spec)
sys.modules["bf_numba_impl"] = bf_mod
spec.loader.exec_module(bf_mod)
build_arrays_from_payload = bf_mod.build_arrays_from_payload
bellman_ford_numba = bf_mod.bellman_ford_numba


def make_small_snapshot_triangle():
    tickers = {
        "A/B": {"bid": 1.02, "ask": 1.0, "last": 1.0},
        "B/C": {"bid": 1.02, "ask": 1.0, "last": 1.0},
        "C/A": {"bid": 1.02, "ask": 1.0, "last": 1.0},
    }
    payload = {
        "ex_id": "testex",
        "quote": "USDT",
        "tokens": ["A", "B", "C"],
        "tickers": tickers,
        "fee": 0.10,
        "min_net": 0.0,
        "ts": "tst",
    }
    return payload


def test_numba_vs_python_equivalence():
    payload = make_small_snapshot_triangle()
    # run engine python technique
    res_py = _tech_bellman_ford("snap", payload, {"techniques": {"enabled": ["bellman_ford"]}})
    # build arrays and run numba wrapper directly
    nodes, u_arr, v_arr, w_arr = build_arrays_from_payload(payload)
    res_idx = bellman_ford_numba(len(nodes), u_arr, v_arr, w_arr)
    # convert index cycles to node cycles
    cycles_numba = set()
    for item in res_idx:
        if not item:
            continue
        # item may be a list of indices or a tuple (indices,sum_w,hops)
        if isinstance(item, (list, tuple)) and len(item) >= 3 and isinstance(item[0], (list, tuple)):
            c = list(item[0])
        else:
            c = list(item)
        if not c:
            continue
        if c[0] != c[-1]:
            c = c + [c[0]]
        cycles_numba.add("->".join([nodes[i] for i in c]))

    cycles_py = set(r.get("cycle") for r in res_py)
    assert cycles_numba & cycles_py, (cycles_numba, cycles_py)
