import os
import sys
import time
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # ImportError or others
    def load_dotenv(*args, **kwargs):
        return False


def _try_click_email_login_toggle(ctx) -> None:
    # Some sites show SSO buttons first; try to reveal email/password form
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
    # Try common selectors and placeholders
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
    # Last resort: first visible textbox
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
    # Fallback: second textbox
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
    # Press Enter as last resort
    try:
        ctx.keyboard.press("Enter")
    except Exception:
        pass


def _attempt_export_download(page, per_attempt_timeout_ms: int = 30000):
    """
    Try to trigger the Wiggot export and capture the download using several selector strategies.
    Returns the Download object on success, raises on failure.
    """
    selectors = [
        "button:has-text('Exportar')",
        "[role=button]:has-text('Exportar')",
        "text=Exportar",
        "[data-testid*=export]",
        "[aria-label*=Export]",
        "[title*=Export]",
    ]

    # First, attempt direct clicks in the main page
    for sel in selectors:
        try:
            with page.expect_download(timeout=per_attempt_timeout_ms) as download_info:
                page.click(sel, timeout=4000)
            return download_info.value
        except Exception:
            continue

    # Some UIs hide Export behind a menu, try opening common menus first
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

    # Try inside iframes as a last resort
    for frame in page.frames:
        # Skip the main frame, already tried
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
    """
    Wait for a network response that looks like an Excel export. Returns the Response or raises on timeout.
    Uses wait_for_event('response') for broader compatibility across Playwright versions.
    """
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

    # Wait for a response event matching our predicate
    resp = page.wait_for_event(
        "response",
        predicate=lambda r: is_excel(r),
        timeout=timeout_ms,
    )
    return resp


def _wait_for_export_button(ctx, timeout_ms: int = 20000) -> bool:
    """
    Wait until an element that looks like the 'Exportar' button appears.
    Returns True if found, False otherwise.
    """
    candidates = [
        "button:has-text('Exportar')",
        "[role=button]:has-text('Exportar')",
        "text=Exportar",
        "[data-testid*=export]",
        "[aria-label*=Export]",
        "[title*=Export]",
    ]
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        for sel in candidates:
            try:
                ctx.wait_for_selector(sel, timeout=1500)
                return True
            except Exception:
                continue
        try:
            ctx.wait_for_timeout(500)
        except Exception:
            pass
    return False


def export_wiggot_excel(
    email: str,
    password: str,
    out_path: Path,
    *,
    headed: bool = False,
    slow_mo: int = 0,
    manual_login: bool = False,
    manual_export: bool = False,
):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    state_path = out_path.parent / ".auth_wiggot.json"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed, slow_mo=slow_mo)
        context = browser.new_context(
            accept_downloads=True,
            storage_state=str(state_path) if state_path.exists() else None,
        )
        page = context.new_page()

        # 1) Navigate to login
        page.goto("https://new.wiggot.com/auth/login", wait_until="domcontentloaded")

        # 2) Login flow (manual or automated or via saved session)
        allow_auto_login = bool(email) and bool(password) and not manual_login
        if manual_login:
            print("Manual login: complete login in the opened browser…")
            # Poll up to 3 minutes for access to my-properties
            deadline = time.time() + 180
            while time.time() < deadline:
                try:
                    page.goto("https://new.wiggot.com/my-properties", wait_until="domcontentloaded")
                    page.wait_for_selector("text=Exportar", timeout=3000)
                    break
                except Exception:
                    page.wait_for_timeout(1500)
            else:
                page.screenshot(path=str(out_path.parent / "wiggot_manual_login_timeout.png"))
                raise RuntimeError("Manual login timed out. Saved screenshot.")
        elif allow_auto_login:
            _try_click_email_login_toggle(page)

            # Try main page first
            if not _try_fill_email(page, email):
                # Try inside iframes
                filled = False
                for frame in page.frames:
                    try:
                        _try_click_email_login_toggle(frame)
                        if _try_fill_email(frame, email):
                            if not _try_fill_password(frame, password):
                                page.screenshot(path=str(out_path.parent / "wiggot_password_debug.png"))
                                raise RuntimeError("Could not locate password field in iframe. Saved screenshot.")
                            _click_login_submit(frame)
                            filled = True
                            break
                    except Exception:
                        continue
                if not filled:
                    page.screenshot(path=str(out_path.parent / "wiggot_login_debug.png"))
                    raise RuntimeError("Could not locate the email field on Wiggot login page. Saved screenshot.")
            else:
                if not _try_fill_password(page, password):
                    page.screenshot(path=str(out_path.parent / "wiggot_password_debug.png"))
                    raise RuntimeError("Could not locate the password field on Wiggot login page. Saved screenshot.")
                _click_login_submit(page)

            # wait for post-login
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
        else:
            # No creds and not manual. Proceed only if we have saved state.
            if not state_path.exists():
                page.screenshot(path=str(out_path.parent / "wiggot_need_login.png"))
                raise RuntimeError("No credentials and no saved session found. Run once with --manual-login or provide --email/--password.")

        # 3) Go to my-properties
        try:
            page.goto("https://new.wiggot.com/my-properties", wait_until="networkidle")
        except Exception:
            page.wait_for_timeout(1500)
            page.goto("https://new.wiggot.com/my-properties", wait_until="domcontentloaded")

        # 4) Trigger export
        download = None
        if manual_export:
            print("Manual export: click 'Exportar' now – waiting for download…")
            with page.expect_download(timeout=180000) as download_info:
                try:
                    page.wait_for_selector("text=Exportar", timeout=20000)
                except Exception:
                    pass
            download = download_info.value
        else:
            total_deadline = time.time() + 240  # 4 minutes
            last_error = None
            attempt = 1
            while time.time() < total_deadline and download is None:
                print(f"[wiggot] Attempt {attempt}: triggering export…")
                try:
                    # Ensure button present or refresh
                    try:
                        page.wait_for_selector("text=Exportar", timeout=7000)
                    except Exception:
                        try:
                            page.reload(wait_until="networkidle")
                        except Exception:
                            pass

                    # Try normal download event
                    try:
                        download = _attempt_export_download(page, per_attempt_timeout_ms=25000)
                    except Exception as e1:
                        last_error = e1
                        # Try popup flow
                        popup = None
                        try:
                            with context.expect_page(timeout=8000) as popup_info:
                                page.click("text=Exportar", timeout=3000)
                            popup = popup_info.value
                        except Exception:
                            popup = None

                        target = popup if popup else page
                        # Network response fallback
                        try:
                            resp = _wait_for_excel_response(target, timeout_ms=25000)
                            body = resp.body()
                            with open(out_path, "wb") as f:
                                f.write(body)
                            time.sleep(0.5)
                            download = True  # sentinel for network path
                            break
                        except Exception as e2:
                            last_error = e2
                except Exception as e:
                    last_error = e

                # Scroll a bit and retry
                try:
                    page.mouse.wheel(0, 1000)
                    page.wait_for_timeout(600)
                except Exception:
                    pass
                attempt += 1

            if download is None:
                page.screenshot(path=str(out_path.parent / "wiggot_export_button_debug.png"))
                raise RuntimeError(f"Failed to export within timeout. Last error: {last_error}")

        # 5) Save file
        if download is not True:
            # Use native Download object
            try:
                download.save_as(str(out_path))
            except Exception:
                # Fallback if path() is required on some versions
                tmp = download.path()
                if tmp:
                    Path(tmp).replace(out_path)
                else:
                    # As last resort, try suggested name in same folder
                    suggested = download.suggested_filename or "wiggot.xlsx"
                    (out_path.parent / suggested).replace(out_path)

        time.sleep(0.5)

        # Persist auth state
        try:
            context.storage_state(path=str(state_path))
        except Exception:
            pass

        context.close()
        browser.close()

    return out_path


