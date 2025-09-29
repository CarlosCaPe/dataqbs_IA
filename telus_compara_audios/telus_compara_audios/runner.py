import argparse
import time
import logging
from pathlib import Path
import csv

from playwright.sync_api import sync_playwright


def setup_logger(log_file: Path | None):
    logger = logging.getLogger("telus_compare_audio")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.handlers.clear()
    logger.addHandler(sh)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


def wait_for_audio_panel(page, timeout_s: int = 30) -> bool:
    end = time.time() + timeout_s
    targets = [
        "text=Audio Quality Evaluation Task",
        "text=Which version better matches the reference audio",
        "text=Version A",
        "text=Version B",
    ]
    while time.time() < end:
        for sel in targets:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=800)
                try:
                    loc.scroll_into_view_if_needed(timeout=800)
                except Exception:
                    pass
                return True
            except Exception:
                continue
        try:
            page.evaluate("() => window.scrollBy(0, Math.floor(window.innerHeight*0.9))")
            page.wait_for_timeout(300)
        except Exception:
            try:
                page.mouse.wheel(0, 1000)
            except Exception:
                pass
    return False


def _get_submit_button(page):
    for sel in [
        "button:has-text('Submit Evaluation')",
        "[role=button]:has-text('Submit Evaluation')",
        "button:has-text('Submit')",
        "[type=submit]",
        "[role=button]:has-text('Submit')",
    ]:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=800)
            return loc
        except Exception:
            continue
    return None


def _wait_submit_enabled(submit_loc, timeout_ms: int = 5000) -> bool:
    if submit_loc is None:
        return False
    end = time.time() + (timeout_ms / 1000.0)
    while time.time() < end:
        try:
            if submit_loc.is_enabled():
                return True
        except Exception:
            pass
        try:
            submit_loc.wait_for(state="visible", timeout=300)
        except Exception:
            pass
    return False


def click_decision(page, decision: str) -> bool:
    # Decision labels in audio UI: "Version A", "Version B", "Tie"
    names = [decision, decision.replace("Reconstruction ", "Version ")]
    for nm in names:
        try:
            page.get_by_role("button", name=nm, exact=False).first.click(timeout=1200)
            return True
        except Exception:
            for sel in [f"button:has-text('{nm}')", f"[role=button]:has-text('{nm}')", f"text={nm}"]:
                try:
                    page.locator(sel).first.click(timeout=1200)
                    return True
                except Exception:
                    continue
    return False


def submit_and_next(page) -> bool:
    submit = _get_submit_button(page)
    if submit is None:
        try:
            page.keyboard.press("Enter")
            return True
        except Exception:
            return False
    try:
        submit.scroll_into_view_if_needed(timeout=600)
    except Exception:
        pass
    if not _wait_submit_enabled(submit, timeout_ms=6000):
        try:
            page.evaluate("() => window.scrollBy(0, 100)")
        except Exception:
            pass
        if not _wait_submit_enabled(submit, timeout_ms=2000):
            return False
    try:
        submit.click(timeout=1500)
    except Exception:
        try:
            submit.dispatch_event("click")
        except Exception:
            try:
                page.keyboard.press("Enter")
            except Exception:
                return False
    for _ in range(2):
        try:
            page.wait_for_selector("text=Version A", timeout=4000)
            return True
        except Exception:
            try:
                page.wait_for_timeout(400)
            except Exception:
                pass
    return True


