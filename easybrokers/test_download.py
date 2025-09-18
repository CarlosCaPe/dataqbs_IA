import json
import os
from image_downloader import EasyBrokerImageDownloader

# Cargar config
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

downloader = EasyBrokerImageDownloader(
    api_key=config['EASYBROKER_API_KEY'],
    base_json_folder=config['BASE_JSON_FOLDER'],
    max_workers=config['MAX_WORKERS']
)

# Leer todos los archivos JSON de la carpeta de propiedades
properties = []
json_folder = config['BASE_JSON_FOLDER']
json_dir = os.path.abspath(json_folder)
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
            print(f'Error leyendo {file_path}: {e}')

if not properties:
    print('No se encontraron propiedades con imágenes para descargar.')
else:
    downloader.download_all_property_images(properties)
    print(f'Descarga finalizada para {len(properties)} propiedades.')
