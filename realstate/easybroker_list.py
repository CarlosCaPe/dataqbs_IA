import os
import json
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup basic logger
logger = logging.getLogger("easybroker")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(h)
    try:
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        fh = logging.FileHandler(os.path.join(log_dir, 'easybroker_export.log'), encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)
    except Exception:
        pass


class PropertyJsonDownloader:
    def __init__(self, api_key, properties_url, base_json_folder, max_workers=10):
        self.api_key = api_key
        self.properties_url = properties_url
        self.base_json_folder = base_json_folder
        self.max_workers = max_workers
        os.makedirs(self.base_json_folder, exist_ok=True)

    def _save_one(self, rec):
        public_id = rec.get('public_id') or rec.get('id')
        if not public_id:
            return
        path = os.path.join(self.base_json_folder, f"{public_id}.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved JSON for {public_id}")
        except Exception as e:
            logger.error(f"Error saving {public_id}: {e}")

    def download_all(self):
        logger.info(f"Fetching properties from {self.properties_url}")
        page = 1
        futures = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            while True:
                url = f"{self.properties_url}?page={page}&limit=50"
                try:
                    resp = requests.get(url, headers={"accept": "application/json", "X-Authorization": self.api_key}, timeout=10)
                except Exception as e:
                    logger.error(f"Request error for page {page}: {e}")
                    break
                if resp.status_code != 200:
                    logger.warning(f"Non-200 response fetching properties: {resp.status_code}")
                    break
                data = resp.json()
                records = data.get('content', data) if isinstance(data, dict) else data
                if not records:
                    break
                for rec in records:
                    futures.append(ex.submit(self._save_one, rec))
                # pagination
                next_page = data.get('pagination', {}).get('next_page') if isinstance(data, dict) else None
                if not next_page:
                    break
                page += 1
            for f in as_completed(futures):
                pass
        logger.info('Finished downloading JSONs')


