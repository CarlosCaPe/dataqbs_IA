# Changelog

All notable changes to this repository are documented here. Dates are in YYYY-MM-DD.

## v0.3.0 — 2025-09-18

This release focuses on reliability for the Email Collector (Hotmail/Outlook IMAP), clearer logs, and a small quality-of-life update to the EasyBrokers tools.

Highlights
- Email Collector: Hotmail/Outlook IMAP OAuth device-code support with clearer error messages and safer folder selection (handles Junk/Spam variants more robustly).
- Configuration: Wider Hotmail folder include list; tightened spam heuristics; expanded Spanish transactional short allowlist; disabled domain subfolders so exports are organized by category only.
- Logging: Unified file logging for collectors and utilities under emails_out/logs/.
- Realstate tools: Structured logging to console and file; improved image downloader; declared dependencies (requests, openpyxl) and added lockfile.
- Developer experience: VS Code tasks to install deps and run both projects; docs updated.

Changes by area
- Email Collector
  - Add file logging to emails_out/logs/email_collector.log in addition to console output.
  - Harden OAuth device flow for Hotmail/Outlook (clearer errors, instructions, and token handling).
  - Improve folder selection (INBOX, Junk Email, Junk, Junk E-mail, Spam) with quoting and fuzzy matching fallbacks.
  - Config tweaks: keep Spanish validation, tune allowlist/keywords, and disable domain subfolders in output.
- Realstate
  - Add logging to file at realstate/logs/realstate_export.log.
  - Improve image downloader diagnostics and safety; sanitize filenames.
  - Add requests and openpyxl to pyproject; include poetry.lock for reproducible installs.
- Utilities & Docs
  - extract_domains.py and migrate_suspicious.py now log to emails_out/logs/.
  - Root README and project READMEs document tasks and .env quick-start.

Links
- Tag: https://github.com/CarlosCaPe/dataqbs_IA/tree/v0.3.0
