def submit_and_next(page) -> bool:
    """Click Submit Evaluation and wait for next item or page reload."""
    btn = _get_submit_button(page)
    if not btn:
        return False
    try:
        btn.click(timeout=2000)
    except Exception:
        return False
    # Wait for either panel to reload or submit button to disappear
    end = time.time() + 8
    while time.time() < end:
        try:
            # If submit button is gone, assume next item
            if not btn.is_visible():
                return True
        except Exception:
            return True
        time.sleep(0.5)
    return False
def _get_submit_button(page):
    """Return the 'Submit Evaluation' button locator if visible, else None."""
    for sel in [
        "button:has-text('Submit Evaluation')",
        "[role=button]:has-text('Submit Evaluation')",
        "text=Submit Evaluation",
    ]:
        try:
            btn = page.locator(sel).first
            if btn.is_visible():
                return btn
        except Exception:
            continue
    return None

def _wait_submit_enabled(submit_btn, timeout_ms: int = 5000) -> bool:
    """Wait until the provided submit locator becomes enabled/interactive."""
    if submit_btn is None:
        return False
    end = time.time() + timeout_ms / 1000.0
    while time.time() < end:
        try:
            if submit_btn.is_enabled():
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False
def click_decision(page, decision: str) -> bool:
    """Click the decision button (Version A, Version B, Tie) in the UI."""
    # Map decision to button text
    btn_map = {
        "Version A": "Version A",
        "Version B": "Version B",
        "Tie": "Tie"
    }
    label = btn_map.get(decision, "Tie")
    # Try role-based and text-based selectors
    for sel in [
        f"button:has-text('{label}')",
        f"[role=button]:has-text('{label}')",
        f"text={label}",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                el.click(timeout=1500)
                return True
        except Exception:
            continue
    return False
import argparse
import time
import logging
from pathlib import Path
import csv
from typing import Optional, Tuple

import numpy as np
from playwright.sync_api import sync_playwright
import base64
import json
from datetime import datetime


def setup_logger(log_file: Path | None):
    logger = logging.getLogger("telus_compare_audio")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.handlers.clear()
    logger.addHandler(sh)
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


def wait_for_audio_panel(page, timeout_s: int = 30) -> bool:
    end = time.time() + timeout_s
    while time.time() < end:
        try:
            # Busca los botones clave en la página
            for label in ["Reference Audio", "Audio A", "Audio B"]:
                btn = page.query_selector(f"button:has-text('{label}')")
                if btn:
                    return True
        except Exception:
            pass
        try:
            page.wait_for_timeout(500)
        except Exception:
            pass
    return False
    # If you need to inject JS, use a string like below:
    tmpl = """
        // JS code for PCM capture goes here
        // ...
    """
    # return tmpl.replace("__KEY__", safe_key).replace("__DUR__", str(int(duration_ms)))


def _js_setup_audio_hooks():
        return r"""
        () => {
            if (window.__telusHooksInstalled) return true;
            window.__telusPCM = window.__telusPCM || {};
            window.__telusHooksInstalled = true;
            const C = window.AudioContext || window.webkitAudioContext;
            if (!C) return false;
            const proto = C.prototype;
            // Hook decodeAudioData (promise and callback styles)
            const origDecode = proto.decodeAudioData;
            if (origDecode && !proto.__telusDecodePatched) {
                proto.__telusDecodePatched = true;
                proto.decodeAudioData = function(buffer, successCb, errorCb){
                    try {
                        const self = this;
                        if (typeof successCb === 'function') {
                            return origDecode.call(self, buffer, function(audioBuffer){
                                try {
                                    const lab = window.__telusCurrentLabel;
                                    if (lab && audioBuffer && audioBuffer.getChannelData) {
                                        const ch0 = audioBuffer.getChannelData(0);
                                        window.__telusPCM[lab] = { data: Array.from(ch0), sampleRate: self.sampleRate };
                                    }
                                } catch (e) {}
                                return successCb(audioBuffer);
                            }, errorCb);
                        }
                        const p = origDecode.call(self, buffer);
                        return p.then(audioBuffer => {
                            try {
                                const lab = window.__telusCurrentLabel;
                                if (lab && audioBuffer && audioBuffer.getChannelData) {
                                    const ch0 = audioBuffer.getChannelData(0);
                                    window.__telusPCM[lab] = { data: Array.from(ch0), sampleRate: self.sampleRate };
                                }
                            } catch (e) {}
                            return audioBuffer;
                        });
                    } catch (e) {
                        return origDecode.apply(this, arguments);
                    }
                }
            }
            // Hook createBufferSource -> start to capture buffer content
            const origCreate = proto.createBufferSource;
            if (origCreate && !proto.__telusCreatePatched) {
                proto.__telusCreatePatched = true;
                proto.createBufferSource = function(){
                    const node = origCreate.call(this);
                    try {
                        const origStart = node.start.bind(node);
                        node.start = function(){
                            try {
                                const lab = window.__telusCurrentLabel;
                                if (lab && node.buffer && node.buffer.getChannelData) {
                                    const ch0 = node.buffer.getChannelData(0);
                                    window.__telusPCM[lab] = { data: Array.from(ch0), sampleRate: node.context.sampleRate };
                                }
                            } catch (e) {}
                            return origStart.apply(this, arguments);
                        }
                    } catch (e) {}
                    return node;
                }
            }
            return true;
        }
        """


def _js_setup_deep_audio_hooks():
        return r"""
        () => {
            if (window.__telusDeepHooksInstalled) return true;
            window.__telusPCM = window.__telusPCM || {};
            window.__telusDeepHooksInstalled = true;
            const Ctor = window.AudioContext || window.webkitAudioContext;
            function downsampleAndStore(label, audioBuffer) {
                try {
                    const sr = audioBuffer.sampleRate;
                    const step = Math.max(1, Math.floor(sr / 22050));
                    const ch0 = audioBuffer.getChannelData(0);
                    const out = [];
                    for (let i = 0; i < ch0.length; i += step) out.push(ch0[i]);
                    window.__telusPCM[label] = { sampleRate: sr/step, data: out };
                } catch (e) { /* noop */ }
            }
            async function decodeAndStore(label, arrayBuffer) {
                try {
                    const ctx = window.__telusCtx || new Ctor();
                    window.__telusCtx = ctx;
                    const buf = arrayBuffer.slice ? arrayBuffer.slice(0) : arrayBuffer;
                    const ab = await ctx.decodeAudioData(buf);
                    downsampleAndStore(label, ab);
                } catch (e) { /* noop */ }
            }
            // Patch fetch
            if (!window.__telusFetchPatched) {
                window.__telusFetchPatched = true;
                const origFetch = window.fetch;
                window.fetch = async function() {
                    const label = window.__telusCurrentLabel || 'U';
                    const res = await origFetch.apply(this, arguments);
                    try {
                        const url = (res.url || '').toLowerCase();
                        const ctype = (res.headers.get('content-type') || '').toLowerCase();
                        if (url.endsWith('.mp3') || url.endsWith('.wav') || url.endsWith('.ogg') || url.endsWith('.m4a') || url.endsWith('.aac') || url.endsWith('.flac') || ctype.startsWith('audio/')) {
                            const clone = res.clone();
                            const arr = await clone.arrayBuffer();
                            decodeAndStore(label, arr);
                        }
                    } catch (e) { /* noop */ }
                    return res;
                }
            }
            // Patch XHR
            if (!window.__telusXHRPatched) {
                window.__telusXHRPatched = true;
                const OrigXHR = window.XMLHttpRequest;
                function wrapXHR() {
                    const xhr = new OrigXHR();
                    const label = window.__telusCurrentLabel || 'U';
                    let method = 'GET'; let url = '';
                    const origOpen = xhr.open;
                    xhr.open = function(m,u){ method=m; url=u; return origOpen.apply(this, arguments); };
                    xhr.addEventListener('load', function() {
                        try {
                            const headers = xhr.getAllResponseHeaders().toLowerCase();
                            const ctypeLine = headers.split('\n').find(x => x.startsWith('content-type')) || '';
                            const ctype = ctypeLine.split(':').slice(1).join(':').trim();
                            const lowUrl = (url||'').toLowerCase();
                            if (lowUrl.endsWith('.mp3') || lowUrl.endsWith('.wav') || lowUrl.endsWith('.ogg') || lowUrl.endsWith('.m4a') || lowUrl.endsWith('.aac') || lowUrl.endsWith('.flac') || ctype.startsWith('audio/')) {
                                let arrPromise = null;
                                if (xhr.response instanceof ArrayBuffer) {
                                    arrPromise = Promise.resolve(xhr.response);
                                } else if (xhr.response instanceof Blob) {
                                    arrPromise = xhr.response.arrayBuffer();
                                } else if (xhr.response) {
                                    try { arrPromise = new Blob([xhr.response]).arrayBuffer(); } catch (e) {}
                                }
                                if (arrPromise) {
                                    arrPromise.then(arr => decodeAndStore(label, arr));
                                }
                            }
                        } catch (e) { /* noop */ }
                    });
                    return xhr;
                }
                window.XMLHttpRequest = wrapXHR;
            }
            // Patch URL.createObjectURL for Blob media
            if (!window.__telusCreateObjURLPatched) {
                window.__telusCreateObjURLPatched = true;
                const orig = URL.createObjectURL;
                URL.createObjectURL = function(obj) {
                    try {
                        const label = window.__telusCurrentLabel || 'U';
                        if (obj instanceof Blob) {
                            const type = (obj.type || '').toLowerCase();
                            if (type.startsWith('audio/')) {
                                obj.arrayBuffer().then(arr => decodeAndStore(label, arr));
                            }
                        }
                    } catch (e) { /* noop */ }
                    return orig.apply(this, arguments);
                }
            }
            // Patch HTMLMediaElement src setter
            if (!window.__telusMediaSrcPatched) {
                window.__telusMediaSrcPatched = true;
                const proto = HTMLMediaElement.prototype;
                const desc = Object.getOwnPropertyDescriptor(proto, 'src');
                if (desc && desc.set) {
                    const origSet = desc.set;
                    Object.defineProperty(proto, 'src', {
                        set(value) {
                            try {
                                const label = window.__telusCurrentLabel || 'U';
                                const v = ('' + value).toLowerCase();
                                if (v.endsWith('.mp3') || v.endsWith('.wav') || v.endsWith('.ogg') || v.endsWith('.m4a') || v.endsWith('.aac') || v.endsWith('.flac')) {
                                    fetch(value).then(r => r.arrayBuffer()).then(arr => decodeAndStore(label, arr)).catch(()=>{});
                                }
                            } catch (e) { /* noop */ }
                            return origSet.apply(this, arguments);
                        }
                    });
                }
                const origSetAttr = proto.setAttribute;
                proto.setAttribute = function(name, value) {
                    try {
                        if ((name||'').toLowerCase() === 'src') {
                            const label = window.__telusCurrentLabel || 'U';
                            const v = ('' + value).toLowerCase();
                            if (v.endsWith('.mp3') || v.endsWith('.wav') || v.endsWith('.ogg') || v.endsWith('.m4a') || v.endsWith('.aac') || v.endsWith('.flac')) {
                                fetch(value).then(r => r.arrayBuffer()).then(arr => decodeAndStore(label, arr)).catch(()=>{});
                            }
                        }
                    } catch (e) { /* noop */ }
                    return origSetAttr.apply(this, arguments);
                }
            }
            return true;
        }
        """


def _js_set_current_label(label_key: str):
        safe_key = label_key.replace("'", "")
        return f"""
        () => {{ window.__telusCurrentLabel = '{safe_key}'; return true; }}
        """


def _js_grab_pcm_via_hooks(label_key: str, duration_ms: int, timeout_ms: int = 2500):
        safe_key = label_key.replace("'", "")
        return f"""
        async () => {{
            window.__telusPCM = window.__telusPCM || {{}};
            window.__telusCurrentLabel = '{safe_key}';
            delete window.__telusPCM['{safe_key}'];
            const t0 = performance.now();
            while ((performance.now() - t0) < {timeout_ms}) {{
                const rec = window.__telusPCM['{safe_key}'];
                if (rec && rec.data && rec.data.length > 0) {{
                    const sr = rec.sampleRate || 44100;
                    const step = Math.max(1, Math.floor(sr / 22050));
                    const maxN = Math.floor((sr/1000 * {duration_ms}) / step);
                    const out = [];
                    for (let i=0; i<rec.data.length && out.length<maxN; i+=step) out.push(rec.data[i]);
                    return {{ sampleRate: sr/step, data: out, capturedMs: {duration_ms} }};
                }}
                await new Promise(r => setTimeout(r, 50));
            }}
            return null;
        }}
        """


def _js_click_play_for_label(label_key: str):
        # Explicitly click the Play control for the given label (A/B/Reference) and try to start playback
        safe_key = label_key.replace("'", "")
        tmpl = r"""
        async () => {
            window.__telusCurrentLabel = '__KEY__';
            const LABELS = {
                'A': ['Version A','Audio A','A'],
                'B': ['Version B','Audio B','B'],
                'R': ['Reference','Referencia','Ref','Original']
            };
            const texts = LABELS['__KEY__'] || [];
            const all = Array.from(document.querySelectorAll('button,[role=button],div,section,article,*'));
            let labelEl = null;
            for (const t of texts) {
                labelEl = all.find(el => (el.textContent||'').toLowerCase().includes(t.toLowerCase()));
                if (labelEl) break;
            }
            if (labelEl) {
                try { labelEl.scrollIntoView({block: 'center', behavior: 'instant'}); } catch (e) {}
                try { labelEl.click(); } catch (e) {}
            }
            const container = (labelEl && (labelEl.closest('section,div,article') || labelEl)) || document.body;
            const findPlay = (root) => {
                const sels = [
                    '[aria-label*="play" i]', '[title*="play" i]',
                    '[aria-label*="reproducir" i]', '[title*="reproducir" i]',
                    'button:has-text("Play")', 'button:has-text("Reproducir")',
                    'button .icon-play', 'button[class*="play" i]', '[data-action="play"]',
                ];
                for (const s of sels) {
                    const el = root.querySelector(s);
                    if (el) return el;
                }
                // As a last resort, try any button inside container
                const btn = root.querySelector('button,[role=button]');
                return btn || null;
            };
            let playBtn = findPlay(container) || findPlay(document);
            if (playBtn) {
                try { playBtn.click(); } catch (e) {}
            }
            let audio = container.querySelector('audio') || document.querySelector('audio');
            if (!audio) return false;
            try { audio.crossOrigin = audio.crossOrigin || 'anonymous'; } catch (e) {}
            try { await audio.play(); } catch (e) {}
            // wait for time to advance slightly to confirm playback
            const t0 = audio.currentTime || 0;
            const tStart = performance.now();
            while ((performance.now() - tStart) < 1200) {
                if ((audio.currentTime||0) > t0 + 0.05) break;
                await new Promise(r => setTimeout(r, 50));
            }
            return !audio.paused;
        }
        """
        return tmpl.replace("__KEY__", safe_key)


def _js_get_audio_src_for_label(label_key: str):
        safe_key = label_key.replace("'", "")
        return r"""
        () => {
            const LABELS = {
                'A': ['Version A','Audio A','A'],
                'B': ['Version B','Audio B','B'],
                'R': ['Reference','Referencia','Ref','Original']
            };
            const texts = LABELS['__KEY__'] || [];
            const all = Array.from(document.querySelectorAll('button,[role=button],div,section,article,*'));
            let labelEl = null;
            for (const t of texts) {
                labelEl = all.find(el => (el.textContent||'').toLowerCase().includes(t.toLowerCase()));
                if (labelEl) break;
            }
            const container = (labelEl && (labelEl.closest('section,div,article') || labelEl)) || document.body;
            let audio = container.querySelector('audio') || document.querySelector('audio');
            let video = container.querySelector('video') || document.querySelector('video');
            const element = audio || video;
            if (element) {
                const cur = element.currentSrc || element.src || '';
                if (cur) return cur;
                const srcEl = element.querySelector && element.querySelector('source[src]');
                if (srcEl && srcEl.getAttribute('src')) return srcEl.getAttribute('src');
            }
            // fallback: search for nearby data attributes or links
            const cand = container.querySelector('[data-src],[data-url],[data-audio],[data-href]');
            if (cand) return cand.getAttribute('data-src') || cand.getAttribute('data-url') || cand.getAttribute('data-audio') || cand.getAttribute('data-href');
            const a = container.querySelector('a[href$=".mp3"],a[href$=".wav"],a[href*="audio" i]');
            if (a) return a.href;
            return null;
        }
        """.replace('__KEY__', safe_key)


def _js_decode_base64_to_pcm(b64: str):
        return f"""
        async () => {{
            const b64 = '{b64}';
            function b64ToArrayBuffer(base64) {{
                const binary_string = atob(base64);
                const len = binary_string.length;
                const bytes = new Uint8Array(len);
                for (let i = 0; i < len; i++) {{
                    bytes[i] = binary_string.charCodeAt(i);
                }}
                return bytes.buffer;
            }}
            const buf = b64ToArrayBuffer(b64);
            const Ctor = window.AudioContext || window.webkitAudioContext;
            const ctx = new Ctor();
            const audio = await ctx.decodeAudioData(buf.slice(0));
            const ch = audio.numberOfChannels > 0 ? 0 : 0;
            const data = audio.getChannelData(ch);
            const step = Math.max(1, Math.floor(audio.sampleRate / 22050));
            const out = [];
            for (let i=0;i<data.length;i+=step) out.push(data[i]);
            const result = {{sampleRate: audio.sampleRate/step, data: out}};
            try {{ ctx.close(); }} catch (e) {{}}
            return result;
        }}
        """


def _js_overlay_show(message: str):
        # Show a non-blocking overlay instruction banner
        msg = message.replace("'", "\'")
        return f"""
        () => {{
            let div = document.getElementById('telus-audio-overlay');
            if (!div) {{
                div = document.createElement('div');
                div.id = 'telus-audio-overlay';
                document.body.appendChild(div);
            }}
            Object.assign(div.style, {{
                position: 'fixed', left: '0', bottom: '0', width: '100%', minHeight: '48px',
                background: 'rgba(0,0,0,0.8)', color: '#fff', display: 'flex',
                alignItems: 'center', justifyContent: 'center', zIndex: 2147483647,
                fontSize: '16px', fontFamily: 'system-ui, sans-serif',
                pointerEvents: 'none', padding: '8px 12px'
            }});
            div.textContent = '{msg}';
        }}
        """


def _js_overlay_hide():
        return """
        () => { const d=document.getElementById('telus-audio-overlay'); if(d) d.remove(); }
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


def _sig_is_silent(sig: np.ndarray) -> bool:
        if sig.size == 0:
            return True
        # Use both stddev and max-abs to detect near-silence
        return float(np.std(sig)) < 5e-6 or float(np.max(np.abs(sig))) < 5e-5


def main():
    parser = argparse.ArgumentParser(description="Automatiza comparaciones de calidad de audio en Multimango")
    parser.add_argument("--headed", action="store_true", help="Abrir navegador con UI")
    parser.add_argument("--delay-seconds", type=int, default=2, help="Retardo humano por iteración (s)")
    parser.add_argument("--max-iters", type=int, default=0, help="Máximo de iteraciones (0 = ilimitado)")
    parser.add_argument("--log-file", type=str, default="", help="Ruta del log")
    parser.add_argument("--out-dir", type=str, default="runs/audio", help="Directorio base para salidas (log/CSV) si no se especifican rutas explícitas")
    parser.add_argument("--use-chrome", action="store_true", help="Usar canal Chrome y perfil persistente")
    parser.add_argument("--no-persistent", action="store_true", help="No usar perfil persistente (contexto efímero)")
    parser.add_argument("--audit-csv", type=str, default="", help="Ruta de CSV para auditar decisiones")
    parser.add_argument("--audit-limit", type=int, default=0, help="Máximo de filas a guardar en CSV (0 = todas)")
    parser.add_argument("--manual-login", action="store_true", help="Hacer login manualmente (3 min)")
    parser.add_argument("--manual-login-timeout", type=int, default=180, help="Tiempo máximo para completar el login manual (s)")
    parser.add_argument("--iter-timeout", type=int, default=20, help="Tiempo máximo por iteración (s)")
    parser.add_argument("--strategy", type=str, default="smart", choices=["smart","tie","alternate","always-a","always-b"], help="Estrategia para decidir")
    parser.add_argument("--tie-diff", type=float, default=0.02, help="Umbral |simA-simB| para Tie")
    parser.add_argument("--fallback-strategy", type=str, default="alternate", choices=["tie","alternate","always-a","always-b"], help="Qué hacer si SMART no puede leer audio (solo si smart-fail-policy=fallback)")
    parser.add_argument("--smart-fail-policy", type=str, default="stop", choices=["stop","skip","fallback"], help="Acción cuando SMART no puede comparar: stop=detener y avisar; skip=recargar e intentar siguiente; fallback=usar --fallback-strategy")
    parser.add_argument("--smart-retries", type=int, default=2, help="Reintentos locales al fallar SMART (errores transitorios)")
    parser.add_argument("--smart-retry-wait", type=float, default=1.0, help="Espera entre reintentos SMART (s)")
    parser.add_argument("--no-mute-audio", action="store_true", help="No silenciar audio del navegador (por defecto se silencia)")
    parser.add_argument("--smart-capture-mode", type=str, default="auto", choices=["auto","fetch","media"], help="Cómo obtener PCM: auto=URLs luego media; fetch=solo URLs; media=solo reproducción del elemento")
    parser.add_argument("--capture-ms", type=int, default=1500, help="Milisegundos de audio a capturar por cada clip en modo media")
    parser.add_argument("--manual-play", action="store_true", help="Pedirte que hagas clic en Play para Ref/A/B antes de capturar")
    parser.add_argument("--play-a-sel", type=str, default="", help="Selector CSS para botón Play de Version A (opcional)")
    parser.add_argument("--play-b-sel", type=str, default="", help="Selector CSS para botón Play de Version B (opcional)")
    parser.add_argument("--play-ref-sel", type=str, default="", help="Selector CSS para botón Play de Reference (opcional)")
    parser.add_argument("--diagnose", action="store_true", help="Volcar diagnóstico de botones y fuentes de audio/video para ayudar a configurar selectores")
    args = parser.parse_args()

    # Begin main execution after parsing args
    base_out = Path(args.out_dir)
    try:
        base_out.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    # Resolve default paths under out-dir if not provided
    log_path = Path(args.log_file) if args.log_file else base_out / "audio_run.log"
    csv_default = base_out / "audio_audit.csv"
    logger = setup_logger(log_path)

    url = "https://www.multimango.com/tasks/080825-audio-quality-compare"
    start = time.time()
    iterations = 0

    csv_path = Path(args.audit_csv) if args.audit_csv else csv_default
    csv_rows: list[dict] = []

    with sync_playwright() as p:
        context = None
        browser = None
        # Lanzar navegador: intentar persistente si no se desactiva, con fallback a efímero
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

        if not wait_for_audio_panel(page, timeout_s=8):
            if args.headed and args.manual_login:
                # Solo mostrar overlay y esperar si el panel de audio NO está visible
                if not wait_for_audio_panel(page, timeout_s=2):
                    try:
                        page.evaluate("""
                        () => {
                            const div = document.createElement('div');
                            div.id = 'telus-login-overlay';
                            div.textContent = 'Por favor inicia sesión. La automatización reanudará sola.';
                            Object.assign(div.style, {
                                position: 'fixed', left: '0', top: '0', width: '100%', height: '60px',
                                background: 'rgba(0,0,0,0.8)', color: '#fff', display: 'flex',
                                alignItems: 'center', justifyContent: 'center', zIndex: 999999,
                                fontSize: '18px', fontFamily: 'system-ui, sans-serif'
                            });
                            document.body.appendChild(div);
                        }
                        """)
                    except Exception:
                        pass
                    logger.info(f"Esperando login manual (hasta {args.manual_login_timeout//60} minutos)…")
                    end = time.time() + float(args.manual_login_timeout)
                    while time.time() < end:
                        if wait_for_audio_panel(page, timeout_s=2):
                            break
                        page.wait_for_timeout(1000)
                    # Remove overlay if present
                    try:
                        page.evaluate("() => { const d=document.getElementById('telus-login-overlay'); if(d) d.remove(); }")
                    except Exception:
                        pass
                if not wait_for_audio_panel(page, timeout_s=10):
                    logger.info("No se pudo acceder al panel de audio.")
                    return

        logger.info("Panel de Audio encontrado. Iniciando iteraciones…")
        # Optional diagnostics: dump candidate buttons and media sources
        if args.diagnose:
            try:
                diag = {"frames": []}
                for fr in page.frames:
                    try:
                        data = fr.evaluate(r"""
                        () => {
                            const info = {};
                            info.buttons = Array.from(document.querySelectorAll('button,[role=button]')).slice(0, 100).map(el => ({
                                text: (el.textContent||'').trim().slice(0,200),
                                aria: el.getAttribute('aria-label')||'',
                                title: el.getAttribute('title')||'',
                                cls: el.className||''
                            }));
                            info.media = Array.from(document.querySelectorAll('audio,video')).map((m,i) => ({
                                tag: m.tagName.toLowerCase(),
                                id: m.id||'',
                                cls: m.className||'',
                                src: m.getAttribute('src')||'',
                                currentSrc: m.currentSrc||'',
                                paused: !!m.paused,
                                muted: !!m.muted,
                                volume: m.volume,
                                readyState: m.readyState||0,
                                duration: isFinite(m.duration) ? m.duration : null
                            }));
                            return info;
                        }
                        """)
                        diag["frames"].append(data)
                    except Exception:
                        diag["frames"].append({"error": "frame eval failed"})
                # Add per-label source guesses
                try:
                    diag["src_ref"] = page.evaluate(_js_get_audio_src_for_label('R'))
                except Exception:
                    diag["src_ref"] = None
                try:
                    diag["src_a"] = page.evaluate(_js_get_audio_src_for_label('A'))
                except Exception:
                    diag["src_a"] = None
                try:
                    diag["src_b"] = page.evaluate(_js_get_audio_src_for_label('B'))
                except Exception:
                    diag["src_b"] = None
                diag_path = base_out / f"diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with diag_path.open('w', encoding='utf-8') as f:
                    json.dump(diag, f, ensure_ascii=False, indent=2)
                logger.info(f"Diagnóstico escrito en: {diag_path}")
            except Exception as e:
                logger.warning(f"No se pudo escribir diagnóstico: {e}")
        # Asegurar que elementos <audio> se reproduzcan en silencio si llegan a cargarse
        if not args.no_mute_audio:
            try:
                page.evaluate("() => { document.querySelectorAll('audio').forEach(a => { a.muted = true; a.volume = 0; }); }")
            except Exception:
                pass

        pick_toggle = False
        aborted_due_to_smart = False
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
                smart_ok = False
                last_err: Optional[Exception] = None
                # placeholders para auditoría
                metrics_A: Optional[dict] = None
                metrics_B: Optional[dict] = None
                delta: Optional[float] = None
                # Reintentos locales para manejar "Execution context was destroyed" o latencias de carga
                for attempt in range(max(1, args.smart_retries + 1)):
                    try:
                        # Pequeña espera de estabilidad antes de consultar el DOM/Audio
                        page.wait_for_timeout(int(args.smart_retry_wait * 1000))
                        # Try to grab PCM via hooks or URLs/media across all frames
                        frames = page.frames
                        # Install hooks in all frames
                        for fr in frames:
                            try:
                                fr.evaluate(_js_setup_audio_hooks())
                            except Exception:
                                pass
                        for fr in frames:
                            try:
                                fr.evaluate(_js_setup_deep_audio_hooks())
                            except Exception:
                                pass
                        # Merge audio URLs detected across frames
                        merged_srcs = []
                        for fr in frames:
                            try:
                                part = fr.evaluate(_js_get_audio_srcs())
                                if isinstance(part, list):
                                    merged_srcs.extend(part)
                            except Exception:
                                pass
                        # Mapear por rol
                        urlA = next((s['src'] for s in merged_srcs if s.get('role')=='A'), None)
                        urlB = next((s['src'] for s in merged_srcs if s.get('role')=='B'), None)
                        urlR = next((s['src'] for s in merged_srcs if s.get('role') in ('R','Ref')), None)
                        have_urls = bool(urlA and urlB and urlR)
                        ref = a = b = None
                        # Decide capture path according to mode and availability
                        if args.smart_capture_mode in ("auto", "fetch") and have_urls:
                            ref = page.evaluate(_js_fetch_pcm_from_src(urlR))
                            a = page.evaluate(_js_fetch_pcm_from_src(urlA))
                            b = page.evaluate(_js_fetch_pcm_from_src(urlB))
                        elif args.smart_capture_mode in ("auto", "media"):
                            # Sequential media capture using optional selectors for determinism
                            def _click_label(fr, label: str):
                                if label == 'A' and args.play_a_sel:
                                    return fr.evaluate(_js_click_selector_and_play(args.play_a_sel))
                                if label == 'B' and args.play_b_sel:
                                    return fr.evaluate(_js_click_selector_and_play(args.play_b_sel))
                                if label == 'R' and args.play_ref_sel:
                                    return fr.evaluate(_js_click_selector_and_play(args.play_ref_sel))
                                return fr.evaluate(_js_click_play_for_label(label))

                            def _grab_media_seq(label: str):
                                if args.manual_play:
                                    try:
                                        page.evaluate(_js_overlay_show(f"Haz clic en Play de {label} y no pares la reproducción…"))
                                    except Exception:
                                        pass
                                for fr in frames:
                                    try:
                                        fr.evaluate(_js_set_current_label(label))
                                        _ = _click_label(fr, label)
                                        fr.wait_for_timeout(150)
                                    except Exception:
                                        pass
                                # Try immediate hook capture (deep/fetch/XHR/src interception)
                                try:
                                    for fr in frames:
                                        try:
                                            res = fr.evaluate(_js_grab_pcm_via_hooks(label, args.capture_ms, 1200))
                                            if res and len(res.get('data', [])) >= 256:
                                                try:
                                                    if args.manual_play:
                                                        page.evaluate(_js_overlay_hide())
                                                except Exception:
                                                    pass
                                                return res
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                                # First, try to capture the audio bytes from network response and decode client-side
                                try:
                                    def _is_audio_response(r):
                                        try:
                                            if not r.ok:
                                                return False
                                            url = (r.url or '').lower()
                                            if url.endswith(('.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac')):
                                                return True
                                            ctype = (r.headers.get('content-type', '') or '').lower()
                                            return ('audio/' in ctype) or ('mpegurl' in ctype and url.endswith('.m3u8') == False)
                                        except Exception:
                                            return False
                                    resp = page.wait_for_event('response', _is_audio_response, timeout=4000)
                                    if resp:
                                        try:
                                            body = resp.body()
                                            if body and len(body) > 256:
                                                b64 = base64.b64encode(body).decode('ascii')
                                                decoded = page.evaluate(_js_decode_base64_to_pcm(b64))
                                                if decoded and len(decoded.get('data', [])) >= 256:
                                                    try:
                                                        if args.manual_play:
                                                            page.evaluate(_js_overlay_hide())
                                                    except Exception:
                                                        pass
                                                    return decoded
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                                for fr in frames:
                                    try:
                                        res = fr.evaluate(_js_capture_pcm_from_label(label, args.capture_ms))
                                        if res and len(res.get('data', [])) >= 256:
                                            try:
                                                if args.manual_play:
                                                    page.evaluate(_js_overlay_hide())
                                            except Exception:
                                                pass
                                            return res
                                    except Exception:
                                        pass
                                try:
                                    if args.manual_play:
                                        page.evaluate(_js_overlay_hide())
                                except Exception:
                                    pass
                                return None

                            logger.info("Playback order: Audio A → Audio B → Reference")
                            a = _grab_media_seq('A')
                            b = _grab_media_seq('B')
                            ref = _grab_media_seq('R')
                            # If media failed, fall back to hook-based capture
                            if not ref or not a or not b:
                                def _grab_hooks(label: str):
                                    for fr in frames:
                                        try:
                                            res = fr.evaluate(_js_grab_pcm_via_hooks(label, args.capture_ms))
                                            if res and len(res.get('data', [])) >= 128:
                                                return res
                                        except Exception:
                                            pass
                                    return None
                                ref = ref or _grab_hooks('R')
                                a = a or _grab_hooks('A')
                                b = b or _grab_hooks('B')
                            # If hooks didn't capture, try direct URL fetch via page context base64 decode
                            if not ref or not a or not b:
                                try:
                                    # attempt to get current src per label from any frame
                                    def _get_src(label: str):
                                        # prefer merged URL if present
                                        if label == 'R' and urlR: return urlR
                                        if label == 'A' and urlA: return urlA
                                        if label == 'B' and urlB: return urlB
                                        for fr in frames:
                                            try:
                                                u = fr.evaluate(_js_get_audio_src_for_label(label))
                                                if u: return u
                                            except Exception:
                                                pass
                                        return None
                                    urlR2 = _get_src('R')
                                    urlA2 = _get_src('A')
                                    urlB2 = _get_src('B')
                                    if urlR2 and (not ref or len(ref.get('data', [])) < 128):
                                        try:
                                            resp = page.context.request.get(urlR2)
                                            if resp.ok:
                                                import base64
                                                b64 = base64.b64encode(resp.body()).decode('ascii')
                                                # use main frame to decode
                                                ref = page.evaluate(_js_decode_base64_to_pcm(b64))
                                        except Exception:
                                            pass
                                    if urlA2 and (not a or len(a.get('data', [])) < 128):
                                        try:
                                            resp = page.context.request.get(urlA2)
                                            if resp.ok:
                                                import base64
                                                b64 = base64.b64encode(resp.body()).decode('ascii')
                                                a = page.evaluate(_js_decode_base64_to_pcm(b64))
                                        except Exception:
                                            pass
                                    if urlB2 and (not b or len(b.get('data', [])) < 128):
                                        try:
                                            resp = page.context.request.get(urlB2)
                                            if resp.ok:
                                                import base64
                                                b64 = base64.b64encode(resp.body()).decode('ascii')
                                                b = page.evaluate(_js_decode_base64_to_pcm(b64))
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                            # If hooks/URL didn't capture, fall back to media element capture per frame
                            if not ref or not a or not b:
                                def _grab_media(label: str):
                                    for fr in frames:
                                        try:
                                            res = fr.evaluate(_js_capture_pcm_from_label(label, args.capture_ms))
                                            if res and len(res.get('data', [])) >= 128:
                                                return res
                                        except Exception:
                                            pass
                                    return None
                                ref = ref or _grab_media('R')
                                a = a or _grab_media('A')
                                b = b or _grab_media('B')
                        else:
                            raise Exception('No se detectaron URLs de audio A/B/Ref')
                        # Validate capture results
                        if not ref or not a or not b:
                            raise Exception('Captura de audio incompleta (R/A/B)')
                        ref_sig = np.array(ref.get('data', []), dtype=np.float32)
                        a_sig = np.array(a.get('data', []), dtype=np.float32)
                        b_sig = np.array(b.get('data', []), dtype=np.float32)
                        if ref_sig.size < 256 or a_sig.size < 256 or b_sig.size < 256:
                            raise Exception('PCM insuficiente para comparar (tamaño)')
                        # Silence guard: if any capture is near-silent, treat as failure so we don't Tie wrongly
                        if _sig_is_silent(ref_sig) or _sig_is_silent(a_sig) or _sig_is_silent(b_sig):
                            raise Exception('Captura silenciosa/near-zero en R/A/B')
                        # Identical-capture guard: if A and B are effectively identical and both match Ref, treat as failure
                        try:
                            if _sim_time_corr(a_sig, b_sig) > 0.999 and _rmse(a_sig, b_sig) < 1e-6:
                                if _sim_time_corr(ref_sig, a_sig) > 0.999 and _rmse(ref_sig, a_sig) < 1e-6:
                                    raise Exception('Capturas A/B idénticas y coinciden con Reference (posible fuente única)')
                        except Exception:
                            # If metrics functions throw (shouldn't), ignore and continue
                            pass
                        mA = compute_audio_metrics(ref_sig, a_sig)
                        mB = compute_audio_metrics(ref_sig, b_sig)
                        metrics_A = mA
                        metrics_B = mB
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
                        logger.info(f"Decision taken: {decision}")
                        if abs(delta) < args.tie_diff:
                            decision = "Tie"
                        else:
                            decision = "Version A" if delta > 0 else "Version B"
                        smart_ok = True
                        break
                    except Exception as e:
                        last_err = e
                        # Si aún hay reintentos, esperar y volver a intentar
                        continue
                if not smart_ok:
                    msg = f"SMART no pudo comparar tras reintentos: {last_err}"
                    if args.smart_fail_policy == 'stop':
                        logger.error(msg)
                        aborted_due_to_smart = True
                        # No tomar decisión ni enviar, salir del bucle principal
                        break
                    elif args.smart_fail_policy == 'skip':
                        logger.warning(msg + "; se saltará esta iteración recargando la página.")
                        try:
                            page.reload(wait_until="domcontentloaded")
                            wait_for_audio_panel(page, timeout_s=15)
                        except Exception:
                            pass
                        # No incrementar iteración ni enviar nada
                        continue
                    else:  # fallback
                        logger.warning(msg + "; usando fallback-strategy")
                        if args.fallback_strategy == 'alternate':
                            decision = "Version A" if not pick_toggle else "Version B"
                            pick_toggle = not pick_toggle
                        elif args.fallback_strategy == 'always-a':
                            decision = "Version A"
                        elif args.fallback_strategy == 'always-b':
                            decision = "Version B"
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
                # Compose a richer audit row similar to images audit
                row = {
                    "iter": iterations,
                    "decision": decision,
                    "scoreA": (metrics_A["score"] if 'metrics_A' in locals() and metrics_A else None),
                    "scoreB": (metrics_B["score"] if 'metrics_B' in locals() and metrics_B else None),
                    "delta": (delta if 'delta' in locals() else None),
                    "corrA": (metrics_A["corr_t"] if 'metrics_A' in locals() and metrics_A else None),
                    "cosA": (metrics_A["cos_f"] if 'metrics_A' in locals() and metrics_A else None),
                    "rmseA": (metrics_A["rmse"] if 'metrics_A' in locals() and metrics_A else None),
                    "psnrA": (metrics_A["psnr"] if 'metrics_A' in locals() and metrics_A else None),
                    "klA": (metrics_A["kl"] if 'metrics_A' in locals() and metrics_A else None),
                    "corrB": (metrics_B["corr_t"] if 'metrics_B' in locals() and metrics_B else None),
                    "cosB": (metrics_B["cos_f"] if 'metrics_B' in locals() and metrics_B else None),
                    "rmseB": (metrics_B["rmse"] if 'metrics_B' in locals() and metrics_B else None),
                    "psnrB": (metrics_B["psnr"] if 'metrics_B' in locals() and metrics_B else None),
                    "klB": (metrics_B["kl"] if 'metrics_B' in locals() and metrics_B else None),
                    "tie_diff": args.tie_diff,
                    "timestamp": time.time(),
                }
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
        # Salir con código distinto de cero si se abortó por fallo SMART
        if aborted_due_to_smart:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
