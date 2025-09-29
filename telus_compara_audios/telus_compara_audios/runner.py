import argparse
import time
import logging
from pathlib import Path
import csv
from typing import Optional, Tuple

import numpy as np
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


# -------- Audio Capture & Similarity ---------
def _js_get_audio_srcs():
        # Returns an array of objects with {role, src} for audio elements
        return """
        () => {
            const out = [];
            const buttons = Array.from(document.querySelectorAll('button, [role=button]'));
            // Heuristic: find audio players or data-src near the labels
            const areas = [
                {key: 'A', label: ['Audio A','Version A']},
                {key: 'B', label: ['Audio B','Version B']},
                {key: 'R', label: ['Reference','Referencia']}
            ];
            const getClosestAudioOrSrc = (el) => {
                const container = el.closest('section,div') || document.body;
                const audio = container.querySelector('audio');
                if (audio && audio.src) return audio.src;
                // look for data attributes commonly used
                const cand = container.querySelector('[data-src], [data-url]');
                if (cand) return cand.getAttribute('data-src') || cand.getAttribute('data-url');
                // try links
                const a = container.querySelector('a[href$=".mp3"],a[href$=".wav"],a[href*="audio"]');
                if (a) return a.href;
                return null;
            };
            for (const area of areas) {
                let found = null;
                for (const txt of area.label) {
                    const btn = buttons.find(b => (b.textContent||'').toLowerCase().includes(txt.toLowerCase()));
                    if (btn) { found = btn; break; }
                }
                if (found) {
                    const src = getClosestAudioOrSrc(found);
                    if (src) out.push({role: area.key, src});
                }
            }
            // Also include any obvious <audio> tags if not found
            if (out.length < 3) {
                document.querySelectorAll('audio').forEach(a => {
                    if (a.src) out.push({role: 'U', src: a.src});
                });
            }
            return out;
        }
        """


def _js_fetch_pcm_from_src(src: str):
        # Decode audio via WebAudio and return Float32Array as Array
        return f"""
        async () => {{
            const Ctor = window.AudioContext || window.webkitAudioContext;
            const ctx = new Ctor();
            const res = await fetch('{src}');
            const buf = await res.arrayBuffer();
            const audio = await ctx.decodeAudioData(buf.slice(0));
            const ch = audio.numberOfChannels > 0 ? 0 : 0;
            const data = audio.getChannelData(ch);
            // Downsample to ~22050 to limit size
            const step = Math.max(1, Math.floor(audio.sampleRate / 22050));
            const out = [];
            for (let i=0;i<data.length;i+=step) out.push(data[i]);
            const result = {{sampleRate: audio.sampleRate/step, data: out}};
            try {{ ctx.close(); }} catch (e) {{}}
            return result;
        }}
        """


def _normalize(sig: np.ndarray) -> np.ndarray:
        sig = sig.astype(np.float32)
        sig -= np.mean(sig) if sig.size else 0.0
        std = float(np.std(sig))
        if std > 1e-12:
                sig /= std
        return sig


def _sim_time_corr(ref: np.ndarray, x: np.ndarray) -> float:
        a = _normalize(ref)
        b = _normalize(x)
        n = min(len(a), len(b))
        if n < 64:
                return 0.0
        a = a[:n]
        b = b[:n]
        return float(np.clip(np.mean(a * b), -1.0, 1.0))


def _sim_freq_cos(ref: np.ndarray, x: np.ndarray) -> float:
        n = min(len(ref), len(x))
        if n < 256:
                return 0.0
        n = int(2 ** np.floor(np.log2(n)))  # power of two
        A = np.fft.rfft(_normalize(ref[:n]))
        B = np.fft.rfft(_normalize(x[:n]))
        magA = np.abs(A)
        magB = np.abs(B)
        num = float(np.dot(magA, magB))
        den = float(np.linalg.norm(magA) * np.linalg.norm(magB))
        return float(num / den) if den > 1e-9 else 0.0


def compute_similarity(ref: np.ndarray, cand: np.ndarray) -> float:
        # Blend time correlation and spectral cosine
        t = _sim_time_corr(ref, cand)
        f = _sim_freq_cos(ref, cand)
        # map to [0,1]
        t_n = (t + 1) / 2
        f_n = (f + 1) / 2
        return 0.6 * t_n + 0.4 * f_n


def _best_lag(ref: np.ndarray, x: np.ndarray, max_lag: int = 2048) -> int:
        n = min(len(ref), len(x))
        if n < 256:
            return 0
        a = _normalize(ref[:n])
        b = _normalize(x[:n])
        max_lag = int(min(max_lag, n - 1))
        # compute correlation around zero lag
        lags = range(-max_lag, max_lag + 1)
        best_val = -1e9
        best_l = 0
        for L in lags:
            if L >= 0:
                val = float(np.mean(a[L:] * b[: n - L])) if (n - L) > 0 else -1e9
            else:
                L2 = -L
                val = float(np.mean(a[: n - L2] * b[L2:])) if (n - L2) > 0 else -1e9
            if val > best_val:
                best_val = val
                best_l = L
        return best_l


def _align_by_lag(ref: np.ndarray, x: np.ndarray, max_lag: int = 2048) -> Tuple[np.ndarray, np.ndarray]:
        L = _best_lag(ref, x, max_lag=max_lag)
        n = min(len(ref), len(x))
        if L >= 0:
            a = ref[L:n]
            b = x[: n - L]
        else:
            k = -L
            a = ref[: n - k]
            b = x[k:n]
        m = min(len(a), len(b))
        return a[:m], b[:m]


