import os, shutil, logging
from pathlib import Path

logger = logging.getLogger('dataqbs')
if not logger.handlers:
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(sh)
try:
    log_dir = Path(r'c:\Users\Lenovo\dataqbs_IA\emails_out\logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / 'migrate_suspicious.log', encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(fh)
except Exception:
    pass
logger.setLevel(logging.INFO)
SRC = r'c:\Users\Lenovo\dataqbs_IA\emails_out\Gmail_dataqbs\Suspicious'
DST = r'c:\Users\Lenovo\dataqbs_IA\emails_out\Gmail_dataqbs\Sus'
count=0
if os.path.isdir(SRC):
    for name in os.listdir(SRC):
        if not name.lower().endswith('.eml'): continue
        new_name = name.replace('Suspicious','Sus')
        src_path = os.path.join(SRC,name)
        dst_path = os.path.join(DST,new_name)
        if os.path.exists(dst_path):
            os.remove(src_path)
        else:
            shutil.move(src_path,dst_path)
            count+=1
    try:
        os.rmdir(SRC)
    except OSError:
        pass
logger.info('Migrated %d files from %s to %s', count, SRC, DST)
