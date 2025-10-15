import subprocess
import sys
from pathlib import Path


def test_cli_version_prints_version_and_engine():
    # Run the CLI in a subprocess to verify --version output
    proj = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, "-m", "arbitraje.arbitrage_report_ccxt", "--version"]
    p = subprocess.run(cmd, cwd=str(proj), capture_output=True, text=True, timeout=10)
    out = (p.stdout or p.stderr or "").strip()
    assert "arbitraje version:" in out
    assert "engine:" in out
