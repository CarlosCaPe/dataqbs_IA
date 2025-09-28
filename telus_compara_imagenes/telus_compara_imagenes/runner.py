import argparse
import hashlib
import io
import time
import logging
from pathlib import Path
import csv
from typing import Tuple, Optional, List

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright


def setup_logger(log_file: Path | None):
    logger = logging.getLogger("telus_compare")
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


def image_sharpness_score(pil_img: Image.Image) -> float:
    # Laplacian variance by finite differences (no SciPy dependency)
    gray = pil_img.convert("L")
    arr = np.asarray(gray, dtype=np.float32)
    gx = np.zeros_like(arr)
    gy = np.zeros_like(arr)
    gx[:, 1:-1] = arr[:, 2:] - arr[:, :-2]
    gy[1:-1, :] = arr[2:, :] - arr[:-2, :]
    lap = gx + gy
    var = float(np.var(lap))
    return var


def grab_element_image(page, selector: str) -> Optional[Image.Image]:
    try:
        el = page.wait_for_selector(selector, timeout=1000)
        buf = el.screenshot(timeout=800)
        return Image.open(io.BytesIO(buf))
    except Exception:
        return None


def grab_recon_container(page, which: str) -> Optional[Image.Image]:
    """Try multiple anchors to screenshot the container for Reconstruction A or B.
    which: 'A' or 'B'
    """
    which = which.upper().strip()
    texts = [
        f"Reconstruction {which}",
        f"Reconstrucción {which}",
        f"Option {which}",
        which,  # risky but used as last resort
    ]
    # 1) Try by label text
    for txt in texts:
        try:
            label = page.get_by_text(txt, exact=False).first
            container = label.locator("xpath=ancestor::*[self::div or self::section][1]").first
            buf = container.screenshot(timeout=1500)
            return Image.open(io.BytesIO(buf))
        except Exception:
            continue
    # 2) Try by role/button name
    for txt in texts:
        try:
            btn = page.get_by_role("button", name=txt, exact=False).first
            container = btn.locator("xpath=ancestor::*[self::div or self::section][1]").first
            buf = container.screenshot(timeout=1500)
            return Image.open(io.BytesIO(buf))
        except Exception:
            continue
    # Removed global scan to keep iteration snappy
    return None


def _nearest_image_to_button(page, button_locator, root=None) -> Optional[Image.Image]:
    """Given a decision button locator, find the most plausible associated image above it."""
    try:
        bb_btn = _bbox(page, button_locator)
        if not bb_btn:
            return None
        cx_btn = bb_btn.get("x", 0) + bb_btn.get("width", 0) / 2
        y_btn = bb_btn.get("y", 0)
        scope = root if root is not None else page
        imgs = scope.locator("img").all()
        best = None
        best_score = -1.0
        for im in imgs:
            try:
                bb = im.bounding_box()
                if not bb:
                    continue
                # Prefer images above the button and roughly aligned horizontally
                cx = bb["x"] + bb["width"] / 2
                cy = bb["y"] + bb["height"] / 2
                if cy >= y_btn - 10:
                    continue
                dx = abs(cx - cx_btn)
                if dx > max(200, 0.6 * bb_btn.get("width", 200)):
                    continue
                area = bb["width"] * bb["height"]
                # Score: larger area and closer horizontally
                score = area / (1.0 + dx)
                if score > best_score:
                    best = im
                    best_score = score
            except Exception:
                continue
        if best is not None:
            buf = best.screenshot(timeout=1200)
            return Image.open(io.BytesIO(buf))
    except Exception:
        return None
    return None


def grab_recon_by_button(page, which: str) -> Optional[Image.Image]:
    which = which.upper().strip()
    names = [
        f"Reconstruction {which}",
        f"Reconstrucción {which}",
        f"Option {which}",
        f"Opción {which}",
        which,
    ]
    for nm in names:
        for getter in (
            lambda: page.get_by_role("button", name=nm, exact=False).first,
            lambda: page.get_by_text(nm, exact=False).first,
        ):
            try:
                btn = getter()
                # Ensure it exists/visible quickly
                btn.wait_for(state="visible", timeout=800)
                # Prefer searching within the same card as the submit button
                card = None
                try:
                    card = _get_submit_button(page)
                    if card is not None:
                        card = card.locator("xpath=ancestor::*[self::div or self::section][1]").first
                except Exception:
                    card = None
                img = _nearest_image_to_button(page, btn, root=card)
                if img is not None:
                    return img
            except Exception:
                continue
    return None


