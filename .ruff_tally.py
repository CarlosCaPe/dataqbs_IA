import collections
import json
import os

REPORT = ".ruff_report.json"
if not os.path.exists(REPORT):
    print("ERROR: .ruff_report.json not found")
    raise SystemExit(1)

j = json.load(open(REPORT, "r", encoding="utf-8"))
counts = collections.Counter()
files_errors = {}
skip_patterns = [
    "/sdk/",
    "/artifacts/",
    ".ipynb",
    "/examples/",
    "/example/",
    "/node_modules/",
    "/vendor/",
]
for e in j:
    f = e.get("filename") or ""
    if not f:
        continue
    fl = f.replace("\\\\", "/").replace("\\", "/")
    low = fl.lower()
    if any(p in low for p in skip_patterns):
        continue
    counts[fl] += 1
    files_errors.setdefault(fl, []).append(e.get("code"))

TOP = counts.most_common(20)

mapping = {
    "F401": "remove-unused-import",
    "F821": "undefined-name",
    "F405": "star-import-usage",
    "F403": "import-star",
    "F811": "redefinition-while-unused",
    "F841": "remove-unused-local",
    "E501": "line-too-long",
    "E402": "imports-not-at-top",
    "E712": "replace-==True",
    "E731": "lambda-assignment",
    "E722": "bare-except",
    "E721": "use-is-or-isinstance",
}

out = []
print("\nTop non-vendor files with ruff issues (top 20):\n")
for i, (fn, cnt) in enumerate(TOP, 1):
    codes = collections.Counter(files_errors[fn])
    topcodes = codes.most_common(6)
    print(f"{i:2d}. {cnt:4d} errors — {fn}")
    for code, num in topcodes:
        sugg = mapping.get(code, "manual")
        print(f"     {code:6s} x{num:3d} -> {sugg}")
    out.append({"file": fn, "count": cnt, "codes": topcodes})
print("\nTotal non-vendor files with issues:", len(counts))

# write JSON summary
with open(".ruff_top20.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)

print("\nWrote .ruff_top20.json with details.")
