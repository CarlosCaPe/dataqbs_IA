from __future__ import annotations

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict

import requests
import pandas as pd
from dotenv import load_dotenv

from . import paths
from .providers import coinpaprika

# Basic logger
logger = logging.getLogger("arbitraje")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    try:
        paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(paths.LOGS_DIR / "arbitraje.log", encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass

load_dotenv()  # load .env if present

# === Config (env override friendly) ===
COIN_IDS: List[str] = json.loads(os.getenv("ARBITRAJE_COIN_IDS", "[]"))
QUOTE: str = os.getenv("ARBITRAJE_QUOTE", "USD")
MIN_TRUST: str = os.getenv("ARBITRAJE_MIN_TRUST", "green")
SPREAD_THRESHOLD: float = float(os.getenv("ARBITRAJE_SPREAD_THRESHOLD", "0.5"))
API_KEY: str = os.getenv("COINGECKO_DEMO_API_KEY", "")
HEADERS: Dict[str, str] = {"x-cg-demo-api-key": API_KEY} if API_KEY else {}
PROVIDER: str = os.getenv("ARBITRAJE_PROVIDER", "coinpaprika").lower()

SESSION = requests.Session()
TIMEOUT = int(os.getenv("ARBITRAJE_HTTP_TIMEOUT", "15"))
BASE_URL = os.getenv("ARBITRAJE_BASE_URL", "https://api.coingecko.com/api/v3")
CONTRACT_PREF = [
    s.strip() for s in os.getenv(
        "ARBITRAJE_CONTRACT_PREF",
        "ethereum,binance-smart-chain,arbitrum-one,base,polygon-pos,optimistic-ethereum,solana,avalanche"
    ).split(",") if s.strip()
]

# simple in-memory cache to avoid repeated lookups
_CONTRACT_CACHE: dict[str, dict] = {}


def get_coin_contract_info(coin_id: str) -> dict:
    """Return contract info for a coin from /coins/{id}.

    Response schema example includes {"platforms": {"ethereum": "0x...", ...}}
    For native coins (BTC, ETH, SOL) platforms may be empty.
    Returns dict: {"platforms": {...}, "primary_chain": str|None, "primary_address": str|None}
    """
    if coin_id in _CONTRACT_CACHE:
        return _CONTRACT_CACHE[coin_id]
    url = f"{BASE_URL}/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "false",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false",
    }
    primary_chain = None
    primary_address = None
    platforms = {}
    try:
        resp = SESSION.get(url, headers=HEADERS, timeout=TIMEOUT, params=params)
        if resp.status_code == 200:
            platforms = resp.json().get("platforms", {}) or {}
            # pick preferred chain with non-empty address
            for chain in CONTRACT_PREF:
                addr = (platforms or {}).get(chain)
                if isinstance(addr, str) and addr.strip():
                    primary_chain = chain
                    primary_address = addr.strip()
                    break
            # fallback to first available
            if not primary_address and isinstance(platforms, dict):
                for chain, addr in platforms.items():
                    if isinstance(addr, str) and addr.strip():
                        primary_chain = chain
                        primary_address = addr.strip()
                        break
    except Exception:
        pass
    info = {
        "platforms": platforms,
        "primary_chain": primary_chain,
        "primary_address": primary_address,
    }
    _CONTRACT_CACHE[coin_id] = info
    return info


def get_tickers(coin_id: str) -> List[Dict]:
    """Fetch tickers for a coin from CoinGecko public API.

    Filters by QUOTE target, MIN_TRUST trust_score, and excludes stale/anomaly.
    """
    url = f"{BASE_URL}/coins/{coin_id}/tickers"
    try:
        resp = SESSION.get(url, headers=HEADERS, timeout=TIMEOUT)
    except Exception as e:
        logger.warning("Request error for %s: %s", coin_id, e)
        return []
    if resp.status_code != 200:
        logger.warning("HTTP %s for %s", resp.status_code, coin_id)
        return []
    try:
        data = resp.json().get("tickers", [])
    except Exception:
        logger.warning("Invalid JSON for %s", coin_id)
        return []
    out = []
    for t in data:
        try:
            if t.get("target") != QUOTE:
                continue
            if t.get("trust_score") != MIN_TRUST:
                continue
            if t.get("is_stale") or t.get("is_anomaly"):
                continue
            out.append({
                "coin": coin_id,
                "exchange": t["market"]["identifier"],
                "pair": f"{t['base']}/{t['target']}",
                "price": float(t["last"]),
                "trust": t["trust_score"],
                "is_stale": bool(t["is_stale"]),
                "is_anomaly": bool(t["is_anomaly"]),
            })
        except Exception:
            continue
    return out


def find_spreads(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for coin in df["coin"].unique():
        subset = df[df["coin"] == coin]
        if subset.empty:
            continue
        min_row = subset.loc[subset["price"].idxmin()]
        max_row = subset.loc[subset["price"].idxmax()]
        spread = (max_row["price"] - min_row["price"]) / min_row["price"] * 100
        if spread >= SPREAD_THRESHOLD:
            cinfo = get_coin_contract_info(coin)
            results.append({
                "coin": coin,
                "buy_exchange": min_row["exchange"],
                "buy_price": float(min_row["price"]),
                "sell_exchange": max_row["exchange"],
                "sell_price": float(max_row["price"]),
                "spread_%": round(float(spread), 3),
                "contract_chain": cinfo.get("primary_chain") or "N/A",
                "contract_address": cinfo.get("primary_address") or "N/A",
            })
    return pd.DataFrame(results)


def save_report(report: pd.DataFrame) -> None:
    if report.empty:
        logger.info("No spreads above threshold.")
        return
    try:
        paths.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = paths.OUTPUTS_DIR / "arbitrage_report.csv"
        md_path = paths.OUTPUTS_DIR / "arbitrage_report.md"
        report.to_csv(csv_path, index=False)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report.to_markdown(index=False))
        logger.info("Report written to %s and %s", csv_path, md_path)
    except Exception as e:
        logger.error("Failed writing report: %s", e)


def main() -> None:
    logger.info("Searching arbitrage opportunities (%s)", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    all_rows: List[Dict] = []
    session = SESSION
    if PROVIDER == "coinpaprika":
        # If no explicit list, pull top-300 ids by rank
        coins = COIN_IDS or coinpaprika.get_top_coin_ids(session, limit=300)
        logger.info("Provider: coinpaprika (coins=%d)", len(coins))
        for cid in coins:
            all_rows.extend(coinpaprika.get_markets_for_coin(session, cid))
    else:
        coins = COIN_IDS or ["bitcoin", "ethereum", "solana"]
        logger.info("Provider: coingecko (coins=%d)", len(coins))
        for coin in coins:
            all_rows.extend(get_tickers(coin))
    df = pd.DataFrame(all_rows)
    if df.empty:
        logger.error("No valid data found.")
        return
    report = find_spreads(df)
    if report.empty:
        logger.info("No spreads above threshold.")
    else:
        logger.info("Found %d opportunities:", len(report))
        try:
            md = report.to_markdown(index=False)
        except Exception:
            md = report.to_string(index=False)
        logger.info("\n%s", md)
        save_report(report)


if __name__ == "__main__":
    main()