def select_side_by_side(page) -> None:
    # Try a few candidates to click the mode
    for sel in [
        "text=Side by Side",
        "button:has-text('Side by Side')",
        "[role=button]:has-text('Side by Side')",
    ]:
        try:
            page.click(sel, timeout=2500)
            break
        except Exception:
            continue


def _bbox(page, locator) -> Optional[dict]:
    try:
        return locator.bounding_box()
    except Exception:
        return None


def _resize_to(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
    return img.resize(size, Image.BILINEAR)


def _to_gray_f32(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L"), dtype=np.float32)


def _mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean((a - b) ** 2))


def _psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = _mse(a, b)
    if mse <= 1e-9:
        return 100.0
    return float(20.0 * np.log10(255.0 / np.sqrt(mse)))


def _global_ssim_like(a: np.ndarray, b: np.ndarray) -> float:
    # One-window SSIM approximation (not patch-based)
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2
    mu_x = float(np.mean(a))
    mu_y = float(np.mean(b))
    sigma_x = float(np.var(a))
    sigma_y = float(np.var(b))
    sigma_xy = float(np.mean((a - mu_x) * (b - mu_y)))
    num = (2 * mu_x * mu_y + C1) * (2 * sigma_xy + C2)
    den = (mu_x ** 2 + mu_y ** 2 + C1) * (sigma_x + sigma_y + C2)
    if den == 0:
        return 0.0
    return float(num / den)


def _hist_corr(a: np.ndarray, b: np.ndarray) -> float:
    # histogram correlation on grayscale 256 bins
    ha, _ = np.histogram(a, bins=256, range=(0, 255), density=True)
    hb, _ = np.histogram(b, bins=256, range=(0, 255), density=True)
    # Pearson correlation
    va = ha - ha.mean()
    vb = hb - hb.mean()
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def image_signature(img: Optional[Image.Image]) -> Optional[str]:
    if img is None:
        return None
    try:
        # Downscale to limit bytes and normalize
        thumb = img.convert("L").resize((64, 64), Image.BILINEAR)
        return hashlib.md5(thumb.tobytes()).hexdigest()
    except Exception:
        return None


def _get_decision_button(page, which: str):
    which = which.upper().strip()
    names = [
        f"Reconstruction {which}",
        f"Reconstrucción {which}",
        f"Option {which}",
        f"Opción {which}",
        which,
    ]
    for nm in names:
        for q in [
            lambda: page.get_by_role("button", name=nm, exact=False).first,
            lambda: page.get_by_text(nm, exact=False).first,
            lambda: page.locator(f"button:has-text('{nm}')").first,
        ]:
            try:
                loc = q()
                loc.wait_for(state="visible", timeout=600)
                return loc
            except Exception:
                continue
    return None


def _get_submit_button(page):
    """Return the 'Submit Evaluation' button locator if visible, else None."""
    for sel in [
        "button:has-text('Submit Evaluation')",
        "[role=button]:has-text('Submit Evaluation')",
        "button:has-text('Submit')",
        "[type=submit]",
        "[role=button]:has-text('Submit')",
        "text=Submit Evaluation",
    ]:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=800)
            return loc
        except Exception:
            continue
    return None


def _wait_submit_enabled(submit_loc, timeout_ms: int = 5000) -> bool:
    """Wait until the provided submit locator becomes enabled/interactive."""
    if submit_loc is None:
        return False
    end = time.time() + (timeout_ms / 1000.0)
    while time.time() < end:
        try:
            # is_enabled accounts for disabled attribute and CSS/disconnected states
            if submit_loc.is_enabled():
                return True
        except Exception:
            pass
        try:
            submit_loc.wait_for(state="visible", timeout=300)
        except Exception:
            pass
    return False


def click_decision_scoped(page, decision: str) -> bool:
    """Click the decision button inside the same card/section as the Submit button.
    Falls back to global click if scoping fails.
    Returns True if a click was performed.
    """
    decision = decision.strip()
    submit = _get_submit_button(page)
    if submit is not None:
        try:
            card = submit.locator("xpath=ancestor::*[self::div or self::section][1]").first
            # Prefer role-based lookup within card
            try:
                card.get_by_role("button", name=decision, exact=False).first.click(timeout=1200)
                return True
            except Exception:
                pass
            # Fallback to text-based within card
            for sel in [
                f"button:has-text('{decision}')",
                f"[role=button]:has-text('{decision}')",
                f"text={decision}",
            ]:
                try:
                    card.locator(sel).first.click(timeout=1200)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
    # Last resort: global click
    try:
        page.get_by_role("button", name=decision, exact=False).first.click(timeout=1200)
        return True
    except Exception:
        for sel in [
            f"button:has-text('{decision}')",
            f"[role=button]:has-text('{decision}')",
            f"text={decision}",
        ]:
            try:
                page.locator(sel).first.click(timeout=1200)
                return True
            except Exception:
                continue
    return False


