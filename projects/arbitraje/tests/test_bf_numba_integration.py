import json
from pathlib import Path
import pytest

from arbitraje import engine_techniques


@pytest.mark.skipif(
    True, reason="Numba tests are optional in CI unless env provides numba"
)
def test_bf_python_vs_numba_smoke():
    p = (
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "arbitraje"
        / "offline_snapshot_synth_large.json"
    )
    with open(p, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    first = next(iter(data.keys()))
    payload = data[first]
    # run python impl
    res_py = engine_techniques._tech_bellman_ford("test", payload, {})
    # run numba impl if available
    try:
        from bf_numba_impl import build_arrays_from_payload, bellman_ford_numba
    except Exception:
        pytest.skip("numba not available")
    nodes, u_arr, v_arr, w_arr = build_arrays_from_payload(payload)
    cycles = bellman_ford_numba(len(nodes), u_arr, v_arr, w_arr)
    # at least ensure code runs and returns list
    assert isinstance(res_py, list)
    assert isinstance(cycles, list)
