from __future__ import annotations

import os, time, math, argparse, logging, sys, json
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import ccxt
import pandas as pd
import yaml
try:
    import ujson as _json
except Exception:
    _json = None

from . import paths
from .ws_binance import BinanceL2PartialBook  # works when --ex binance; other venues can get similar wrappers
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=str(paths.MONOREPO_ROOT/".env"), override=False)
    load_dotenv(dotenv_path=str(paths.PROJECT_ROOT/".env"), override=False)
except Exception:
    pass


logger = logging.getLogger("arbitraje_tri")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    try:
        paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(paths.LOGS_DIR/"tri_bot.log", encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass


@dataclass
class Opportunity:
    exchange: str
    cycle: Tuple[str, str, str, str]  # A->B->C->A
    net_bps_est: float
    fee_bps_total: float
    slippage_bps_est: float


def read_yaml(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


def get_env_str(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if v is not None else default


def mk_exchange(ex_id: str, timeout_ms: int = 20000) -> ccxt.Exchange:
    cls = getattr(ccxt, ex_id)
    ex = cls({"enableRateLimit": True})
    try:
        ex.timeout = int(timeout_ms)
    except Exception:
        pass
    return ex


def best_bid_ask(ob: dict) -> Tuple[Optional[float], Optional[float]]:
    try:
        bid = ob.get("bids", [[None]])[0][0]
        ask = ob.get("asks", [[None]])[0][0]
        return (float(bid) if bid else None, float(ask) if ask else None)
    except Exception:
        return None, None


def consume_depth(ob: dict, side: str, qty: float) -> Tuple[Optional[float], float]:
    """Depth-aware fill: return (avg_price, slippage_bps_est). side=buy uses asks; sell uses bids."""
    if qty <= 0:
        return None, 0.0
    levels = ob.get("asks") if side == "buy" else ob.get("bids")
    if not levels:
        return None, 0.0
    remaining = float(qty)
    notional = 0.0
    qty_filled = 0.0
    ref_px = levels[0][0]
    for px, q in levels:
        px = float(px); q = float(q)
        take = min(remaining, q)
        notional += take * px
        qty_filled += take
        remaining -= take
        if remaining <= 1e-15:
            break
    if qty_filled <= 0:
        return None, 0.0
    avg_px = notional / qty_filled
    # simple slippage estimate vs top-of-book in bps
    slippage_bps = 0.0
    try:
        if ref_px and avg_px:
            if side == "buy":
                slippage_bps = max(0.0, (avg_px / ref_px - 1.0) * 10000.0)
            else:
                slippage_bps = max(0.0, (1.0 - avg_px / ref_px) * 10000.0)
    except Exception:
        pass
    return avg_px, slippage_bps


def find_triangles(ex: ccxt.Exchange, quote: str, whitelist: List[str]) -> List[Tuple[str, str, str, str]]:
    """Derive triangles A/B, B/C, C/A for bases in whitelist with common quote."""
    markets = ex.load_markets()
    syms = [s for s in markets.keys() if s.endswith(f"/{quote}")]
    bases = [s.split("/")[0] for s in syms]
    bases = [b for b in bases if (not whitelist or b in whitelist)]
    bases = sorted(set(bases))
    tris = []
    # triangles like: A/USDT, A/B, B/USDT → A->B->USDT->A simplified as quote-based cycles
    for i in range(len(bases)):
        for j in range(i+1, len(bases)):
            a = bases[i]; b = bases[j]
            # Cycle A -> B -> quote -> A
            # require symbols existence: A/B or B/A, A/quote, B/quote
            s_ab = f"{a}/{b}"; s_ba = f"{b}/{a}"
            if s_ab in markets or s_ba in markets:
                if f"{a}/{quote}" in markets and f"{b}/{quote}" in markets:
                    tris.append((a, b, quote, a))
    return tris


def evaluate_cycle(ex: ccxt.Exchange, a: str, b: str, q: str, size_q: float, fee_bps: float, max_slip_bps: float) -> Optional[Opportunity]:
    # Symbols
    sym_aq = f"{a}/{q}"; sym_bq = f"{b}/{q}"
    sym_ab = f"{a}/{b}"; sym_ba = f"{b}/{a}"
    # Order books
    ob_aq = ex.fetch_order_book(sym_aq, limit=20)
    ob_bq = ex.fetch_order_book(sym_bq, limit=20)
    ob_ab = ex.fetch_order_book(sym_ab, limit=20) if sym_ab in ex.markets else None
    ob_ba = ex.fetch_order_book(sym_ba, limit=20) if (ob_ab is None and sym_ba in ex.markets) else None

    # Step1: buy A with Q at ask using depth
    px_aq, slip1 = consume_depth(ob_aq, side="buy", qty=size_q/ max(1e-12, (ob_aq.get('asks', [[1,1]])[0][0])))
    # We need consistent sizing; approximate by first converting Q→A size using best ask
    best_ask_aq = ob_aq.get('asks', [[None, None]])[0][0] or None
    if best_ask_aq is None or px_aq is None:
        return None
    qty_a = size_q / float(best_ask_aq)
    px_aq, slip1 = consume_depth(ob_aq, side="buy", qty=qty_a)
    if px_aq is None:
        return None
    # Step2: trade A→B (sell A for B)
    if ob_ab is not None:
        px_ab, slip2 = consume_depth(ob_ab, side="sell", qty=qty_a)
        if px_ab is None:
            return None
        qty_b = qty_a * px_ab
    else:
        ob_ba = ob_ba or ex.fetch_order_book(sym_ba, limit=20)
        px_ba, slip2 = consume_depth(ob_ba, side="buy", qty=qty_a)  # buying B with A
        if px_ba is None:
            return None
        qty_b = qty_a / px_ba
    # Step3: sell B for Q at bid
    px_bq, slip3 = consume_depth(ob_bq, side="sell", qty=qty_b)
    if px_bq is None:
        return None
    size_q_out = qty_b * px_bq

    # Fees (taker for 3 legs)
    fee_bps_total = 3.0 * float(fee_bps)
    slippage_bps_est = min(max_slip_bps, (slip1 + slip2 + slip3))
    gross = (size_q_out / size_q - 1.0) * 10000.0
    net_bps_est = gross - fee_bps_total - slippage_bps_est
    return Opportunity(exchange=ex.id, cycle=(a,b,q,a), net_bps_est=net_bps_est, fee_bps_total=fee_bps_total, slippage_bps_est=slippage_bps_est)


def main() -> None:
    parser = argparse.ArgumentParser(description="Triangular arbitrage (paper) depth-aware within one exchange")
    parser.add_argument("--ex", default=os.environ.get("EX", os.environ.get("EXCHANGE", "binance")))
    parser.add_argument("--quote", default=os.environ.get("QUOTE", "USDT"))
    parser.add_argument("--mode", choices=["paper","live"], default=os.environ.get("MODE", "paper"))
    parser.add_argument("--config", default=str(paths.MONOREPO_ROOT/"config.yaml"))
    parser.add_argument("--fee_bps", type=float, default=float(os.environ.get("TAKER_FEE_BPS", "10")))
    parser.add_argument("--min_profit_bps", type=float, default=float(os.environ.get("MIN_PROFIT_BPS", "12")))
    parser.add_argument("--max_slippage_bps", type=float, default=float(os.environ.get("MAX_SLIPPAGE_BPS", "8")))
    parser.add_argument("--max_notional", type=float, default=float(os.environ.get("MAX_NOTIONAL_PER_TRADE", "100")))
    parser.add_argument("--latency_penalty_bps", type=float, default=float(os.environ.get("LATENCY_PENALTY_BPS", "2")))
    parser.add_argument("--use_ws", action="store_true", help="Usar WebSocket L2 parcial si está disponible; fallback REST si no hay libro")
    parser.add_argument("--max_open_chains", type=int, default=int(os.environ.get("MAX_OPEN_CHAINS", "1")))
    parser.add_argument("--max_drawdown_session_bps", type=float, default=float(os.environ.get("MAX_DRAWDOWN_SESSION_BPS", "200")))
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()

    cfg = read_yaml(args.config)
    whitelist = cfg.get("whitelist_symbols") or []

    ex = mk_exchange(args.ex)
    ex.load_markets()

    triangles = find_triangles(ex, args.quote, whitelist)
    logger.info("%s: %d triángulos derivados (quote=%s)", ex.id, len(triangles), args.quote)

    paths.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = paths.OUTPUTS_DIR / f"tri_bot_{ex.id}_{args.quote.lower()}.csv"
    jsonl_path = paths.LOGS_DIR / f"tri_bot_{ex.id}_{args.quote.lower()}.jsonl"

    rows: List[dict] = []
    # Session metrics
    pnl_bps_cum = 0.0
    pnl_bps_peak = 0.0
    max_dd_bps = 0.0
    n_trades = 0
    wins = 0
    open_chains = 0
    for it in range(1, int(max(1, args.repeat)) + 1):
        seen = 0
        actionable = 0
        for (a,b,q,a2) in triangles:
            if q != args.quote or a2 != a:
                continue
            try:
                # Prefer WS book if requested and available (binance only in this helper)
                use_ws = bool(args.use_ws and ex.id == 'binance')
                op = None
                if use_ws:
                    # Start/consult WS partial books per needed symbols; minimal cache per iteration
                    syms = [f"{a}/{q}", f"{b}/{q}", f"{a}/{b}", f"{b}/{a}"]
                    ws_books: Dict[str, dict] = {}
                    managers: List[BinanceL2PartialBook] = []
                    try:
                        for s in syms:
                            sym = s.replace('/','').lower()
                            m = BinanceL2PartialBook(symbol=sym)
                            m.start()
                            managers.append(m)
                        # wait briefly to get first snapshot
                        time.sleep(0.2)
                        for s, m in zip(syms, managers):
                            book = m.last_book()
                            if book:
                                ws_books[s] = book
                        # fallback REST if any missing
                        if len([k for k in ws_books.values() if k]) < 2:
                            # Not enough data; defer to REST evaluate
                            op = evaluate_cycle(ex, a, b, q, size_q=float(args.max_notional), fee_bps=args.fee_bps, max_slippage_bps=args.max_slippage_bps)
                        else:
                            # Use depth-aware with WS books
                            # Re-implement minimal evaluation against provided books
                            def consume_local(sym: str, side: str, qty: float):
                                book = ws_books.get(sym)
                                if not book:
                                    return None, 0.0
                                # reuse same slippage calc
                                from math import isfinite
                                bids = book.get('bids') or []
                                asks = book.get('asks') or []
                                ob = {'bids': bids, 'asks': asks}
                                return consume_depth(ob, side=side, qty=qty)

                            # step sizing mirroring evaluate_cycle
                            sym_aq = f"{a}/{q}"; sym_bq = f"{b}/{q}"
                            sym_ab = f"{a}/{b}"; sym_ba = f"{b}/{a}"
                            best_ask_aq = (ws_books.get(sym_aq, {}).get('asks') or [[None,None]])[0][0]
                            if not best_ask_aq:
                                op = None
                            else:
                                qty_a = float(args.max_notional) / float(best_ask_aq)
                                px_aq, slip1 = consume_local(sym_aq, 'buy', qty_a)
                                if px_aq is None:
                                    op = None
                                else:
                                    # A->B
                                    if ws_books.get(sym_ab):
                                        px_ab, slip2 = consume_local(sym_ab, 'sell', qty_a)
                                        if px_ab is None:
                                            op = None
                                        else:
                                            qty_b = qty_a * px_ab
                                    elif ws_books.get(sym_ba):
                                        px_ba, slip2 = consume_local(sym_ba, 'buy', qty_a)
                                        if px_ba is None:
                                            op = None
                                        else:
                                            qty_b = qty_a / px_ba
                                    else:
                                        op = None
                                    if op is None:
                                        pass
                                    else:
                                        px_bq, slip3 = consume_local(sym_bq, 'sell', qty_b)
                                        if px_bq is None:
                                            op = None
                                        else:
                                            size_q_out = qty_b * px_bq
                                            fee_bps_total = 3.0 * float(args.fee_bps)
                                            slippage_bps_est = min(float(args.max_slippage_bps), (slip1+slip2+slip3))
                                            gross = (size_q_out / float(args.max_notional) - 1.0) * 10000.0
                                            net_bps_est = gross - fee_bps_total - slippage_bps_est - float(args.latency_penalty_bps)
                                            op = Opportunity(exchange=ex.id, cycle=(a,b,q,a), net_bps_est=net_bps_est, fee_bps_total=fee_bps_total, slippage_bps_est=slippage_bps_est)
                    finally:
                        for m in managers:
                            try:
                                m.stop()
                            except Exception:
                                pass
                if op is None:
                    # REST path
                    op = evaluate_cycle(ex, a, b, q, size_q=float(args.max_notional), fee_bps=args.fee_bps, max_slippage_bps=args.max_slippage_bps)
            except Exception as e:
                logger.debug("eval fallo %s-%s-%s: %s", a,b,q,e)
                continue
            seen += 1
            if op and op.net_bps_est >= float(args.min_profit_bps):
                # Session risk: circuit breaker and MAX_OPEN_CHAINS
                if args.mode == 'live':
                    if max_dd_bps >= float(args.max_drawdown_session_bps):
                        continue
                    if open_chains >= int(args.max_open_chains):
                        continue
                    # Placeholder live execution (to implement fully): mark as executed
                    open_chains += 1
                    # After filled/unwound, decrement; for now simulate instant close
                    open_chains = max(0, open_chains - 1)
                actionable += 1
                rec = {
                    "ts": pd.Timestamp.utcnow().isoformat(),
                    "venue": ex.id,
                    "mode": args.mode,
                    "cycle": f"{a}->{b}->{q}->{a}",
                    "notional_quote_req": float(args.max_notional),
                    "net_bps_est": round(op.net_bps_est - float(args.latency_penalty_bps), 4),
                    "fee_bps_total": op.fee_bps_total,
                    "slippage_bps_est": op.slippage_bps_est,
                    "status": "actionable",
                }
                rows.append(rec)
                line = (_json or json).dumps(rec)
                try:
                    with open(jsonl_path, "a", encoding="utf-8") as jfh:
                        jfh.write(line+"\n")
                except Exception:
                    pass
                # Update session PnL (approx by net_bps_est)
                n_trades += 1
                pnl_bps_cum += float(rec["net_bps_est"]) / max(1, actionable)
                pnl_bps_peak = max(pnl_bps_peak, pnl_bps_cum)
                max_dd_bps = max(max_dd_bps, pnl_bps_peak - pnl_bps_cum)
                if rec["net_bps_est"] > 0:
                    wins += 1
        logger.info("it#%d: opportunities_seen=%d actionable=%d (min_profit_bps=%.2f)", it, seen, actionable, args.min_profit_bps)
        if it < args.repeat:
            time.sleep(max(0.0, args.sleep))

    if rows:
        pd.DataFrame(rows).to_csv(csv_path, index=False)
        logger.info("CSV: %s", csv_path)
    # Session metrics
    if n_trades > 0:
        win_rate = wins / n_trades
        sess = {
            "n_trades": n_trades,
            "win_rate": round(win_rate, 4),
            "max_dd_bps": round(max_dd_bps, 4),
        }
        logger.info("SESSION: %s", (_json or json).dumps(sess))

if __name__ == "__main__":
    main()