def ensure_decision_selected(page, decision: str, logger: logging.Logger, wait_ms: int = 2000) -> bool:
    """After attempting to click the decision, ensure it's actually selected by
    waiting for Submit enabled. If not, try several strategies and re-check.
    """
    submit = _get_submit_button(page)
    if _wait_submit_enabled(submit, timeout_ms=wait_ms):
        return True

    # Strategy 1: double-click decision
    try:
        if click_decision_scoped(page, decision):
            page.wait_for_timeout(150)
            if click_decision_scoped(page, decision):
                if _wait_submit_enabled(_get_submit_button(page), timeout_ms=800):
                    return True
    except Exception:
        pass

    # Strategy 2: focus + Space key on the decision button
    try:
        submit = _get_submit_button(page)
        if submit is not None:
            card = submit.locator("xpath=ancestor::*[self::div or self::section][1]").first
            btn = card.get_by_role("button", name=decision, exact=False).first
            btn.focus()
            page.keyboard.press("Space")
            if _wait_submit_enabled(_get_submit_button(page), timeout_ms=800):
                return True
    except Exception:
        pass

    # Strategy 3: try radio inputs inside the card (pick by index: A=first, B=second)
    try:
        submit = _get_submit_button(page)
        if submit is not None:
            card = submit.locator("xpath=ancestor::*[self::div or self::section][1]").first
            radios = card.locator("input[type=radio]")
            count = radios.count()
            if count > 0:
                idx = 0 if decision.endswith("A") else (1 if decision.endswith("B") else min(2, count - 1))
                idx = max(0, min(idx, count - 1))
                radios.nth(idx).check(force=True, timeout=800)
                if _wait_submit_enabled(_get_submit_button(page), timeout_ms=800):
                    return True
    except Exception:
        pass

    # Strategy 4: try pressing Enter (some UIs toggle selection on Enter when focused)
    try:
        page.keyboard.press("Enter")
        if _wait_submit_enabled(_get_submit_button(page), timeout_ms=800):
            return True
    except Exception:
        pass

    logger.info("No se pudo confirmar la selección (Submit no habilitado).")
    return False


def fallback_grab_by_layout(page, which: str) -> Optional[Image.Image]:
    """Fallback: viewport screenshot and crop left/right region based on button positions or halves."""
    try:
        # Take a viewport screenshot
        png = page.screenshot(full_page=False, timeout=1500)
        shot = Image.open(io.BytesIO(png))
        W, H = shot.size

        # Find header and buttons to define regions
        header_y = 0
        for sel in [
            "text=Compare Reconstructions",
            "text=Which reconstruction better",
            "text=Reconstrucciones",
        ]:
            try:
                loc = page.locator(sel).first
                bb = _bbox(page, loc)
                if bb:
                    header_y = int(bb.get("y", 0))
                    break
            except Exception:
                continue

        btnA = _get_decision_button(page, "A")
        btnB = _get_decision_button(page, "B")
        xA = int(_bbox(page, btnA).get("x", 0) + _bbox(page, btnA).get("width", 0) / 2) if btnA and _bbox(page, btnA) else int(W * 0.25)
        xB = int(_bbox(page, btnB).get("x", 0) + _bbox(page, btnB).get("width", 0) / 2) if btnB and _bbox(page, btnB) else int(W * 0.75)
        yBtm = 0
        try:
            # Bottom bound: min of A/B button top y
            yA = int(_bbox(page, btnA).get("y", 0)) if btnA and _bbox(page, btnA) else int(H * 0.9)
            yB = int(_bbox(page, btnB).get("y", 0)) if btnB and _bbox(page, btnB) else int(H * 0.9)
            yBtm = max(0, min(yA, yB) - 10)
        except Exception:
            yBtm = int(H * 0.85)

        x_mid = (xA + xB) // 2
        top = max(0, header_y + 20)
        bottom = min(H, max(top + 20, yBtm))
        if which.upper() == "A":
            box = (0, top, max(1, x_mid), bottom)
        else:
            box = (min(W - 1, x_mid), top, W, bottom)
        if box[2] - box[0] < 10 or box[3] - box[1] < 10:
            return None
        return shot.crop(box)
    except Exception:
        return None


