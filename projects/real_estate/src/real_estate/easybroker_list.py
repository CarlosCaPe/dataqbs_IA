import os
import json
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List, Optional
from threading import Lock
from datetime import datetime
import shutil

import requests

from . import paths

# ---------------- Logging ----------------
logger = logging.getLogger("easybroker")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(sh)
    try:
        paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(paths.LOGS_DIR / 'easybroker_export.log', encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)
    except Exception:  # pragma: no cover - logging setup failure non-fatal
        pass


class PropertyJsonDownloader:
    def __init__(self, api_key: str, properties_url: str, base_json_folder: str, max_workers: int = 10, only_if_stale: bool = False):
        self.api_key = api_key
        self.properties_url = properties_url
        self.base_json_folder = base_json_folder
        self.max_workers = max_workers
        self.only_if_stale = only_if_stale
        self._lock = Lock()
        self.stats = {"saved": 0, "updated": 0, "skipped": 0, "errors": 0}
        os.makedirs(self.base_json_folder, exist_ok=True)

    @staticmethod
    def _parse_dt(val: Optional[str]) -> Optional[datetime]:
        if not isinstance(val, str) or not val:
            return None
        try:
            if val.endswith('Z'):
                val = val.replace('Z', '+00:00')
            return datetime.fromisoformat(val)
        except Exception:
            return None

    def _detail_url_for(self, public_id: str) -> str:
        base = (self.properties_url or '').split('?')[0].rstrip('/')
        if base.endswith('/properties'):
            return f"{base}/{public_id}"
        return f"{base}/properties/{public_id}"

    def _fetch_details(self, public_id: str) -> dict | None:
        url = self._detail_url_for(public_id)
        headers = {"accept": "application/json", "X-Authorization": self.api_key}
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200 and resp.content:
                return resp.json()
            logger.warning(f"Detail request for {public_id} returned {resp.status_code}")
        except Exception as e:  # pragma: no cover
            logger.error(f"Error fetching details for {public_id}: {e}")
        return None

    def _save_one(self, rec: dict) -> None:
        public_id = rec.get('public_id') or rec.get('id')
        if not public_id:
            return
        path = os.path.join(self.base_json_folder, f"{public_id}.json")
        was_update = False
        if os.path.exists(path):
            if not self.only_if_stale:
                logger.info(f"Skipping existing JSON for {public_id}")
                with self._lock:
                    self.stats["skipped"] += 1
                return
            local_updated: Optional[datetime] = None
            try:
                with open(path, 'r', encoding='utf-8') as rf:
                    local_data = json.load(rf)
                    local_updated = self._parse_dt(local_data.get('updated_at'))
            except Exception:
                local_updated = None
            remote_updated = self._parse_dt(rec.get('updated_at'))
            if local_updated and remote_updated and local_updated >= remote_updated:
                logger.info(f"Skipping JSON (up-to-date) for {public_id}")
                with self._lock:
                    self.stats["skipped"] += 1
                return
            was_update = True
        has_imgs = isinstance(rec.get('images'), list) or isinstance(rec.get('photos'), list) or isinstance(rec.get('property_images'), list)
        if not has_imgs:
            details = self._fetch_details(public_id)
            if isinstance(details, dict) and details:
                rec = details
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
            key = "updated" if was_update else "saved"
            logger.info(f"Saved JSON for {public_id}")
            with self._lock:
                self.stats[key] += 1
        except Exception as e:  # pragma: no cover
            logger.error(f"Error saving {public_id}: {e}")
            with self._lock:
                self.stats["errors"] += 1

    def download_all(self) -> None:
        logger.info(f"Fetching properties from {self.properties_url}")
        url = self.properties_url
        futures = []
        headers = {"accept": "application/json", "X-Authorization": self.api_key}
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            while url:
                try:
                    resp = requests.get(url, headers=headers, timeout=15)
                except Exception as e:  # pragma: no cover
                    logger.error(f"Request error for url {url}: {e}")
                    break
                if resp.status_code != 200:
                    logger.warning(f"Non-200 response fetching properties: {resp.status_code}")
                    break
                data = resp.json() if resp.content else {}
                records: Iterable = []
                if isinstance(data, dict):
                    records = data.get('content') or []
                elif isinstance(data, list):
                    records = data
                for rec in records:
                    futures.append(ex.submit(self._save_one, rec))
                url = data.get('pagination', {}).get('next_page') if isinstance(data, dict) else None
            for _ in as_completed(futures):
                pass
        logger.info('Finished downloading JSONs')
        s = self.stats
        logger.info(f"JSON summary -> saved: {s['saved']}, updated: {s['updated']}, skipped: {s['skipped']}, errors: {s['errors']}")


