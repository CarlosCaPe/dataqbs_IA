from pathlib import Path

p = Path("arbitraje/arbitrage_report_ccxt.py")
src = p.read_text(encoding="utf-8")
lines = src.splitlines()
start_idx = None
end_idx = None
for i, l in enumerate(lines):
    if "for it in range(1, int(max(1, args.repeat)) + 1):" in l:
        start_idx = i
        break
for j in range(start_idx + 1, len(lines)):
    if "# ---------------------------" in lines[
        j
    ] and "INTER-EXCHANGE SPREAD MODE" in "\n".join(lines[j : j + 3]):
        end_idx = j
        break
if start_idx is None or end_idx is None:
    print("Markers not found", start_idx, end_idx)
else:
    print("Start", start_idx + 1, "End", end_idx + 1)
    changed = 0
    for k in range(start_idx + 1, end_idx):
        if lines[k].startswith("            "):
            lines[k] = lines[k][4:]
            changed += 1
    out = "\n".join(lines)
    p.write_text(out, encoding="utf-8")
    print("Done. Changed lines:", changed)
