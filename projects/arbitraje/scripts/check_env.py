import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # type: ignore


def load_envs() -> None:
    # Load .env from monorepo root and project root if python-dotenv is available
    if load_dotenv is None:
        return
    project_root = Path(__file__).resolve().parents[1]
    monorepo_root = project_root.parent.parent
    # Do not override existing environment values
    try:
        load_dotenv(dotenv_path=str(monorepo_root / ".env"), override=False)
    except Exception:
        pass
    try:
        load_dotenv(dotenv_path=str(project_root / ".env"), override=False)
    except Exception:
        pass


def present(var: str) -> bool:
    v = os.environ.get(var)
    return bool(v and str(v).strip())


def main() -> int:
    load_envs()
    checks = {
        "binance": ["BINANCE_API_KEY", "BINANCE_API_SECRET"],
        "mexc": ["MEXC_API_KEY", "MEXC_API_SECRET"],
        "bitget": ["BITGET_API_KEY", "BITGET_API_SECRET", "BITGET_PASSWORD"],
        "okx": ["OKX_API_KEY", "OKX_API_SECRET", "OKX_PASSWORD"],
    }
    print("Exchange | keys_present")
    print("-------- | ------------")
    for ex, vars_ in checks.items():
        ok = all(present(v) for v in vars_)
        # Do not print actual values; only presence
        print(f"{ex:7} | {str(ok)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
