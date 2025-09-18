import json, collections, sys
from pathlib import Path

REPORT_PATH = Path('emails_out/validation_report.json')
OUTPUT_CSV = Path('emails_out/domain_inventory.csv')
OUTPUT_LIST = Path('emails_out/domains_list.txt')

if not REPORT_PATH.exists():
    print('validation_report.json not found', file=sys.stderr)
    sys.exit(1)

data = json.loads(REPORT_PATH.read_text(encoding='utf-8'))
counts = collections.defaultdict(lambda: collections.Counter())

for item in data.get('items', []):
    addr = item.get('from') or ''
    if '@' not in addr:
        continue
    dom = addr.split('@', 1)[1].lower().strip()
    if not dom:
        continue
    cat = item.get('category') or 'Unknown'
    counts[dom][cat] += 1
    counts[dom]['_total'] += 1

lines = ['domain,total,Clean,Spam,Sus,Scam,Unknown']
for dom, c in sorted(counts.items(), key=lambda x: (-x[1]['_total'], x[0])):
    lines.append(f"{dom},{c['_total']},{c.get('Clean',0)},{c.get('Spam',0)},{c.get('Sus',0)},{c.get('Scam',0)},{c.get('Unknown',0)}")

OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_CSV.write_text('\n'.join(lines), encoding='utf-8')
# Plain list (just domain names sorted by frequency desc)
plain = [l.split(',')[0] for l in lines[1:]]
OUTPUT_LIST.write_text('\n'.join(plain), encoding='utf-8')
print(f"Generated {OUTPUT_CSV} and {OUTPUT_LIST} with {len(counts)} domains.")
