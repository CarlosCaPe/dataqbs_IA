from pathlib import Path

p = Path("arbitraje/arbitrage_report_ccxt.py")
start = 3288
end = 3700
for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
    if start <= i <= end:
        leading = ""
        for ch in line:
            if ch in (" ", "\t"):
                leading += ch
            else:
                break
        print(f"{i:5d}: {len(leading):2d} {repr(leading)} {line[len(leading):]}")
