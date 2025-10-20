from arbitraje.tri_bot import consume_depth

def test_consume_depth_zero_qty():
    ob = {"asks": [[10.0, 1.0]], "bids": [[9.5, 1.0]]}
    px, slip = consume_depth(ob, side="buy", qty=0.0)
    assert px is None
    assert slip == 0.0