def main():
    # Load env variables from optional .env files (local first, then defaults)
    # This lets users put WIGGOT_EMAIL and WIGGOT_PASSWORD in realstate/.env
    env_local = Path(__file__).parent / ".env"
    if env_local.exists():
        try:
            load_dotenv(dotenv_path=env_local, override=False)
        except Exception:
            pass
    else:
        # Fallback to any project-level .env if present
        try:
            load_dotenv(override=False)
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Download Wiggot 'Exportar' Excel via headless browser")
    parser.add_argument("--email", default=os.getenv("WIGGOT_EMAIL"), help="Wiggot email (or set WIGGOT_EMAIL)")
    parser.add_argument("--password", default=os.getenv("WIGGOT_PASSWORD"), help="Wiggot password (or set WIGGOT_PASSWORD)")
    parser.add_argument("--headed", action="store_true", help="Run browser headed for debugging")
    parser.add_argument("--slow-mo", type=int, default=int(os.getenv("WIGGOT_SLOWMO", "0")), help="Slow motion in ms")
    parser.add_argument("--manual-login", action="store_true", help="Skip automated login and let user sign in manually (headed recommended)")
    parser.add_argument("--manual-export", action="store_true", help="Do not click Exportar automatically; you will click it and we will capture the download")
    parser.add_argument("--total-timeout", type=int, default=int(os.getenv("WIGGOT_TOTAL_TIMEOUT", "240")), help="Overall timeout in seconds before failing (default 240s)")
    parser.add_argument(
        "--out",
        default=str(Path(__file__).parent / "properties" / "wiggot.xlsx"),
        help="Output Excel path (default: realstate/properties/wiggot.xlsx)",
    )
    args = parser.parse_args()

    # If no credentials provided, allow running if a saved session exists for the target output folder
    out_path = Path(args.out)
    state_path = out_path.resolve().parent / ".auth_wiggot.json"
    if (not args.email or not args.password) and not state_path.exists() and not args.manual_login:
        print("Missing Wiggot credentials and no saved session found. "
              "Provide --email/--password or run once with --manual-login to persist a session.")
        sys.exit(2)

    out = export_wiggot_excel(
        args.email or "",
        args.password or "",
        out_path,
        headed=args.headed,
        slow_mo=args.slow_mo,
        manual_login=args.manual_login,
        manual_export=args.manual_export,
    )
    print(f"Saved Wiggot export to: {out}")


if __name__ == "__main__":
    main()
