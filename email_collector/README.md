# email_collector

Proyecto para colección y clasificación de correos IMAP con exportación .eml.

## Instalación

```powershell
cd email_collector
poetry install
```

## Configuración rápida (.env)

Coloca un archivo `.env` en la raíz del repo (no dentro de email_collector) con al menos:

```
HOTMAIL_USER=you@hotmail.com
HOTMAIL_AUTH=oauth
MSAL_CLIENT_ID=00000000-0000-0000-0000-000000000000
# MSAL_TENANT=consumers
```

Revisa `email_collector/.env.example` para un ejemplo completo.

## Ejecución

```powershell
poetry run email-collect --precheck -v
poetry run email-collect -v
```

Las credenciales se leen desde `../.env` y la configuración desde `../config.yaml`.

También puedes usar las tareas de VS Code (Terminal > Run Task):
- Email Collector: Install deps
- Precheck run
- Email Collector: Full run