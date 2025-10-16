import argparse
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from . import paths

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # ImportError or others
    def load_dotenv(*args, **kwargs):
        return False


def _try_click_email_login_toggle(ctx) -> None:
    for toggle in [
        "button:has-text('Correo')",
        "button:has-text('Email')",
        "text=Entrar con correo",
        "text=Iniciar sesión con correo",
        "text=Usar correo",
        "text=Continuar con correo",
    ]:
        try:
            ctx.click(toggle, timeout=1500)
            break
        except Exception:
            pass


def _try_fill_email(ctx, email: str) -> bool:
    for sel in [
        "input[type=email]",
        "input[name=email]",
        "input[id*=email]",
        "input[autocomplete=email]",
    ]:
        try:
            ctx.wait_for_selector(sel, timeout=4000)
            ctx.fill(sel, email)
            return True
        except Exception:
            continue
    for placeholder in ["Correo", "Correo electrónico", "Email", "Email address"]:
        try:
            ctx.get_by_placeholder(placeholder, exact=False).fill(email)
            return True
        except Exception:
            continue
    try:
        ctx.get_by_role("textbox").fill(email)
        return True
    except Exception:
        pass
    return False


def _try_fill_password(ctx, password: str) -> bool:
    for sel in [
        "input[type=password]",
        "input[name=password]",
        "input[id*=pass]",
        "input[autocomplete=current-password]",
    ]:
        try:
            ctx.wait_for_selector(sel, timeout=4000)
            ctx.fill(sel, password)
            return True
        except Exception:
            continue
    for placeholder in ["Contraseña", "Password", "Tu contraseña"]:
        try:
            ctx.get_by_placeholder(placeholder, exact=False).fill(password)
            return True
        except Exception:
            continue
    try:
        ctx.get_by_role("textbox").nth(1).fill(password)
        return True
    except Exception:
        pass
    return False


def _click_login_submit(ctx) -> None:
    for selector in [
        "button:has-text('Iniciar sesión')",
        "button:has-text('Ingresar')",
        "button:has-text('Acceder')",
        "button:has-text('Sign in')",
        "button[type=submit]",
        "[role=button]:has-text('Iniciar')",
    ]:
        try:
            ctx.click(selector, timeout=2000)
            return
        except Exception:
            continue
    try:
        ctx.keyboard.press("Enter")
    except Exception:
        pass


def _attempt_export_download(page, per_attempt_timeout_ms: int = 30000):
    selectors = [
        "button:has-text('Exportar')",
        "[role=button]:has-text('Exportar')",
        "text=Exportar",
        "[data-testid*=export]",
        "[aria-label*=Export]",
        "[title*=Export]",
    ]
    for sel in selectors:
        try:
            with page.expect_download(timeout=per_attempt_timeout_ms) as download_info:
                page.click(sel, timeout=4000)
            return download_info.value
        except Exception:
            continue
    menu_triggers = [
        "button[aria-haspopup]",
        "[role=button][aria-expanded]",
        "button:has([class*='menu'])",
        "[aria-label*='Más']",
        "[aria-label*='More']",
    ]
    menu_items = [
        "text=Exportar",
        "text=Export",
        "[role=menuitem]:has-text('Export')",
        "[role=menuitem]:has-text('Exportar')",
    ]
    for trigger in menu_triggers:
        try:
            page.click(trigger, timeout=2000)
            for item in menu_items:
                try:
                    with page.expect_download(timeout=per_attempt_timeout_ms) as download_info:
                        page.click(item, timeout=3000)
                    return download_info.value
                except Exception:
                    continue
        except Exception:
            continue
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        for sel in selectors:
            try:
                with page.expect_download(timeout=per_attempt_timeout_ms) as download_info:
                    frame.click(sel, timeout=4000)
                return download_info.value
            except Exception:
                continue
    raise RuntimeError("Couldn't find or trigger the 'Exportar' control.")


def _wait_for_excel_response(page, timeout_ms: int = 30000):
    def is_excel(resp):
        try:
            ct = (resp.headers.get('content-type') or '').lower()
            cd = (resp.headers.get('content-disposition') or '').lower()
            url = resp.url.lower()
            if 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in ct:
                return True
            if 'application/vnd.ms-excel' in ct:
                return True
            if 'application/octet-stream' in ct and ('filename=' in cd or url.endswith('.xlsx') or url.endswith('.xls')):
                return True
            if 'text/csv' in ct and ('export' in url or 'download' in url):
                return True
        except Exception:
            pass
        return False
    resp = page.wait_for_event(
        "response",
        predicate=is_excel,
        timeout=timeout_ms,
    )
    return resp


def _download_loop(page, download_dir: Path, max_attempts: int = 3) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            dl = _attempt_export_download(page)
            path = dl.path()
            if path is None:
                raise RuntimeError("Download path is None")
            final_path = download_dir / dl.suggested_filename
            os.replace(path, final_path)
            return final_path
        except Exception as e:  # pragma: no cover
            last_error = e
            time.sleep(1)
    if last_error:
        raise last_error
    raise RuntimeError("Download attempts exhausted without explicit error")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Automate Wiggot export via Playwright")
    parser.add_argument("--email", help="Login email (or set WIGGOT_EMAIL)")
    parser.add_argument("--password", help="Login password (or set WIGGOT_PASSWORD)")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--out-dir", default=str(paths.DATA_DIR), help="Directory to place exported file")
    parser.add_argument("--max-attempts", type=int, default=3, help="Attempts to click Export")
    args = parser.parse_args(argv)

    load_dotenv()
    email = args.email or os.getenv("WIGGOT_EMAIL")
    password = args.password or os.getenv("WIGGOT_PASSWORD")
    if not email or not password:
        print("Missing credentials (provide --email/--password or env vars)", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.goto("https://app.wiggot.com/", timeout=60000)
        _try_click_email_login_toggle(page)
        if not _try_fill_email(page, email):
            print("Could not find email field", file=sys.stderr)
            return 3
        if not _try_fill_password(page, password):
            print("Could not find password field", file=sys.stderr)
            return 4
        _click_login_submit(page)
        try:
            page.wait_for_load_state("networkidle", timeout=60000)
        except PlaywrightTimeoutError:  # pragma: no cover
            pass

        try:
            download_path = _download_loop(page, out_dir, max_attempts=args.max_attempts)
            print(f"Downloaded export -> {download_path}")
        finally:
            browser.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