def _rmse(a: np.ndarray, b: np.ndarray) -> float:
        m = min(len(a), len(b))
        if m == 0:
            return 1.0
        d = _normalize(a[:m]) - _normalize(b[:m])
        return float(np.sqrt(np.mean(d * d)))


def _psnr_from_rmse(rmse: float) -> float:
        eps = 1e-9
        rmse = max(rmse, eps)
        return float(20.0 * np.log10(1.0 / rmse))  # signals normalized


def _symmetric_kl_spectrum(a: np.ndarray, b: np.ndarray) -> float:
        n = min(len(a), len(b))
        if n < 256:
            return 1.0
        n = int(2 ** np.floor(np.log2(n)))
        A = np.abs(np.fft.rfft(_normalize(a[:n]))) ** 2
        B = np.abs(np.fft.rfft(_normalize(b[:n]))) ** 2
        eps = 1e-12
        A = A + eps
        B = B + eps
        A = A / np.sum(A)
        B = B / np.sum(B)
        kl_ab = float(np.sum(A * np.log(A / B)))
        kl_ba = float(np.sum(B * np.log(B / A)))
        return 0.5 * (kl_ab + kl_ba)


def compute_audio_metrics(ref: np.ndarray, cand: np.ndarray) -> dict:
        r, c = _align_by_lag(ref, cand, max_lag=2048)
        corr_t = _sim_time_corr(r, c)
        cos_f = _sim_freq_cos(r, c)
        rmse = _rmse(r, c)
        psnr = _psnr_from_rmse(rmse)
        kl = _symmetric_kl_spectrum(r, c)
        # Composite score in [0,1]
        corr_n = (corr_t + 1) / 2
        cos_n = max(0.0, min(1.0, cos_f))
        psnr_n = max(0.0, min(1.0, psnr / 60.0))
        kl_inv = 1.0 / (1.0 + 5.0 * kl)
        score = 0.4 * corr_n + 0.3 * cos_n + 0.2 * psnr_n + 0.1 * kl_inv
        return {
            "corr_t": corr_t,
            "cos_f": cos_f,
            "rmse": rmse,
            "psnr": psnr,
            "kl": kl,
            "score": float(score),
        }


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
    parser.add_argument("--strategy", type=str, default="smart", choices=["smart","tie","alternate","always-a","always-b"], help="Estrategia para decidir")
    parser.add_argument("--tie-diff", type=float, default=0.02, help="Umbral |simA-simB| para Tie")
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

            # Estrategias: simple o SMART (analiza PCM vs Reference)
            if args.strategy == "always-a":
                decision = "Version A"
            elif args.strategy == "always-b":
                decision = "Version B"
            elif args.strategy == "alternate":
                decision = "Version A" if not pick_toggle else "Version B"
                pick_toggle = not pick_toggle
            elif args.strategy == "tie":
                decision = "Tie"
            else:
                # SMART: intenta recuperar URLs y decodificar PCM en el navegador
                decision = "Tie"
                try:
                    srcs = page.evaluate(_js_get_audio_srcs())
                    # Mapear por rol
                    urlA = next((s['src'] for s in srcs if s.get('role')=='A'), None)
                    urlB = next((s['src'] for s in srcs if s.get('role')=='B'), None)
                    urlR = next((s['src'] for s in srcs if s.get('role') in ('R','Ref')), None)
                    if urlA and urlB and urlR:
                        ref = page.evaluate(_js_fetch_pcm_from_src(urlR))
                        a = page.evaluate(_js_fetch_pcm_from_src(urlA))
                        b = page.evaluate(_js_fetch_pcm_from_src(urlB))
                        ref_sig = np.array(ref.get('data', []), dtype=np.float32)
                        a_sig = np.array(a.get('data', []), dtype=np.float32)
                        b_sig = np.array(b.get('data', []), dtype=np.float32)
                        mA = compute_audio_metrics(ref_sig, a_sig)
                        mB = compute_audio_metrics(ref_sig, b_sig)
                        delta = mA['score'] - mB['score']
                        logger.info(
                            "AudioMetrics-> A: corr={mA_corr:.4f} cos={mA_cos:.4f} rmse={mA_rmse:.4f} psnr={mA_psnr:.2f} kl={mA_kl:.4f} | "
                            "B: corr={mB_corr:.4f} cos={mB_cos:.4f} rmse={mB_rmse:.4f} psnr={mB_psnr:.2f} kl={mB_kl:.4f}".format(
                                mA_corr=mA['corr_t'], mA_cos=mA['cos_f'], mA_rmse=mA['rmse'], mA_psnr=mA['psnr'], mA_kl=mA['kl'],
                                mB_corr=mB['corr_t'], mB_cos=mB['cos_f'], mB_rmse=mB['rmse'], mB_psnr=mB['psnr'], mB_kl=mB['kl']
                            )
                        )
                        logger.info(
                            f"CombinedScore-> A:{mA['score']:.4f} B:{mB['score']:.4f} (Δ={delta:.4f}, tie≤{args.tie_diff})"
                        )
                        if abs(delta) < args.tie_diff:
                            decision = "Tie"
                        else:
                            decision = "Version A" if delta > 0 else "Version B"
                except Exception as e:
                    logger.info(f"SMART fallo, usando respaldo: {e}")

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
