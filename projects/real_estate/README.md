# Realstate Tools

Small helper scripts to process real estate data.

- Configure: edit `config.json`.
- Run: `poetry run python test_download.py`.
- Logs: `realstate/logs/realstate_export.log`.

## Búsquedas exactas por requerimiento

Este proyecto trae un buscador que filtra *estrictamente* por parámetros usando los JSON ya descargados.

- Edita los perfiles en `requirements.json`.
- Asegúrate que `BASE_JSON_FOLDER` en `config.json` apunte al folder con `*.json` (por defecto: `easybrokers/properties/data`).

### Ejecutar

- Bodega chica:
	- `poetry run real-estate-search --profile bodega_chica`

- Bodega grande:
	- `poetry run real-estate-search --profile bodega_grande`

- Bodega gym 12x16:
	- `poetry run real-estate-search --profile bodega_gym_12x16`

- Terreno bardeado (cerca Centro Sur / Mariano Otero):
	- `poetry run real-estate-search --profile terreno_bardeado_centro_sur`

Tips:
- Agrega `--explain` si quieres ver por qué *no* pasa un filtro.
- Agrega `--top-misses 10` para ver los "casi" (los que fallan menos reglas).
- La regla de altura para bodegas puede exigir altura del portón ("incluido el portón") si el perfil lo pide.
