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

    return page.wait_for_response(lambda r: is_excel(r), timeout=timeout_ms)


def _wait_for_export_button(ctx, timeout_ms: int = 20000) -> bool:
    """
    Wait until an element that looks like the 'Exportar' button appears.
    Returns True if found, False otherwise.
    """
        # 4) Capture the download
        if manual_export:
            print("Manual export mode: please click 'Exportar' in the Wiggot UI now… waiting for download…")
            try:
                with page.expect_download(timeout=180000) as download_info:
                    # Just block waiting for the user's click to trigger download
                    pass
                download = download_info.value
            except Exception:
                page.screenshot(path=str(out_path.parent / "wiggot_manual_export_timeout.png"))
                raise
        else:
            # Automated export with retries, popup handling, and network fallback
            total_deadline = time.time() + 240  # 4 minutes total
            last_error = None
            attempt = 1
            download = None
            while time.time() < total_deadline and download is None:
                print(f"[wiggot] Attempt {attempt}: looking for 'Exportar' and triggering export…")
                try:
                    # Ensure page is ready and the Exportar control is likely present
                    try:
                        page.wait_for_selector("text=Exportar", timeout=7000)
                    except Exception:
                        # Try a gentle reload to refresh UI state
                        try:
                            page.reload(wait_until="networkidle")
                        except Exception:
                            pass

                    # First try normal download event
                    try:
                        download = _attempt_export_download(page, per_attempt_timeout_ms=25000)
                    except Exception as e1:
                        last_error = e1
                        print("[wiggot] No direct download event, trying popup/network fallback…")

                        # Some sites open a new popup/tab for export; listen for it
                        popup = None
                        try:
                            with context.expect_page(timeout=8000) as popup_info:
                                # Try clicking again to force popup
                                page.click("text=Exportar", timeout=3000)
                            popup = popup_info.value
                        except Exception:
                            popup = None

                        target_page = popup if popup is not None else page

                        # Network response fallback: wait for an Excel-looking response
                        try:
                            resp = _wait_for_excel_response(target_page, timeout_ms=25000)
                            # Save to out_path
                            body = resp.body()
                            with open(out_path, 'wb') as f:
                                f.write(body)
                            # Small wait to ensure write completion
                            time.sleep(0.5)
                            download = True  # sentinel indicating success via network
                            break
                        except Exception as e2:
                            last_error = e2

                except Exception as e:
                    last_error = e

                # Scroll and retry; sometimes controls render lazily
                try:
                    page.mouse.wheel(0, 1200)
                    page.wait_for_timeout(800)
                except Exception:
                    pass
                attempt += 1

            if download is None:
                page.screenshot(path=str(out_path.parent / "wiggot_export_button_debug.png"))
                raise RuntimeError(f"Failed to export within timeout. Last error: {last_error}")
            try:
                page.click(cookie_sel, timeout=2000)
                break
            except Exception:
                pass

        # 2) Fill credentials and sign in
        # If already authenticated (from storage state), skip login
        try:
            if "my-properties" in page.url:
                pass
            else:
                # Sometimes the export control is present on dashboard too
                page.wait_for_selector("text=Exportar", timeout=3000)
        except Exception:
            # Not authenticated yet; proceed with login
            pass

        # Decide if we're allowed to attempt automated login
        allow_auto_login = bool(email) and bool(password) and not manual_login

        if manual_login:
            # Allow user to complete login manually (headed recommended)
            print("Manual login mode: complete Wiggot login in the opened browser window…")
            # Poll for authenticated state by checking Exportar presence on my-properties
            deadline = time.time() + 180  # 3 minutes
            while time.time() < deadline:
                try:
                    if "my-properties" not in page.url:
                        # Try to navigate to target page; if not logged in, Wiggot may redirect back to login
                        page.goto("https://new.wiggot.com/my-properties", wait_until="domcontentloaded")
                    # Check for export control
                    page.wait_for_selector("text=Exportar", timeout=3000)
                    break
                except Exception:
                    page.wait_for_timeout(1500)
            else:
                page.screenshot(path=str(out_path.parent / "wiggot_manual_login_timeout.png"))
                raise RuntimeError("Manual login timed out. Saved screenshot.")
        elif allow_auto_login:
            # Automated login attempt, try top-level, then any iframes
            _try_click_email_login_toggle(page)

            # First try on main page
            # Tune selectors for /auth/login form variants
            if not _try_fill_email(page, email):
                # Try inside iframes (Auth providers often use iframes)
                for frame in page.frames:
                    try:
                        _try_click_email_login_toggle(frame)
                        if _try_fill_email(frame, email):
                            # Fill password where the email succeeded
                            if not _try_fill_password(frame, password):
                                page.screenshot(path=str(out_path.parent / "wiggot_password_debug.png"))
                                raise RuntimeError("Could not locate the password field on Wiggot login (iframe). Saved screenshot.")
                            _click_login_submit(frame)
                            break
                    except Exception:
                        continue
                else:
                    # Not found in any frame
                    page.screenshot(path=str(out_path.parent / "wiggot_login_debug.png"))
                    raise RuntimeError("Could not locate the email field on Wiggot login page. Saved screenshot.")
            else:
                # Email filled in main page, do password and submit
                if not _try_fill_password(page, password):
                    page.screenshot(path=str(out_path.parent / "wiggot_password_debug.png"))
                    raise RuntimeError("Could not locate the password field on Wiggot login page. Saved screenshot.")
                _click_login_submit(page)
        else:
            # No credentials provided and manual login not requested. If a saved session exists,
            # we will proceed; otherwise we cannot log in automatically.
            if not state_path.exists():
                page.screenshot(path=str(out_path.parent / "wiggot_need_login.png"))
                raise RuntimeError(
                    "No Wiggot credentials provided and no saved session found. "
                    "Run once with --manual-login (headed) or provide --email/--password."
                )
        # End login handling

        # 3) Navigate to My Properties
        page.wait_for_load_state("networkidle")
        try:
            page.goto("https://new.wiggot.com/my-properties", wait_until="networkidle")
        except Exception:
            # In some flows, login redirects differently; try a second time
            page.wait_for_timeout(1500)
            page.goto("https://new.wiggot.com/my-properties", wait_until="networkidle")

        # 4) Capture the download
        # Option A: manual export: user clicks 'Exportar' themselves
        if manual_export:
            print("Manual export mode: please click 'Exportar' in the Wiggot UI now… waiting for download…")
            with page.expect_download(timeout=180000) as download_info:
                # Wait for the user to click the export control
                try:
                    page.wait_for_selector("text=Exportar", timeout=20000)
                except Exception:
                    pass
            download = download_info.value
        else:
            # Option B: automated click
            # The export button typically has text 'Exportar' and a download icon.
            # First ensure the button is present (with a few retries)
            found = False
            for _ in range(3):
                if _wait_for_export_button(page, timeout_ms=15000):
                    found = True
                    break
                # If not found, refresh or re-navigate once to stabilize
                try:
                    page.reload(wait_until="networkidle")
                except Exception:
                    page.goto("https://new.wiggot.com/my-properties", wait_until="networkidle")
            if not found:
                page.screenshot(path=str(out_path.parent / "wiggot_export_button_not_found.png"))
                raise RuntimeError("Couldn't locate 'Exportar' on the page. Saved screenshot.")

            with page.expect_download(timeout=180000) as download_info:
                # Try a few candidate selectors for robustness
                clicked = False
                for sel in [
                    "button:has-text('Exportar')",
                    "[role=button]:has-text('Exportar')",
                    "text=Exportar",
                    "[data-testid*=export]",
                    "[aria-label*=Export]",
                    "[title*=Export]",
                ]:
                    try:
                        page.click(sel, timeout=6000)
                        clicked = True
                        break
                    except Exception:
                        continue
                if not clicked:
                    # Some UIs use a menu: try opening common menu triggers first
                    for trigger in [
                        "button[aria-haspopup]",
                        "[role=button][aria-expanded]",
                        "button:has([class*='menu'])",
                        "[aria-label*='Más']",
                        "[aria-label*='More']",
                    ]:
                        try:
                            page.click(trigger, timeout=3000)
                            # After menu opens, try export options again
                            for menu_item in [
                                "text=Exportar",
                                "text=Export",
                                "[role=menuitem]:has-text('Export')",
                                "[role=menuitem]:has-text('Exportar')",
                            ]:
                                try:
                                    page.click(menu_item, timeout=3000)
                                    clicked = True
                                    break
                                except Exception:
                                    continue
                            if clicked:
                                break
                        except Exception:
                            continue
                if not clicked:
                    page.screenshot(path=str(out_path.parent / "wiggot_export_button_debug.png"))
                    raise RuntimeError("Couldn't find the 'Exportar' control on Wiggot page. Saved screenshot.")
            download = download_info.value

        # 5) Save to desired path (overwrite) if we used a real Download object
        if download is not True:  # True means we saved via network fallback already
            # Wiggot likely generates a .xlsx; keep name consistent
            tmp_path = download.path()
            if tmp_path is None:
                tmp_path = download.save_as(str(download_dir / download.suggested_filename))
            else:
                # Ensure overwrite behavior
                download.save_as(str(out_path))

            # If saved via suggested_filename, move/rename to out_path
            suggested = download.suggested_filename
            suggested_path = download_dir / suggested if suggested else None
            if suggested_path and suggested_path.exists() and suggested_path.resolve() != out_path:
                suggested_path.replace(out_path)

        # Small wait to ensure file lock released on Windows
        time.sleep(0.5)

        # Persist auth state for next runs
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
