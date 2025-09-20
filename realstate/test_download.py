import json
import os
import logging
from pathlib import Path
from image_downloader import RealstateImageDownloader

logger = logging.getLogger("realstate")
if not logger.handlers:
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(sh)
logger.setLevel(logging.INFO)

# also log to file under properties/logs
try:
    log_dir = Path(__file__).resolve().parent / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / 'realstate_export.log', encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)
except Exception:
    pass

"""Simple driver script to download images for properties discovered in JSON files.

Reads configuration from config.json. For backwards-compatibility, it accepts
either REALSTATE_API_KEY or EASYBROKER_API_KEY in the config file.
"""

# Load config
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Accept REALSTATE_API_KEY or fallback to EASYBROKER_API_KEY
api_key = config.get('REALSTATE_API_KEY') or config.get('EASYBROKER_API_KEY')
if not api_key:
    raise KeyError("Missing REALSTATE_API_KEY or EASYBROKER_API_KEY in config.json")

downloader = RealstateImageDownloader(
    api_key=api_key,
    base_json_folder=config['BASE_JSON_FOLDER'],
    max_workers=config.get('MAX_WORKERS', 8)
)

json_folder = config['BASE_JSON_FOLDER']
json_dir = os.path.abspath(json_folder)
images_root = os.path.join(json_folder, "images")
logger.info('Starting image download discovery in %s', json_dir)

properties_to_download = []
skipped = 0
total = 0

for filename in os.listdir(json_dir):
    if filename.endswith('.json'):
        file_path = os.path.join(json_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            property_id = data.get('property_id') or data.get('id') or os.path.splitext(filename)[0]
            images = []
            if 'images' in data and isinstance(data['images'], list):
                for img in data['images']:
                    if isinstance(img, dict) and 'url' in img:
                        images.append(img['url'])
                    elif isinstance(img, str):
                        images.append(img)
            elif 'photos' in data and isinstance(data['photos'], list):
                for img in data['photos']:
                    if isinstance(img, dict) and 'url' in img:
                        images.append(img['url'])
                    elif isinstance(img, str):
                        images.append(img)
            if property_id and images:
                total += 1
                property_img_dir = os.path.join(images_root, property_id)
                # If folder exists and has at least one image, skip
                if os.path.isdir(property_img_dir) and any(os.listdir(property_img_dir)):
                    logger.info(f"Skipping {property_id}: images already exist.")
                    skipped += 1
                else:
                    properties_to_download.append({'property_id': property_id, 'images': images})
        except Exception as e:
            logger.error('Error reading %s: %s', file_path, e)

if not properties_to_download:
    logger.info(f"No new properties to download. {skipped} already had images.")
else:
    logger.info(f"Downloading images for {len(properties_to_download)} properties (skipped {skipped} of {total})...")
    downloader.download_all_property_images(properties_to_download)
    logger.info(f"Finished download for {len(properties_to_download)} properties.")
    logger.info('Finished download for %d properties.', len(properties))
