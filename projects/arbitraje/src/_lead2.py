from pathlib import Path

p = Path("arbitraje/arbitrage_report_ccxt.py")
start = 3248
end = 3320
for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
    if start <= i <= end:
        leading = ""
        for ch in line:
            if ch in (" ", "\t"):
                leading += ch
            else:
                break
        print(f"{i:5d}: {len(leading)} {repr(leading)} {line[len(leading):]}")
