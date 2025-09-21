import os
import json
import requests
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("realstate")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)


class RealstateImageDownloader:
    def __init__(self, api_key, base_json_folder, max_workers):
        self.api_key = api_key
        self.base_json_folder = base_json_folder
        self.max_workers = max_workers
        self.headers = {
            "accept": "application/json",
            "X-Authorization": self.api_key
        }

    def download_image(self, image_url, save_path):
        # Skip if the file already exists
        if os.path.exists(save_path):
            logger.info(f"Skipping existing image: {save_path}")
            return
        try:
            response = requests.get(image_url, headers=self.headers, stream=True)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Image downloaded: {save_path}")
        except Exception as e:
            logger.error(f"Failed to download image {image_url}: {e}")

    def sanitize_file_name(self, file_name):
        """Remove invalid characters and query parameters from file name."""
        file_name = file_name.split('?')[0]  # Remove query parameters
        return file_name.replace(':', '').replace('/', '').replace('\\', '').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')

    def download_property_images(self, property_data):
        property_id = property_data['property_id']
        images = property_data['images']
        property_folder = os.path.join(self.base_json_folder, "images", property_id)
        os.makedirs(property_folder, exist_ok=True)

        for image_url in images:
            image_name = self.sanitize_file_name(os.path.basename(image_url))
            save_path = os.path.join(property_folder, image_name)
            self.download_image(image_url, save_path)

    def download_all_property_images(self, properties):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            executor.map(self.download_property_images, properties)