class PropertyImageDownloader:
    def __init__(self, base_json_folder, images_folder, max_workers=10):
        self.base_json_folder = base_json_folder
        self.images_folder = images_folder
        self.max_workers = max_workers
        os.makedirs(self.images_folder, exist_ok=True)

    def _download_for_file(self, filename):
        src = os.path.join(self.base_json_folder, filename)
        try:
            with open(src, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")
            return
        prop_id = data.get('public_id') or data.get('id') or os.path.splitext(filename)[0]
        urls = []
        if isinstance(data.get('images'), list):
            for img in data['images']:
                if isinstance(img, dict) and img.get('url'):
                    urls.append(img['url'])
                elif isinstance(img, str):
                    urls.append(img)
        if data.get('title_image_full'):
            urls.append(data.get('title_image_full'))
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
                    continue
                r = requests.get(url, stream=True, timeout=8)
                if r.status_code == 200:
                    with open(out_path, 'wb') as wf:
                        for chunk in r.iter_content(8192):
                            if chunk:
                                wf.write(chunk)
                    logger.info(f"Downloaded {fname} for {prop_id}")
                else:
                    logger.warning(f"Image request for {url} returned {r.status_code}")
            except Exception as e:
                logger.error(f"Error downloading image {url} for {prop_id}: {e}")

    def download_all(self):
        logger.info('Starting image downloads')
        files = [f for f in os.listdir(self.base_json_folder) if f.endswith('.json')]
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = [ex.submit(self._download_for_file, fn) for fn in files]
            for f in as_completed(futures):
                pass
        logger.info('Finished image downloads')


class ListingStatusDownloader:
    def __init__(self, api_key, listing_statuses_url, output_folder):
        self.api_key = api_key
        self.url = listing_statuses_url
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)

    def download(self):
        logger.info(f"Fetching listing statuses from {self.url}")
        all_items = []
        url = self.url
        while url:
            try:
                r = requests.get(url, headers={"accept": "application/json", "X-Authorization": self.api_key}, timeout=10)
            except Exception as e:
                logger.error(f"Request error fetching listing statuses: {e}")
                break
            if r.status_code != 200:
                logger.warning(f"Non-200 from listing statuses endpoint: {r.status_code}")
                break
            data = r.json()
            items = data.get('content', data) if isinstance(data, dict) else data
            all_items.extend(items)
            url = data.get('pagination', {}).get('next_page') if isinstance(data, dict) else None
        out = os.path.join(self.output_folder, 'listing_statuses.json')
        try:
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(all_items, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved listing statuses to {out}")
        except Exception as e:
            logger.error(f"Failed saving listing statuses: {e}")


if __name__ == '__main__':
    # Load config.json
    cfg_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.exists(cfg_path):
        logger.error('config.json not found in script folder')
        raise SystemExit(1)
    with open(cfg_path, 'r', encoding='utf-8') as cf:
        cfg = json.load(cf)

    api_key = cfg.get('EASYBROKER_API_KEY')
    endpoints = cfg.get('ENDPOINTS', {})
    base_json_folder = cfg.get('BASE_JSON_FOLDER', 'properties/data')
    images_folder = os.path.join(base_json_folder, 'images')

    if not api_key or 'properties' not in endpoints or 'listing_statuses' not in endpoints:
        logger.error('Required config keys missing: EASYBROKER_API_KEY, ENDPOINTS.properties, ENDPOINTS.listing_statuses')
        raise SystemExit(1)

    pj = PropertyJsonDownloader(api_key, endpoints['properties'], base_json_folder, max_workers=10)
    pj.download_all()

    pi = PropertyImageDownloader(base_json_folder, images_folder, max_workers=10)
    pi.download_all()

    ls = ListingStatusDownloader(api_key, endpoints['listing_statuses'], os.path.join(base_json_folder, 'listing'))
    ls.download()



import os
import json
import datetime
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize logger
logger = logging.getLogger("easybroker")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
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
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab

    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

# --- Config Loader ---
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass  # Suprime errores en la lectura
    if 'LOG_FOLDER' in config:
        os.makedirs(config['LOG_FOLDER'], exist_ok=True)
    return EasyBrokerConfig(config)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Main Workflow Steps ---
def download_jsons(exporter):
    logger.info("Starting JSON download process.")
    properties = exporter.get_properties(excel_filename)
    exporter.save_property_jsons(properties, max_workers=exporter.max_workers)
    logger.info("Completed JSON download process.")

def create_easybrokers_files(exporter):
    logger.info("Creating Easybrokers Excel files.")
    excel_filename = exporter.fetch_endpoints_to_excel()
    logger.info(f"Easybrokers Excel file created: {excel_filename}")
    return excel_filename

def format_easybrokers_files(exporter, excel_filename):
    logger.info("Formatting Easybrokers Excel files.")
    wb = openpyxl.load_workbook(excel_filename)

    # Clean and style "properties" tab
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        exporter.cleaner.format_operations_column(ws)
        headers = [cell.value for cell in ws[1]]
        # Elimina columna "title_image_thumb" si existe
        if "title_image_thumb" in headers:
            thumb_col_idx = headers.index("title_image_thumb") + 1
            ws.delete_cols(thumb_col_idx)
            headers = [cell.value for cell in ws[1]]

    # Aplica SAP style a todas las pestañas y habilita filtros en row1
    exporter.styler.apply(wb)

    # Reemplaza el valor en "title_image_full" con el "public_url" obtenido de cada JSON
    if exporter.tab_names['properties'] in wb.sheetnames:
        ws = wb[exporter.tab_names['properties']]
        headers = [cell.value for cell in ws[1]]
        if "title_image_full" in headers:
            image_full_col_idx = headers.index("title_image_full")
            public_id_col_idx = headers.index(exporter.col_indices['public_id_column_name'])
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                public_id = row[public_id_col_idx].value
                json_path = os.path.join(exporter.base_json_folder, f"{public_id}.json")
                public_url = None
                if public_id and os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            public_url = data.get("public_url")
                    except Exception as e:
                        logger.warning(f"Error reading JSON for {public_id}: {e}")
                target_cell = row[image_full_col_idx]
                if public_url and isinstance(public_url, str):
                    # Reemplaza el valor por la URL y crea el hipervínculo
                    exporter.hyperlink_helper.set_hyperlink(target_cell, public_url, display=public_url)
                else:
                    target_cell.value = ''
        # Vuelve a habilitar filtro sobre la fila 1 (por si se perdió)
        ws.auto_filter.ref = ws.dimensions

    # Elimina la pestaña "Property Types" si existe y hay más de una pestaña
    if 'Property Types' in wb.sheetnames and len(wb.sheetnames) > 1:
        del wb['Property Types']

    wb.save(excel_filename)
    logger.info("Completed formatting of Easybrokers Excel files.")

def download_images():
    logger.info("Starting image download process.")
    from test_download import downloader
    properties = []
    json_folder = config.base_json_folder
    json_dir = os.path.abspath(json_folder)
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
                    properties.append({'property_id': property_id, 'images': images})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    if not properties:
        logger.warning("No properties with images found for download.")
    else:
        downloader.download_all_property_images(properties)
        logger.info(f"Image download completed for {len(properties)} properties.")
    logger.info("Completed image download process.")

def upsert_data_into_wiggot():
    logger.info("Starting upsert process for Wiggot data.")
    wiggot_file = os.path.join(config.excel_folder, "wiggot.xlsx")

    # Dynamically locate the latest easybrokers file
    easybrokers_files = [f for f in os.listdir(config.excel_folder) if f.startswith("easybrokers_") and f.endswith(".xlsx")]
    if not easybrokers_files:
        logger.error("No Easybrokers file found in the directory.")
        return

    easybrokers_file = os.path.join(config.excel_folder, max(easybrokers_files))

    try:
        wiggot_wb = load_workbook(wiggot_file)
        easybrokers_wb = load_workbook(easybrokers_file)

        wiggot_sheet = wiggot_wb.active
        easybrokers_sheet = easybrokers_wb.active

        wiggot_data = {row[0].value: row for row in wiggot_sheet.iter_rows(min_row=2)}
        for row in easybrokers_sheet.iter_rows(min_row=2):
            property_id = row[0].value
            if property_id not in wiggot_data:
                # Ensure all records are mapped correctly
                wiggot_sheet.append([cell.value for cell in row])

        wiggot_wb.save(wiggot_file)
        logger.info("Wiggot file successfully updated.")
    except Exception as e:
        logger.error(f"Error during Wiggot file upsertion: {e}")
    logger.info("Completed upsert process for Wiggot data.")

