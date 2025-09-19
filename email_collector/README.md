# email_collector

IMAP email collection and classification with .eml export.

## Installation

```powershell
cd email_collector
poetry install
```

## Quick setup (.env)

Create a `.env` at the repo root (not inside `email_collector`) with, at minimum:

```
HOTMAIL_USER=your_account@outlook.com
HOTMAIL_AUTH=oauth
MSAL_CLIENT_ID=00000000-0000-0000-0000-000000000000
# MSAL_TENANT=consumers
```

See `email_collector/.env.example` for a more complete example.

## Running

```powershell
poetry run email-collect --precheck -v
poetry run email-collect -v
```

Credentials are read from `../.env` and configuration from `../config.yaml`.

You can also use VS Code Tasks (Terminal > Run Task):
- Email Collector: Install deps
- Precheck run
- Email Collector: Full run