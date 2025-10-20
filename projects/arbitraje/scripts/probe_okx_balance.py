import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # type: ignore

import json
import ccxt


def load_envs() -> None:
    if load_dotenv is None:
        return
    project_root = Path(__file__).resolve().parents[1]
    monorepo_root = project_root.parent.parent
    try:
        load_dotenv(dotenv_path=str(monorepo_root / ".env"), override=False)
    except Exception:
        pass
    try:
        load_dotenv(dotenv_path=str(project_root / ".env"), override=False)
    except Exception:
        pass


def summarize_balances(bal: dict) -> dict:
    res = {
        "free": {},
        "total": {},
        "nonzero_free": {},
        "nonzero_total": {},
    }
    try:
        free = bal.get("free") or {}
        total = bal.get("total") or {}
        res["free"] = {k: float(v) for k, v in free.items() if isinstance(v, (int, float))}
        res["total"] = {k: float(v) for k, v in total.items() if isinstance(v, (int, float))}
        res["nonzero_free"] = {k: v for k, v in res["free"].items() if v and abs(v) > 0}
        res["nonzero_total"] = {k: v for k, v in res["total"].items() if v and abs(v) > 0}
    except Exception:
        pass
    return res


def make_okx(options: dict | None = None) -> ccxt.okx:
    api_key = os.environ.get("OKX_API_KEY")
    api_secret = os.environ.get("OKX_API_SECRET")
    password = os.environ.get("OKX_PASSWORD")
    cfg = {
        "apiKey": api_key,
        "secret": api_secret,
        "password": password,
        "enableRateLimit": True,
    }
    if options:
        cfg["options"] = options
    return ccxt.okx(cfg)


def try_fetch(tag: str, ex: ccxt.okx) -> dict:
    out = {"tag": tag, "ok": False, "error": None, "balances": None}
    try:
        bal = ex.fetch_balance()
        out["ok"] = True
        out["balances"] = summarize_balances(bal)
    except Exception as e:
        out["error"] = str(e)
    return out


def main() -> int:
    load_envs()
    tests = [
        ("default", None),
        ("options.defaultType=spot", {"defaultType": "spot"}),
        ("options.defaultType=trading", {"defaultType": "trading"}),
        ("options.defaultType=funding", {"defaultType": "funding"}),
    ]
    results = []
    for tag, opts in tests:
        ex = make_okx(opts)
        r = try_fetch(tag, ex)
        # Trim large maps to just a few entries for readability
        bal = r.get("balances") or {}
        for key in ("nonzero_free", "nonzero_total"):
            try:
                items = list((bal.get(key) or {}).items())
                bal[key] = dict(items[:10])
            except Exception:
                pass
        results.append(r)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
