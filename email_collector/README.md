# email_collector

Proyecto para colección y clasificación de correos IMAP con exportación .eml.

## Instalación

```powershell
cd email_collector
poetry install
```

## Ejecución

```powershell
poetry run email-collect --precheck -v
poetry run email-collect -v
```

Las credenciales se leen desde `../.env` y la configuración desde `../config.yaml`.