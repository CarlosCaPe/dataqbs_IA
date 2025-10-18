from pathlib import Path

p = Path("arbitraje/arbitrage_report_ccxt.py")
lines = p.read_text(encoding="utf-8").splitlines()
for i in range(3550, 3596):
    print(f"{i+1:5d}: {repr(lines[i])}")