class PropertyImageDownloader:
    def __init__(self, base_json_folder: str, images_folder: str, max_workers: int = 10):
        self.base_json_folder = base_json_folder
        self.images_folder = images_folder
        self.max_workers = max_workers
        self._lock = Lock()
        self.stats = {"downloaded": 0, "skipped": 0, "errors": 0}
        os.makedirs(self.images_folder, exist_ok=True)

    @staticmethod
    def _extract_urls(data: dict) -> List[str]:
        urls: List[str] = []
        imgs = data.get('images')
        if isinstance(imgs, list):
            for img in imgs:
                if isinstance(img, dict) and img.get('url'):
                    urls.append(img['url'])
                elif isinstance(img, str):
                    urls.append(img)
        pimgs = data.get('property_images')
        if isinstance(pimgs, list):
            for img in pimgs:
                if isinstance(img, dict) and img.get('url'):
                    urls.append(img['url'])
                elif isinstance(img, str):
                    urls.append(img)
        photos = data.get('photos')
        if isinstance(photos, list):
            for img in photos:
                if isinstance(img, dict) and img.get('url'):
                    urls.append(img['url'])
                elif isinstance(img, str):
                    urls.append(img)
        if isinstance(data.get('title_image_full'), str):
            urls.append(data['title_image_full'])
        seen = set()
        dedup = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                dedup.append(u)
        return dedup

    def _download_for_file(self, filename: str) -> None:
        if not filename.endswith('.json'):
            return
        src = os.path.join(self.base_json_folder, filename)
        try:
            with open(src, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:  # pragma: no cover
            logger.error(f"Failed to load {filename}: {e}")
            return
        prop_id = data.get('public_id') or data.get('id') or os.path.splitext(filename)[0]
        urls = self._extract_urls(data)
        if not urls:
            return
        dest_folder = os.path.join(self.images_folder, prop_id)
        os.makedirs(dest_folder, exist_ok=True)
        for idx, url in enumerate(urls, start=1):
            try:
                base = url.split('?')[0]
                ext = os.path.splitext(base)[1] or '.jpg'
                fname = f"img_{idx}{ext}"
                out_path = os.path.join(dest_folder, fname)
                if os.path.exists(out_path):
                    logger.info(f"Skipping existing image {out_path}")
                    with self._lock:
                        self.stats["skipped"] += 1
                    continue
                r = requests.get(url, stream=True, timeout=15)
                if r.status_code == 200:
                    with open(out_path, 'wb') as wf:
                        for chunk in r.iter_content(8192):
                            if chunk:
                                wf.write(chunk)
                    logger.info(f"Downloaded {fname} for {prop_id}")
                    with self._lock:
                        self.stats["downloaded"] += 1
                else:
                    logger.warning(f"Image request for {url} returned {r.status_code}")
            except Exception as e:  # pragma: no cover
                logger.error(f"Error downloading image {url} for {prop_id}: {e}")
                with self._lock:
                    self.stats["errors"] += 1

    def download_all(self) -> None:
        logger.info('Starting image downloads')
        files = [f for f in os.listdir(self.base_json_folder) if f.endswith('.json')]
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = [ex.submit(self._download_for_file, fn) for fn in files]
            for _ in as_completed(futures):
                pass
        logger.info('Finished image downloads')
        s = self.stats
        logger.info(f"Images summary -> downloaded: {s['downloaded']}, skipped: {s['skipped']}, errors: {s['errors']}")


class ListingStatusDownloader:
    def __init__(self, api_key: str, listing_statuses_url: str, output_folder: str):
        self.api_key = api_key
        self.url = listing_statuses_url
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)

    def download(self) -> None:
        logger.info(f"Fetching listing statuses from {self.url}")
        all_items = []
        url = self.url
        headers = {"accept": "application/json", "X-Authorization": self.api_key}
        while url:
            try:
                r = requests.get(url, headers=headers, timeout=15)
            except Exception as e:  # pragma: no cover
                logger.error(f"Request error fetching listing statuses: {e}")
                break
            if r.status_code != 200:
                logger.warning(f"Non-200 from listing statuses endpoint: {r.status_code}")
                break
            data = r.json() if r.content else {}
            items = data.get('content', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            all_items.extend(items)
            url = data.get('pagination', {}).get('next_page') if isinstance(data, dict) else None
        out = os.path.join(self.output_folder, 'listing_statuses.json')
        try:
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(all_items, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved listing statuses to {out}")
        except Exception as e:  # pragma: no cover
            logger.error(f"Failed saving listing statuses: {e}")


def _normalize_easybrokers_excel(root_dir: str) -> None:
    excel_dirs = [paths.DATA_DIR]  # keeping normalization simple; artifacts location
    for d in excel_dirs:
        if not os.path.isdir(d):
            continue
        try:
            excel_files = [f for f in os.listdir(d) if f.lower().startswith('easybrokers_') and f.lower().endswith('.xlsx')]
        except Exception:
            continue
        if not excel_files:
            continue
        latest = max(excel_files)
        src = os.path.join(d, latest)
        dst = os.path.join(d, 'easybrokers.xlsx')
        try:
            shutil.copy2(src, dst)
            logger.info(f"Normalized Excel output -> {dst}")
            removed = 0
            for f in excel_files:
                try:
                    os.remove(os.path.join(d, f))
                    removed += 1
                except Exception:
                    pass
            if removed:
                logger.info(f"Removed {removed} dated EasyBrokers Excel file(s) from {d}")
        except Exception as e:  # pragma: no cover
            logger.error(f"Failed normalizing Excel filename in {d}: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='EasyBroker export pipeline')
    parser.add_argument('--only-if-stale', action='store_true', help='Update JSON only if the remote record is newer than local JSON')
    parser.add_argument('--max-workers', type=int, default=10, help='Max worker threads for downloads')
    args = parser.parse_args()

    cfg_path = paths.PROJECT_ROOT / 'config.json'
    if not cfg_path.exists():
        logger.error('config.json not found (expected at project root)')
        raise SystemExit(1)
    with open(cfg_path, 'r', encoding='utf-8') as cf:
        cfg = json.load(cf)

    api_key = cfg.get('EASYBROKER_API_KEY')
    endpoints = cfg.get('ENDPOINTS', {})
    base_json_folder = str(paths.DATA_DIR)
    images_folder = str(paths.IMAGES_DIR)

    if not api_key or not isinstance(endpoints, dict) or not endpoints.get('properties') or not endpoints.get('listing_statuses'):
        logger.error('Required config keys missing: EASYBROKER_API_KEY, ENDPOINTS.properties, ENDPOINTS.listing_statuses')
        raise SystemExit(1)

    pj = PropertyJsonDownloader(api_key, endpoints['properties'], base_json_folder, max_workers=args.max_workers, only_if_stale=args.only_if_stale)
    pj.download_all()

    pi = PropertyImageDownloader(base_json_folder, images_folder, max_workers=args.max_workers)
    pi.download_all()

    ls = ListingStatusDownloader(api_key, endpoints['listing_statuses'], os.path.join(base_json_folder, 'listing'))
    ls.download()

    _normalize_easybrokers_excel(str(paths.DATA_DIR))
    js = pj.stats
    is_ = pi.stats
    logger.info(f"JSON -> saved: {js['saved']}, updated: {js['updated']}, skipped: {js['skipped']}, errors: {js['errors']}")
    logger.info(f"Images -> downloaded: {is_['downloaded']}, skipped: {is_['skipped']}, errors: {is_['errors']}")
