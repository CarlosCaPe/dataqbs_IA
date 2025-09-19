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

# Cargar config
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

downloader = RealstateImageDownloader(
    api_key=config['EASYBROKER_API_KEY'],
    base_json_folder=config['BASE_JSON_FOLDER'],
    max_workers=config.get('MAX_WORKERS', 8)
)

# Leer todos los archivos JSON de la carpeta de propiedades
properties = []
json_folder = config['BASE_JSON_FOLDER']
json_dir = os.path.abspath(json_folder)
logger.info('Starting image download discovery in %s', json_dir)
for filename in os.listdir(json_dir):
    if filename.endswith('.json'):
        file_path = os.path.join(json_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            property_id = data.get('property_id') or data.get('id') or os.path.splitext(filename)[0]
            # Buscar imágenes en campos comunes
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
                properties.append({'property_id': property_id, 'images': images})
        except Exception as e:
            logger.error('Error leyendo %s: %s', file_path, e)

if not properties:
    logger.warning('No se encontraron propiedades con imágenes para descargar.')
else:
    logger.info('Descargando imágenes para %d propiedades...', len(properties))
    downloader.download_all_property_images(properties)
    logger.info('Descarga finalizada para %d propiedades.', len(properties))
