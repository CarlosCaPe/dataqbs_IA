import collections
import json
import logging
import sys
from pathlib import Path

REPORT_PATH = Path("emails_out/validation_report.json")
OUTPUT_CSV = Path("emails_out/domain_inventory.csv")
OUTPUT_LIST = Path("emails_out/domains_list.txt")
LOG_DIR = Path("emails_out/logs")

logger = logging.getLogger("dataqbs")
if not logger.handlers:
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(sh)
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_DIR / "extract_domains.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
except Exception:
    pass
logger.setLevel(logging.INFO)

if not REPORT_PATH.exists():
    logger.error("validation_report.json not found at %s", REPORT_PATH)
    sys.exit(1)

data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
counts = collections.defaultdict(lambda: collections.Counter())

for item in data.get("items", []):
    addr = item.get("from") or ""
    if "@" not in addr:
        continue
    dom = addr.split("@", 1)[1].lower().strip()
    if not dom:
        continue
    cat = item.get("category") or "Unknown"
    counts[dom][cat] += 1
    counts[dom]["_total"] += 1

lines = ["domain,total,Clean,Spam,Sus,Scam,Unknown"]
for dom, c in sorted(counts.items(), key=lambda x: (-x[1]["_total"], x[0])):
    lines.append(
        f"{dom},{c['_total']},{c.get('Clean',0)},{c.get('Spam',0)},{c.get('Sus',0)},{c.get('Scam',0)},{c.get('Unknown',0)}"
    )

OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_CSV.write_text("\n".join(lines), encoding="utf-8")
# Plain list (just domain names sorted by frequency desc)
plain = [ln.split(",")[0] for ln in lines[1:]]
OUTPUT_LIST.write_text("\n".join(plain), encoding="utf-8")
logger.info(
    "Generated %s and %s with %d domains.", OUTPUT_CSV, OUTPUT_LIST, len(counts)
)