def main():
    parser = argparse.ArgumentParser(description="Automatiza comparaciones de calidad de audio en Multimango")
    parser.add_argument("--headed", action="store_true", help="Abrir navegador con UI")
    parser.add_argument("--delay-seconds", type=int, default=1, help="Retardo humano por iteración (s)")
    parser.add_argument("--max-iters", type=int, default=0, help="Máximo de iteraciones (0 = ilimitado)")
    parser.add_argument("--log-file", type=str, default="", help="Ruta del log")
    parser.add_argument("--use-chrome", action="store_true", help="Usar canal Chrome y perfil persistente")
    parser.add_argument("--no-persistent", action="store_true", help="No usar perfil persistente (contexto efímero)")
    parser.add_argument("--audit-csv", type=str, default="", help="Ruta de CSV para auditar decisiones")
    parser.add_argument("--audit-limit", type=int, default=0, help="Máximo de filas a guardar en CSV (0 = todas)")
    parser.add_argument("--manual-login", action="store_true", help="Hacer login manualmente (3 min)")
    parser.add_argument("--iter-timeout", type=int, default=20, help="Tiempo máximo por iteración (s)")
    parser.add_argument("--strategy", type=str, default="tie", choices=["tie","alternate","always-a","always-b"], help="Estrategia simple para decidir")
    args = parser.parse_args()

    log_path = Path(args.log_file) if args.log_file else None
    logger = setup_logger(log_path)

    url = "https://www.multimango.com/tasks/080825-audio-quality-compare"
    start = time.time()
    iterations = 0

    csv_path = Path(args.audit_csv) if args.audit_csv else None
    csv_rows: list[dict] = []

    with sync_playwright() as p:
        context = None
        browser = None
        if not args.no_persistent:
            try:
                user_data = Path.cwd() / ".user_data"
                user_data.mkdir(exist_ok=True)
                context = p.chromium.launch_persistent_context(
                    str(user_data), headless=not args.headed, channel=("chrome" if args.use_chrome else None)
                )
            except Exception as e:
                logger.warning(f"Fallo al abrir contexto persistente: {e}. Se intentará efímero.")
        if context is None:
            try:
                browser = p.chromium.launch(headless=not args.headed, channel=("chrome" if args.use_chrome else None))
            except Exception:
                browser = p.chromium.launch(headless=not args.headed)
            context = browser.new_context()

        page = context.new_page()
        try:
            page.set_default_timeout(1500)
            page.set_default_navigation_timeout(8000)
        except Exception:
            pass
        page.goto(url, wait_until="domcontentloaded")

        if not wait_for_audio_panel(page, timeout_s=8):
            if args.headed and args.manual_login:
                logger.info("Esperando login manual (hasta 3 minutos)…")
                end = time.time() + 180
                while time.time() < end:
                    if wait_for_audio_panel(page, timeout_s=2):
                        break
                    page.wait_for_timeout(1000)
            if not wait_for_audio_panel(page, timeout_s=10):
                logger.info("No se pudo acceder al panel de audio.")
                return

        logger.info("Panel de Audio encontrado. Iniciando iteraciones…")

        pick_toggle = False
        while True:
            total_str = str(args.max_iters) if args.max_iters else "?"
            logger.info(f"Iteración {iterations + 1}/{total_str}")
            iter_start = time.time()

            if not wait_for_audio_panel(page, timeout_s=10):
                logger.info("Panel de audio no visible. Terminando.")
                break

            # Estrategias simples para decidir sin análisis de audio
            if args.strategy == "always-a":
                decision = "Version A"
            elif args.strategy == "always-b":
                decision = "Version B"
            elif args.strategy == "alternate":
                decision = "Version A" if not pick_toggle else "Version B"
                pick_toggle = not pick_toggle
            else:
                decision = "Tie"

            if not click_decision(page, decision):
                logger.info("No se pudo hacer clic en la opción; se intenta Tie.")
                _ = click_decision(page, "Tie")

            if not _wait_submit_enabled(_get_submit_button(page), timeout_ms=2000):
                logger.info("Submit no habilitado; se intenta activar con Enter.")
                try:
                    page.keyboard.press("Enter")
                except Exception:
                    pass

            submitted = submit_and_next(page)
            if not submitted:
                logger.info("No fue posible enviar o no hay más items. Terminando.")
                break

            # Delay humano breve
            time.sleep(max(0, min(args.delay_seconds, 2)))

            if (time.time() - iter_start) > args.iter_timeout:
                logger.info(f"Iteración excedió {args.iter_timeout}s; recargando y continuando…")
                try:
                    page.reload(wait_until="domcontentloaded")
                    wait_for_audio_panel(page, timeout_s=15)
                except Exception:
                    pass

            iterations += 1

            if csv_path:
                row = {"iter": iterations, "decision": decision, "timestamp": time.time()}
                csv_rows.append(row)
                if args.audit_limit and len(csv_rows) > args.audit_limit:
                    csv_rows = csv_rows[-args.audit_limit:]
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                with csv_path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                    writer.writeheader()
                    writer.writerows(csv_rows)

            if args.max_iters and iterations >= args.max_iters:
                logger.info(f"Alcanzado max-iters={args.max_iters}")
                break

        elapsed = time.time() - start
        logger.info(f"Iteraciones realizadas: {iterations}")
        logger.info(f"Tiempo total: {elapsed:.1f}s  (~{(elapsed/iterations) if iterations else 0:.1f}s/iter)")
        try:
            context.close()
        finally:
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
