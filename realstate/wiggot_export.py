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


def export_wiggot_excel(email: str, password: str, out_path: Path, headed: bool = False, slow_mo: int = 0, manual_login: bool = False) -> Path:
    """
    Automate Wiggot web UI to download the Excel from My Properties -> Exportar.

    Inputs:
    - email/password: Wiggot credentials
    - out_path: target path to save the downloaded file as wiggot.xlsx
    Options:
    - headed: run with visible browser
    - slow_mo: milliseconds to slow interactions for stability/debugging

    Returns the saved file path.
    """
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    download_dir = out_path.parent
    state_path = download_dir / ".auth_wiggot.json"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed, slow_mo=slow_mo)
        context = browser.new_context(
            accept_downloads=True,
            storage_state=str(state_path) if state_path.exists() else None,
        )
        # Be generous with timeouts; Wiggot can be slow or show modals
        context.set_default_timeout(60000)
        page = context.new_page()

        # 1) Go to login or properties page depending on whether we have auth state
        try:
            if state_path.exists():
                page.goto("https://new.wiggot.com/my-properties", wait_until="domcontentloaded")
            else:
                page.goto("https://new.wiggot.com/login", wait_until="domcontentloaded")
        except Exception:
            page.goto("https://new.wiggot.com/", wait_until="domcontentloaded")

        # Handle cookie banners if present (best-effort)
        for cookie_sel in [
            "button:has-text('Aceptar')",
            "button:has-text('Acepto')",
            "button:has-text('Accept')",
            "[id*='accept'][role='button']",
            "[data-testid*='accept']",
        ]:
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

    if manual_login:
            # Allow user to complete login manually (headed recommended)
            print("Manual login mode: complete Wiggot login in the opened browser window...")
            try:
                page.wait_for_url(lambda url: "wiggot.com" in url and ("prop" in url or "my-properties" in url), timeout=120000)
            except Exception:
                # Try waiting for export controls as a proxy for authenticated state
                try:
                    page.wait_for_selector("text=Exportar", timeout=120000)
                except Exception:
                    page.screenshot(path=str(out_path.parent / "wiggot_manual_login_timeout.png"))
                    raise RuntimeError("Manual login timed out. Saved screenshot.")
        else:
            # Automated login attempt, try top-level, then any iframes
            _try_click_email_login_toggle(page)

            # First try on main page
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
        # End automated login

        # 3) Navigate to My Properties
        page.wait_for_load_state("networkidle")
        try:
            page.goto("https://new.wiggot.com/my-properties", wait_until="networkidle")
        except Exception:
            # In some flows, login redirects differently; try a second time
            page.wait_for_timeout(1500)
            page.goto("https://new.wiggot.com/my-properties", wait_until="networkidle")

        # 4) Click "Exportar" button and capture the download
        # The export button typically has text 'Exportar' and a download icon.
        with page.expect_download(timeout=60000) as download_info:
            # Try a few candidate selectors for robustness
            clicked = False
            for sel in [
                "button:has-text('Exportar')",
                "text=Exportar",
                "[data-testid*=export]",
                "[aria-label*=Export]",
            ]:
                try:
                    page.click(sel, timeout=4000)
                    clicked = True
                    break
                except Exception:
                    continue
            if not clicked:
                # Try a menu variant first
                for alt in ["text=Export", "[title*=Export]"]:
                    try:
                        page.click(alt, timeout=3000)
                        clicked = True
                        break
                    except Exception:
                        continue
            if not clicked:
                page.screenshot(path=str(out_path.parent / "wiggot_export_button_debug.png"))
                raise RuntimeError("Couldn't find the 'Exportar' button on Wiggot page. Saved screenshot.")
        download = download_info.value

        # 5) Save to desired path (overwrite)
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
    parser.add_argument(
        "--out",
        default=str(Path(__file__).parent / "properties" / "wiggot.xlsx"),
        help="Output Excel path (default: realstate/properties/wiggot.xlsx)",
    )
    args = parser.parse_args()

    if not args.email or not args.password:
        print("Missing Wiggot credentials. Provide --email/--password or set WIGGOT_EMAIL/WIGGOT_PASSWORD env vars.")
        sys.exit(2)

    out = export_wiggot_excel(args.email, args.password, Path(args.out), headed=args.headed, slow_mo=args.slow_mo, manual_login=args.manual_login)
    print(f"Saved Wiggot export to: {out}")


if __name__ == "__main__":
    main()
