# dataqbs_IA Monorepo

Multi‑project workspace containing AI/data-engineering tools, portfolio website, crypto arbitrage, and automation utilities.

## Project Index

| Project | Path | Stack | Purpose |
|---------|------|-------|---------|
| **dataqbs.com** | `projects/dataqbs_site` | Astro + Svelte, Tailwind, Cloudflare Pages | Portfolio site with RAG chatbot |
| **Arbitraje** | `projects/arbitraje` | Python, ccxt, pandas | Multi-exchange crypto arbitrage scanner + swap executor |
| Email Collector | `projects/email_collector` | Python, IMAP | Email ingestion, validation & classification |
| OAI Code Evaluator | `projects/oai_code_evaluator` | Python, YAML rules | LLM response auditing with 5-dimension scoring |
| Real Estate Tools | `projects/real_estate` | Python, Playwright | Scraping / export (EasyBroker, Wiggot) |
| Supplier Verifier | `projects/supplier_verifier` | Python | Supplier data verification |
| Audio Compare | `projects/tls_compara_audios` | Python, Playwright | Automated A/B audio quality comparison |
| Image Compare | `projects/tls_compara_imagenes` | Python, Playwright | Side-by-side image comparison |
| Linux Setup | `projects/linux` | Bash | Windows → Linux migration scripts |

Shared assets:
- `rules/email/` → domain rule definitions (email heuristics, summaries)
- `tools/` → operational & maintenance scripts grouped by domain
- `artifacts/` → generated outputs (ignored by git)
- `docs/` → architecture and process documentation

See `docs/monorepo.md` for structure rationale and conventions.

## Environment Setup (Email Collector)

1) Create a `.env` file at the repository root (not committed) with your credentials. Example placeholders below—replace with your own values; do not commit secrets:

```
# === GMAIL account #1 ===
GMAIL1_USER=user1@example.com
GMAIL1_PASS=APP_PASSWORD_GMAIL1

# === HOTMAIL / OUTLOOK account ===
HOTMAIL_USER=user1@outlook.com
HOTMAIL_PASS=YOUR_PASSWORD_OR_APP_PASSWORD

# === GMAIL account #2 (optional) ===
GMAIL2_USER=user2@example.com
GMAIL2_PASS=APP_PASSWORD_GMAIL2

# Optional: select default account for email_collector
# EMAIL_ACCOUNT=gmail1
```

2) Adjust `config.yaml` to fine‑tune classification/validation rules. You can override IMAP host/port/folder via environment variables `IMAP_HOST`, `IMAP_PORT`, `IMAP_FOLDER`.

## Usage: Email Collector

From the repo root with Poetry:

```powershell
poetry install
poetry run email-collect --precheck --account gmail1
poetry run email-collect --account hotmail
```

You can also set the account via env var:

```powershell
$env:EMAIL_ACCOUNT = "gmail2"
poetry run email-collect --precheck
```

Results:
- EML files and validation reports (JSON/TXT) are written under the configured output folder (`emails_out` by default).

### Unified logs

- Email Collector logs to `emails_out/logs/email_collector.log` in addition to the console.
- Realstate logs to `realstate/logs/realstate_export.log`.
- Utility scripts in the repo root write logs to `emails_out/logs/*.log`.

Increase verbosity with `-v/--verbose` (Email Collector) or set `LOGLEVEL=DEBUG`.

## Notes
- Gmail typically requires an App Password if 2FA is enabled.
- Hotmail/Outlook uses `outlook.office365.com` with IMAPS (993).

---

## Usage: Real Estate Tools

Enter the `realstate` folder and use Poetry to install dependencies and run scripts:

```powershell
cd realstate
poetry install
poetry run python test_download.py
```

You can also use VS Code tasks and debug configurations:

- Tasks (Terminal > Run Task):
  - Email Collector: Install deps
  - Precheck run
  - Email Collector: Full run
  - Realstate: Install deps
  - Realstate: Run test_download.py

- Debug (Run and Debug):
  - Email Collector (precheck)
  - Email Collector (run)
  - Realstate: test_download.py
  - Realstate: image_downloader.py

Tip: Open `dataqbs_IA.code-workspace` to load all projects.

### OAuth for Hotmail/Outlook (XOAUTH2)

If basic IMAP login fails for Hotmail/Outlook, the project supports OAuth (device code flow via MSAL):

1. Register an app in Entra ID (Azure AD) as a Public client/native.
2. Put the Application (client) ID in your `.env` as `MSAL_CLIENT_ID`.
3. Add the API permission `IMAP.AccessAsUser.All` (URI: `https://outlook.office.com/IMAP.AccessAsUser.All`) and grant it.
4. Optional: set `MSAL_TENANT=consumers` (personal accounts), or use `common`/your tenant.
5. In `.env` set:
   - `HOTMAIL_AUTH=oauth` (or `auto` to try basic then OAuth)
   - `HOTMAIL_USER=your_account@outlook.com`
   - (With OAuth, `HOTMAIL_PASS` is optional.)

On first run, you’ll get a verification URL and user code to authorize the app. A token is cached at `~/.email_collector/msal_hotmail_token.json`.

---

## Development Tooling

Install root tooling (lint + tests + hooks):
```powershell
poetry install
pre-commit install
```

Run evaluator tests:
```powershell
poetry run pytest
```

Lint & format:
```powershell
poetry run ruff check .
poetry run ruff format .
```

## Adding a New Project
See `docs/monorepo.md` – create under `projects/<name>/src/<package>` with its own `pyproject.toml`.

## License
MIT
