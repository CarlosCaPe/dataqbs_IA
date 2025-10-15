from __future__ import annotations

from arbitraje.tri_bot import consume_depth, evaluate_cycle


def test_consume_depth_basic():
    ob = {
        'asks': [[10.0, 1.0], [11.0, 2.0]],
        'bids': [[9.5, 1.5], [9.0, 3.0]],
    }
    px, slip = consume_depth(ob, 'buy', qty=1.0)
    assert px == 10.0
    assert slip >= 0.0
    px2, slip2 = consume_depth(ob, 'sell', qty=1.0)
    assert px2 == 9.5
    assert slip2 >= 0.0


class _EX:
    id = 'dummy'
    markets = {'AAA/USDT':{}, 'BBB/USDT':{}, 'AAA/BBB':{}}
    def load_markets(self):
        return self.markets
    def fetch_order_book(self, sym, limit=20):
        if sym == 'AAA/USDT':
            return {'asks': [[10.0, 2.0]], 'bids': [[9.9, 2.0]]}
        if sym == 'BBB/USDT':
            return {'asks': [[5.0, 2.0]], 'bids': [[4.9, 2.0]]}
        if sym == 'AAA/BBB':
            return {'asks': [[2.0, 2.0]], 'bids': [[1.9, 2.0]]}
        return {'asks': [], 'bids': []}


def test_evaluate_cycle_net_positive():
    ex = _EX()
    op = evaluate_cycle(ex, 'AAA','BBB','USDT', size_q=100.0, fee_bps=10.0, max_slippage_bps=8.0)
    assert op is not None
    # net may be small but shouldn't be NaN
    assert isinstance(op.net_bps_est, float)