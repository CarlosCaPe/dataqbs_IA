# dataqbs_IA

This repository contains two Python projects in a single workspace:

- email_collector: IMAP email collection and classification with .eml export.
- easybrokers: Utilities and scripts to handle EasyBrokers data.

See also: CHANGELOG.md for English release notes, visible to external collaborators/recruiters.

## Environment setup

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

## Usage (email_collector)

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
- EasyBrokers logs to `easybrokers/logs/easybroker_export.log`.
- Utility scripts in the repo root write logs to `emails_out/logs/*.log`.

Increase verbosity with `-v/--verbose` (Email Collector) or set `LOGLEVEL=DEBUG`.

## Notes
- Gmail typically requires an App Password if 2FA is enabled.
- Hotmail/Outlook uses `outlook.office365.com` with IMAPS (993).

---

## Usage (easybrokers)

Enter the `easybrokers` folder and use Poetry to install dependencies and run scripts:

```powershell
cd easybrokers
poetry install
poetry run python test_download.py
```

You can also use VS Code tasks and debug configurations:

- Tasks (Terminal > Run Task):
  - Email Collector: Install deps
  - Precheck run
  - Email Collector: Full run
  - EasyBrokers: Install deps
  - EasyBrokers: Run test_download.py

- Debug (Run and Debug):
  - Email Collector (precheck)
  - Email Collector (run)
  - EasyBrokers: test_download.py
  - EasyBrokers: image_downloader.py

Tip: Open `dataqbs_IA.code-workspace` to load both projects as folders in one workspace.

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
