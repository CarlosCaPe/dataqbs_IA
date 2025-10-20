import os
import json
import requests
import logging
from concurrent.futures import ThreadPoolExecutor
from . import paths

logger = logging.getLogger("real_estate")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(_h)
    try:
        paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(paths.LOGS_DIR / 'image_downloader.log', encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)
    except Exception:  # pragma: no cover
        pass
logger.setLevel(logging.INFO)


class RealEstateImageDownloader:
    def __init__(self, api_key: str, base_json_folder: str, max_workers: int):
        self.api_key = api_key
        self.base_json_folder = base_json_folder
        self.max_workers = max_workers
        self.headers = {
            "accept": "application/json",
            "X-Authorization": self.api_key
        }

    def download_image(self, image_url: str, save_path: str) -> None:
        if os.path.exists(save_path):
            logger.info(f"Skipping existing image: {save_path}")
            return
        try:
            response = requests.get(image_url, headers=self.headers, stream=True, timeout=20)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Image downloaded: {save_path}")
        except Exception as e:  # pragma: no cover
            logger.error(f"Failed to download image {image_url}: {e}")

    @staticmethod
    def sanitize_file_name(file_name: str) -> str:
        file_name = file_name.split('?')[0]
        return file_name.replace(':', '').replace('/', '').replace('\\', '').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')

    def download_property_images(self, property_data: dict) -> None:
        property_id = property_data.get('property_id') or property_data.get('id')
        if not property_id:
            return
        images = property_data.get('images') or []
        property_folder = os.path.join(self.base_json_folder, "images", property_id)
        os.makedirs(property_folder, exist_ok=True)
        for image_url in images:
            image_name = self.sanitize_file_name(os.path.basename(image_url))
            save_path = os.path.join(property_folder, image_name)
            self.download_image(image_url, save_path)

    def download_all_property_images(self, properties: list[dict]) -> None:
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            list(executor.map(self.download_property_images, properties))
