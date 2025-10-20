# Artifacts Directory

This directory centralizes runtime, generated, or large data assets per project.

## Layout
- `email_collector/`
  - `outputs/`  Downloaded and classified emails (was `projects/email_collector/emails_out`)
- `telus_compara_audios/`
  - `outputs/`  Collected run outputs (was `runs/` and `emails_out/`)
  - `logs/`     Execution logs (was `projects/telus_compara_audios/logs`)
  - `user_data/` Browser/session data (ignored in git; retained locally)
- `telus_compara_imagenes/`
  - `user_data/` Browser/session data (ignored)
- `real_estate/`
  - `data/`      Property JSON/Excel exports (was under `properties/data`)
  - `images/`    Images, Canvas, TikTok assets (was under `properties/images`, `Canvas/`, `TikTok/`)
  - `screenshots/` Debug UI screenshots
  - `logs/`      Aggregated logs (project & nested easybrokers logs)

## Conventions
1. Source code must not import directly from artifacts paths; instead provide a small `paths.py` (upcoming) that computes locations.
2. Large binary or user-specific session data stays ignored by git.
3. Temporary or cache data should go under a subfolder named `tmp/` inside the project’s artifact tree.
4. Do not store secrets here (.env stays at project root, not committed).

## Git Ignore
The root `.gitignore` ignores `artifacts/**` except for this README and `.gitkeep` files to retain structure.