def similarity_to_original(orig: Image.Image, cand: Image.Image) -> float:
    # align size
    cand = _resize_to(cand, orig.size)
    a = _to_gray_f32(orig)
    b = _to_gray_f32(cand)

    # multi-view: full + center crop + scaled small
    views: List[Tuple[np.ndarray, np.ndarray]] = [(a, b)]
    # center 80%
    h, w = a.shape
    cy0 = int(h * 0.1)
    cy1 = int(h * 0.9)
    cx0 = int(w * 0.1)
    cx1 = int(w * 0.9)
    views.append((a[cy0:cy1, cx0:cx1], b[cy0:cy1, cx0:cx1]))
    # scaled small (quarter) via PIL
    small_orig = Image.fromarray(a.astype(np.uint8)).resize((max(8, w // 4), max(8, h // 4)), Image.BILINEAR)
    small_cand = Image.fromarray(b.astype(np.uint8)).resize((max(8, w // 4), max(8, h // 4)), Image.BILINEAR)
    views.append((np.asarray(small_orig, dtype=np.float32), np.asarray(small_cand, dtype=np.float32)))

    scores = []
    for va, vb in views:
        mse = _mse(va, vb)
        psnr = _psnr(va, vb)
        ssim_like = _global_ssim_like(va, vb)  # [-1,1]
        hist = _hist_corr(va, vb)              # [-1,1]
        # normalize to [0,1]
        ssim_n = (ssim_like + 1) / 2
        hist_n = (hist + 1) / 2
        # psnr: typical 0..50+; map to 0..1 with soft cap 60
        psnr_n = min(psnr / 60.0, 1.0)
        # mse: lower better; use 1/(1+mse_norm) with soft norm by 500
        mse_n = 1.0 / (1.0 + (mse / 500.0))
        score = 0.35 * ssim_n + 0.25 * hist_n + 0.25 * psnr_n + 0.15 * mse_n
        scores.append(score)
    return float(np.mean(scores))


def find_original_image(page) -> Optional[Image.Image]:
    # 1) Try text labels
    for txt in ["Original", "Original Image", "Imagen original", "Ground Truth", "Reference"]:
        try:
            label = page.get_by_text(txt, exact=False).first
            container = label.locator("xpath=ancestor::*[self::div or self::section][1]")
            img = container.locator("img").first
            buf = img.screenshot(timeout=1500)
            return Image.open(io.BytesIO(buf))
        except Exception:
            continue

    # 2) Geometric heuristic: pick the largest image above the recon panels
    try:
        a_lbl = page.get_by_text("Reconstruction A").first
        b_lbl = page.get_by_text("Reconstruction B").first
        a_bb = _bbox(page, a_lbl)
        b_bb = _bbox(page, b_lbl)
        if not a_bb or not b_bb:
            return None
        y_limit = min(a_bb.get("y", 1e9), b_bb.get("y", 1e9))
        imgs = page.locator("img").all()
        best = None
        best_area = 0
        for im in imgs:
            try:
                bb = im.bounding_box()
                if not bb:
                    continue
                cy = bb["y"] + bb["height"] / 2
                if cy < y_limit - 20:  # clearly above
                    area = bb["width"] * bb["height"]
                    if area > best_area:
                        best = im
                        best_area = area
            except Exception:
                continue
        if best is not None:
            buf = best.screenshot(timeout=1500)
            return Image.open(io.BytesIO(buf))
    except Exception:
        pass
    return None


def decide_and_click(page, logger: logging.Logger) -> str:
    # Capture A, B, and Original
    left_img = grab_element_image(page, "text=Reconstruction A >> xpath=ancestor::div[1]")
    right_img = grab_element_image(page, "text=Reconstruction B >> xpath=ancestor::div[1]")
    orig_img = find_original_image(page)

    decision = "Tie"
    if left_img and right_img and orig_img:
        sA = similarity_to_original(orig_img, left_img)
        sB = similarity_to_original(orig_img, right_img)
        logger.info(f"Similarity-> A:{sA:.4f} B:{sB:.4f}")
        # If very similar, mark Tie (threshold can be tuned)
        if abs(sA - sB) < 0.02:  # ~2% difference
            decision = "Tie"
        elif sA > sB:
            decision = "Reconstruction A"
        else:
            decision = "Reconstruction B"
    elif left_img and right_img:
        # Fallback to sharpness comparison if original not found
        a = image_sharpness_score(left_img)
        b = image_sharpness_score(right_img)
        logger.info(f"Sharpness-> A:{a:.2f} B:{b:.2f} (sin original)")
        if abs(a - b) < max(5.0, 0.05 * max(a, b)):
            decision = "Tie"
        elif a > b:
            decision = "Reconstruction A"
        else:
            decision = "Reconstruction B"

    # Click choice buttons
    choice_map = {
        "Reconstruction A": "text=Reconstruction A",
        "Reconstruction B": "text=Reconstruction B",
        "Tie": "text=Tie",
    }
    sel = choice_map.get(decision, "text=Tie")
    try:
        page.click(sel, timeout=3000)
    except Exception:
        # fallback: try by role
        try:
            page.get_by_role("button", name=decision).click(timeout=2000)
        except Exception:
            # last resort: choose Tie
            try:
                page.click("text=Tie", timeout=1500)
                decision = "Tie"
            except Exception:
                pass

    return decision


def submit_and_next(page) -> bool:
    """Click Submit when enabled and wait for navigation/content readiness."""
    submit = _get_submit_button(page)
    if submit is None:
        # Try pressing Enter as a fallback (if a decision button focused)
        try:
            page.keyboard.press("Enter")
            return True
        except Exception:
            return False

    # Ensure visible on screen
    try:
        submit.scroll_into_view_if_needed(timeout=600)
    except Exception:
        pass

    # Wait until enabled then click
    if not _wait_submit_enabled(submit, timeout_ms=6000):
        # Nudge the page (tiny scroll) and try again briefly
        try:
            page.evaluate("() => window.scrollBy(0, 100)")
        except Exception:
            pass
        if not _wait_submit_enabled(submit, timeout_ms=2000):
            return False
    try:
        submit.click(timeout=1500)
    except Exception:
        # one more attempt via page.dispatchEvent
        try:
            submit.dispatch_event("click")
        except Exception:
            # Enter fallback
            try:
                page.keyboard.press("Enter")
            except Exception:
                return False

    # Quick readiness checks (panel remains, but content should refresh soon)
    for _ in range(2):
        try:
            page.wait_for_selector("text=Reconstruction A", timeout=4000)
            return True
        except Exception:
            try:
                page.wait_for_timeout(400)
            except Exception:
                pass
    return True


def wait_for_compare_panel(page, timeout_s: int = 30) -> bool:
    """Waits for the compare section to appear, scrolling if needed."""
    end = time.time() + timeout_s
    targets = [
        "text=Compare Reconstructions",
        "text=Reconstruction A",
        "text=Which reconstruction better matches",
    ]
    while time.time() < end:
        # scan current viewport
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
        # full-page progressive scan downward
        try:
            dims = page.evaluate("() => ({sh: document.body.scrollHeight, y: window.scrollY, ih: window.innerHeight})")
            sh = int(dims.get("sh", 0) or 0)
            y = int(dims.get("y", 0) or 0)
            ih = int(dims.get("ih", 0) or 0)
            if y + ih + 50 < sh:
                page.evaluate("() => window.scrollBy(0, Math.floor(window.innerHeight*0.9))")
            else:
                # back to top and retry a bit
                page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(300)
        except Exception:
            try:
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(300)
            except Exception:
                pass
    return False


def main():
    parser = argparse.ArgumentParser(description="Automatiza comparaciones Side by Side en Multimango")
    parser.add_argument("--headed", action="store_true", help="Abrir navegador con UI")
    parser.add_argument("--delay-seconds", type=int, default=1, help="Retardo humano por iteración (s)")
    parser.add_argument("--max-iters", type=int, default=0, help="Máximo de iteraciones (0 = ilimitado)")
    parser.add_argument("--log-file", type=str, default="", help="Ruta del log")
    parser.add_argument("--use-chrome", action="store_true", help="Usar canal Chrome y perfil persistente")
    parser.add_argument("--no-persistent", action="store_true", help="No usar perfil persistente; abrir contexto efímero")
    parser.add_argument("--audit-csv", type=str, default="", help="Ruta de CSV para auditar decisiones")
    parser.add_argument("--audit-limit", type=int, default=0, help="Máximo de filas a guardar en CSV (0 = todas)")
    parser.add_argument("--email", type=str, default="", help="Correo para login (si es requerido)")
    parser.add_argument("--password", type=str, default="", help="Contraseña para login (si es requerido)")
    parser.add_argument("--manual-login", action="store_true", help="Hacer login manualmente en la ventana (tiempo de espera 3 min)")
    parser.add_argument("--fast", action="store_true", help="Modo rápido: omitir cálculos de imagen y seleccionar Tie de inmediato")
    parser.add_argument("--tie-diff", type=float, default=0.02, help="Umbral de |simA-simB| para declarar Tie")
    parser.add_argument("--tie-sharp-abs", type=float, default=5.0, help="Umbral absoluto de diferencia de nitidez para Tie")
    parser.add_argument("--tie-sharp-rel", type=float, default=0.05, help="Umbral relativo (fracción) de nitidez para Tie")
    parser.add_argument("--prefer-sharpness", action="store_true", help="Si similitudes son cercanas, desempatar por nitidez")
    parser.add_argument("--strict", action="store_true", help="Modo estricto: umbrales más bajos y desempate por nitidez")
    parser.add_argument("--iter-timeout", type=int, default=20, help="Tiempo máximo por iteración antes de recargar/saltar (s)")
    parser.add_argument("--quick", action="store_true", help="Modo rápido: saltar comparación con 'Original' y usar nitidez para decidir")
    parser.add_argument("--no-watchdog", action="store_true", help="No verificar cambio de contenido tras Submit (más rápido, puede saltar algún refresh)")
    parser.add_argument("--audit-batch", type=int, default=1, help="Escribir el CSV cada N iteraciones (1 = cada iteración)")
    args = parser.parse_args()

    log_path = Path(args.log_file) if args.log_file else None
    logger = setup_logger(log_path)

    # Ajustes de modo estricto
    if args.strict:
        args.tie_diff = min(args.tie_diff, 0.008)
        args.tie_sharp_abs = min(args.tie_sharp_abs, 2.0)
        args.tie_sharp_rel = min(args.tie_sharp_rel, 0.02)
        args.prefer_sharpness = True

    url = "https://www.multimango.com/tasks/081925-image-quality-compare"
    start = time.time()
    iterations = 0
    csv_path = Path(args.audit_csv) if args.audit_csv else None
    csv_rows: list[dict] = []

    with sync_playwright() as p:
        # Abrir navegador: intentar persistente si no se desactiva, con fallback a efímero.
        context = None
        browser = None
        if not args.no_persistent:
            try:
                user_data = Path.cwd() / ".user_data"
                user_data.mkdir(exist_ok=True)
                if args.use_chrome:
                    context = p.chromium.launch_persistent_context(
                        str(user_data), headless=not args.headed, channel="chrome"
                    )
                else:
                    context = p.chromium.launch_persistent_context(
                        str(user_data), headless=not args.headed
                    )
            except Exception as e:
                logger.warning(f"Fallo al abrir contexto persistente: {e}. Se intentará modo efímero.")

        if context is None:
            # Fallback a efímero; si canal chrome falla, intentar sin canal.
            try:
                if args.use_chrome:
                    browser = p.chromium.launch(headless=not args.headed, channel="chrome")
                else:
                    browser = p.chromium.launch(headless=not args.headed)
            except Exception as e:
                logger.warning(f"Fallo al abrir con canal especificado: {e}. Reintentando con Chromium por defecto.")
                browser = p.chromium.launch(headless=not args.headed)
            context = browser.new_context()

        page = context.new_page()
        # Lower default timeouts to keep things snappy
        try:
            page.set_default_timeout(1500)
            page.set_default_navigation_timeout(8000)
        except Exception:
            pass
        page.goto(url, wait_until="domcontentloaded")

        # Ensure authentication if needed
        if not wait_for_compare_panel(page, timeout_s=5):
            # Try to detect simple email/password login
            auto_attempted = False
            if args.email and args.password and not args.manual_login:
                try:
                    # Try common selectors
                    for sel in [
                        "input[type=email]",
                        "input[name=email]",
                        "input[id*=email]",
                        "input[autocomplete=email]",
                    ]:
                        try:
                            page.fill(sel, args.email, timeout=2000)
                            auto_attempted = True
                            break
                        except Exception:
                            continue
                    for sel in [
                        "input[type=password]",
                        "input[name=password]",
                        "input[id*=pass]",
                        "input[autocomplete=current-password]",
                    ]:
                        try:
                            page.fill(sel, args.password, timeout=2000)
                            break
                        except Exception:
                            continue
                    # click submit
                    for sel in [
                        "button:has-text('Sign in')",
                        "button:has-text('Log in')",
                        "button:has-text('Iniciar')",
                        "button[type=submit]",
                    ]:
                        try:
                            page.click(sel, timeout=2000)
                            break
                        except Exception:
                            continue
                except Exception:
                    pass

            # If still not in compare panel, allow manual login
            if not wait_for_compare_panel(page, timeout_s=10):
                if args.headed:
                    # Manual window: give up to 3 minutes to login
                    logger.info("Esperando login manual (hasta 3 minutos)…")
                    end = time.time() + 180
                    while time.time() < end:
                        if wait_for_compare_panel(page, timeout_s=2):
                            break
                        try:
                            page.wait_for_timeout(1000)
                        except Exception:
                            pass
                    else:
                        logger.info("No se pudo autenticar en el tiempo esperado.")
                        return
                else:
                    logger.info("No autenticado y ventana sin UI. Ejecute con --headed y haga login manual, o proporcione --email/--password.")
                    return

        # Select side-by-side mode if visible
        select_side_by_side(page)

        # Ensure we can see the comparison panel first
        if not wait_for_compare_panel(page, timeout_s=30):
            logger.info("No se encontró el panel de comparación tras scroll. Terminando.")
            return
        else:
            logger.info("Panel de comparación encontrado. Iniciando iteraciones…")

        while True:
            iter_start = time.time()
            if not wait_for_compare_panel(page, timeout_s=10):
                logger.info("Panel de comparación no visible. Asumimos fin de tareas.")
                break

            # Compute metrics and decide
            left_img = None
            right_img = None
            orig_img = None
            if not args.fast:
                # Prefer the fastest method first: viewport crop by layout
                left_img = (
                    fallback_grab_by_layout(page, "A")
                    or grab_recon_by_button(page, "A")
                    or grab_recon_container(page, "A")
                )
                right_img = (
                    fallback_grab_by_layout(page, "B")
                    or grab_recon_by_button(page, "B")
                    or grab_recon_container(page, "B")
                )
                # Skip original lookup if both A/B are present; only try when needed
                orig_img = None
                if left_img is not None and right_img is not None:
                    # Trying original can be slow; rely on sharpness or similarity without it
                    pass
                else:
                    orig_img = find_original_image(page)

            metrics = {
                "simA": None,
                "simB": None,
                "sharpA": None,
                "sharpB": None,
            }

            if not args.fast and left_img:
                try:
                    metrics["sharpA"] = image_sharpness_score(left_img)
                except Exception:
                    pass
            if not args.fast and right_img:
                try:
                    metrics["sharpB"] = image_sharpness_score(right_img)
                except Exception:
                    pass
            if not args.fast and not args.quick and orig_img and left_img and right_img:
                try:
                    metrics["simA"] = similarity_to_original(orig_img, left_img)
                    metrics["simB"] = similarity_to_original(orig_img, right_img)
                except Exception:
                    pass

            decision = "Tie"
            if args.fast:
                decision = "Tie"
            elif metrics["simA"] is not None and metrics["simB"] is not None:
                sA = float(metrics["simA"])  # type: ignore[arg-type]
                sB = float(metrics["simB"])  # type: ignore[arg-type]
                delta = sA - sB
                logger.info(f"Similarity-> A:{sA:.4f} B:{sB:.4f} (Δ={delta:.4f}, tie≤{args.tie_diff})")
                if abs(delta) < args.tie_diff and args.prefer_sharpness and metrics["sharpA"] is not None and metrics["sharpB"] is not None:
                    a = float(metrics["sharpA"])  # type: ignore[arg-type]
                    b = float(metrics["sharpB"])  # type: ignore[arg-type]
                    sharp_delta = abs(a - b)
                    sharp_thr = max(args.tie_sharp_abs, args.tie_sharp_rel * max(a, b))
                    logger.info(f"Tie por similitud, desempate por nitidez A:{a:.2f} B:{b:.2f} (Δ={sharp_delta:.2f}, tie≤{sharp_thr:.2f})")
                    if sharp_delta <= sharp_thr:
                        decision = "Tie"
                    else:
                        decision = "Reconstruction A" if a > b else "Reconstruction B"
                else:
                    if abs(delta) < args.tie_diff:
                        decision = "Tie"
                    else:
                        decision = "Reconstruction A" if delta > 0 else "Reconstruction B"
            elif metrics["sharpA"] is not None and metrics["sharpB"] is not None:
                a = float(metrics["sharpA"])  # type: ignore[arg-type]
                b = float(metrics["sharpB"])  # type: ignore[arg-type]
                sharp_thr = max(args.tie_sharp_abs, args.tie_sharp_rel * max(a, b))
                logger.info(f"Sharpness-> A:{a:.2f} B:{b:.2f} (thr={sharp_thr:.2f}, sin original)")
                if abs(a - b) <= sharp_thr:
                    decision = "Tie"
                elif a > b:
                    decision = "Reconstruction A"
                else:
                    decision = "Reconstruction B"
            else:
                logger.info("No se pudieron obtener imágenes para métricas; se mantiene Tie por seguridad.")

            # Click decision (scoped to the card containing Submit)
            if not click_decision_scoped(page, decision):
                # fallback to Tie
                logger.info("No se pudo hacer clic en la opción; se intenta Tie como respaldo.")
                _ = click_decision_scoped(page, "Tie")

            # Ensure selection actually took effect (Submit enabled)
            if not ensure_decision_selected(page, decision, logger, wait_ms=2000):
                logger.info("Forzando Tie por no habilitarse Submit con la decisión inicial…")
                if not click_decision_scoped(page, "Tie"):
                    _ = click_decision_scoped(page, decision)
                _ = ensure_decision_selected(page, "Tie", logger, wait_ms=1500)

            logger.info(f"Decision: {decision}")

            # Human-like delay (short)
            # keep delay minimal
            time.sleep(max(0, min(args.delay_seconds, 1)))

            # Compute quick signatures to detect content change after submit
            sig_before_A = image_signature(left_img) if left_img else None
            sig_before_B = image_signature(right_img) if right_img else None

            # Try to submit; if it fails, scroll to submit and retry
            submitted = submit_and_next(page)
            if not submitted:
                try:
                    page.locator("text=Submit").first.scroll_into_view_if_needed(timeout=800)
                except Exception:
                    try:
                        page.evaluate("() => window.scrollBy(0, Math.floor(window.innerHeight*0.9))")
                    except Exception:
                        pass
                submitted = submit_and_next(page)
            if not submitted:
                logger.info("No fue posible enviar o no hay más items. Terminando.")
                break

            # Watchdog: ensure new content by comparing signatures (up to ~2s total)
            changed = True if args.no_watchdog else False
            if not args.no_watchdog:
                for _ in range(2):
                    try:
                        page.wait_for_timeout(250)
                        la = grab_recon_by_button(page, "A") or fallback_grab_by_layout(page, "A")
                        lb = grab_recon_by_button(page, "B") or fallback_grab_by_layout(page, "B")
                        if image_signature(la) != sig_before_A or image_signature(lb) != sig_before_B:
                            changed = True
                            break
                    except Exception:
                        continue
            if not changed and not args.no_watchdog:
                logger.info("El contenido no cambió tras enviar; reintentando scroll y esperar un poco más…")
                try:
                    page.evaluate("() => window.scrollTo(0, 0)")
                except Exception:
                    pass
                try:
                    page.wait_for_timeout(800)
                except Exception:
                    pass
                # Last resort: soft reload of page to unstick UI
                try:
                    logger.info("Intentando recargar la página para desbloquear…")
                    page.reload(wait_until="domcontentloaded")
                    select_side_by_side(page)
                    wait_for_compare_panel(page, timeout_s=15)
                except Exception:
                    pass

            # Per-iteration timeout guard
            if (time.time() - iter_start) > args.iter_timeout:
                logger.info(f"Iteración excedió {args.iter_timeout}s; recargando y continuando…")
                try:
                    page.reload(wait_until="domcontentloaded")
                    select_side_by_side(page)
                    wait_for_compare_panel(page, timeout_s=15)
                except Exception:
                    pass

            iterations += 1

            # Audit CSV: keep last N rows or all
            if csv_path:
                row = {
                    "iter": iterations,
                    "decision": decision,
                    "simA": metrics["simA"],
                    "simB": metrics["simB"],
                    "sharpA": metrics["sharpA"],
                    "sharpB": metrics["sharpB"],
                    "timestamp": time.time(),
                }
                csv_rows.append(row)
                # enforce tail limit
                if args.audit_limit and len(csv_rows) > args.audit_limit:
                    csv_rows = csv_rows[-args.audit_limit:]
                # write file every N iterations (faster)
                if args.audit_batch <= 1 or (iterations % args.audit_batch) == 0:
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
        # Cierre ordenado
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
