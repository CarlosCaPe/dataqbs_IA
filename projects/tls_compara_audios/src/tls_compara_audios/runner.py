from __future__ import annotations

import argparse
import time
import logging
from pathlib import Path
import csv
from typing import Optional

import numpy as np
from playwright.sync_api import sync_playwright
import json
from urllib.parse import urlparse
import requests

from . import paths  # artifact-aware paths (with migration shim)


def submit_and_next(page) -> bool:
    """Click Submit Evaluation and wait for next item or page reload."""
    btn = _get_submit_button(page)
    if not btn:
        return False
    try:
        btn.click(timeout=2000)
    except Exception:
        return False
    end = time.time() + 8
    while time.time() < end:
        try:
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
        "text= Submit Evaluation",
    ]:
        try:
            btn = page.locator(sel).first
            if btn.is_visible():
                return btn
        except Exception:
            continue
    return None


def setup_logger(log_file: Path | None):
    logger = logging.getLogger("tls_compare_audio")
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
    labels = [
        "Reference Audio", "Reference", "Referencia", "Original",
        "Audio A", "Audio B", "A", "B",
        "Version A", "Version B", "Tie", "Empate"
    ]
    while time.time() < end:
        try:
            if page.query_selector("audio, video"):
                return True
        except Exception:
            pass
        try:
            all_found = 0
            for label in labels:
                try:
                    if page.query_selector(f"*:has-text('{label}')"):
                        all_found += 1
                except Exception:
                    continue
            if all_found >= 2:
                return True
        except Exception:
            pass
        try:
            page.wait_for_timeout(400)
        except Exception:
            pass
    return False


def click_decision(page, decision: str) -> bool:
    candidates = []
    if decision == "Version A":
        candidates = ["Version A", "Versión A", "A"]
    elif decision == "Version B":
        candidates = ["Version B", "Versión B", "B"]
    else:
        candidates = ["Tie", "Empate"]
    deadline = time.time() + 5.0
    while time.time() < deadline:
        for label in candidates:
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
        try:
            page.wait_for_timeout(200)
        except Exception:
            pass
    return False


def _wait_submit_enabled(submit_btn, timeout_ms: int = 5000) -> bool:
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


def _click_refresh(page) -> bool:
    selectors = [
        "text=Refresh",
        "button:has-text('Refresh')",
        "[role=button]:has-text('Refresh')",
        "a:has-text('Refresh')",
        "[aria-label='Refresh']",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el and el.is_visible():
                el.click(timeout=1500)
                return True
        except Exception:
            continue
    return False


def _get_audio_srcs_by_label_js():
    return r"""
    () => {
        function byText(txt) {
            const xpath = `//*[contains(normalize-space(text()), ${JSON.stringify(txt)})]`;
            const x = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
            const nodes = [];
            for (let i=0;i<x.snapshotLength;i++) nodes.push(x.snapshotItem(i));
            return nodes;
        }
        function nearestAudio(el){
            if (!el) return null;
            let n = el;
            for (let depth=0; depth<4 && n; depth++, n=n.parentElement){
                const a = n.querySelector('audio');
                if (a) return a.currentSrc || a.src || null;
            }
            const any = document.querySelector('audio');
            return any ? (any.currentSrc || any.src || null) : null;
        }
        const result = {A:null,B:null,R:null, all:[]};
        const auds = Array.from(document.querySelectorAll('audio'));
        result.all = auds.map(a=>a.currentSrc||a.src||'').filter(Boolean);
        const aNodes = [...byText('Audio A'), ...byText('Audio  A')];
        const bNodes = [...byText('Audio B'), ...byText('Audio  B')];
        const rNodes = [...byText('Reference'), ...byText('Reference Audio'), ...byText('Referencia')];
        result.A = nearestAudio(aNodes[0]);
        result.B = nearestAudio(bNodes[0]);
        result.R = nearestAudio(rNodes[0]);
        return result;
    }
    """


def _get_audio_srcs(page) -> dict:
    try:
        data = page.evaluate(_get_audio_srcs_by_label_js())
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    A = data.get('A') if isinstance(data, dict) else None
    B = data.get('B') if isinstance(data, dict) else None
    R = data.get('R') if isinstance(data, dict) else None
    all_urls = []
    try:
        all_urls = data.get('all') or []
    except Exception:
        all_urls = []
    if not (A and B and R) and len(all_urls) >= 3:
        A, B, R = all_urls[0], all_urls[1], all_urls[2]
    return {"A": A, "B": B, "R": R, "all": all_urls}


def _cookies_for_url(page, url: str) -> dict:
    try:
        cookies = page.context.cookies([url])
    except Exception:
        cookies = []
    jar = {}
    for c in cookies or []:
        try:
            jar[c.get('name')] = c.get('value')
        except Exception:
            continue
    return jar


def _measure_sizes_via_http(page, urls: dict, ua: str | None = None) -> dict:
    out = {k: 0 for k in urls}
    headers_base = {
        "Accept": "*/*",
        "Referer": page.url,
    }
    if ua:
        headers_base["User-Agent"] = ua
    for key, url in urls.items():
        if not url:
            continue
        try:
            _ = urlparse(url)
            cookies = _cookies_for_url(page, url)
            s = requests.Session()
            cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()]) if cookies else None
            headers = dict(headers_base)
            if cookie_header:
                headers["Cookie"] = cookie_header
            total = 0
            try:
                head_headers = dict(headers)
                head_headers.pop("Range", None)
                head_resp = s.head(url, headers=head_headers, timeout=8, allow_redirects=True)
                cl = head_resp.headers.get('Content-Length') or head_resp.headers.get('content-length')
                if cl:
                    total = int(str(cl).strip())
            except Exception:
                total = 0
            if not total:
                try:
                    range_headers = dict(headers)
                    range_headers["Range"] = "bytes=0-0"
                    get_resp = s.get(url, headers=range_headers, stream=True, timeout=12)
                    cr = get_resp.headers.get('Content-Range') or get_resp.headers.get('content-range')
                    if cr and '/' in cr:
                        total = int(cr.split('/')[-1].strip())
                    if not total:
                        cl2 = get_resp.headers.get('Content-Length') or get_resp.headers.get('content-length')
                        if cl2:
                            total = int(str(cl2).strip())
                except Exception:
                    total = 0
            out[key] = max(0, int(total))
        except Exception:
            out[key] = 0
    return out


def _perf_times_for_urls(page, urls: dict) -> dict:
    js = r"""
    (urls) => {
        const res = {};
        try {
            const entries = performance.getEntriesByType('resource') || [];
            for (const [key, url] of Object.entries(urls||{})){
                if (!url) { res[key] = 0; continue; }
                const list = performance.getEntriesByName(url) || [];
                const e = list.length ? list[list.length-1] : null;
                let dur = 0;
                if (e) dur = e.duration || (e.responseEnd - e.startTime) || 0;
                res[key] = dur * 1.0;
            }
        } catch (e) {
            for (const k of Object.keys(urls||{})) res[k] = 0;
        }
        return res;
    }
    """
    try:
        return page.evaluate(js, {k: v for k, v in urls.items()})
    except Exception:
        return {k: 0 for k in urls}


def _perf_get_last3_media_urls(page) -> list[str]:
    js = r"""
    () => {
        try {
            const all = performance.getEntriesByType('resource') || [];
            const media = all.filter(e => {
                const name = (e.name||'').toLowerCase();
                const it = (e.initiatorType||'').toLowerCase();
                return it === 'media' || /\.(wav|mp3|m4a|aac|ogg|opus|flac|webm)(\?|$)/.test(name);
            }).map(e => ({ url: e.name || '', start: e.startTime||0 }));
            media.sort((a,b)=> (a.start||0)-(b.start||0));
            return media.slice(-3).map(m=>m.url);
        } catch (e) { return []; }
    }
    """
    try:
        urls = page.evaluate(js)
        return [u for u in urls if isinstance(u, str) and u]
    except Exception:
        return []


def _js_setup_audio_hooks():
    return r"""
    () => {
        if (window.__tlsHooksInstalled) return true;
        window.__tlsPCM = window.__tlsPCM || {};
        window.__tlsHooksInstalled = true;
        const C = window.AudioContext || window.webkitAudioContext;
        if (!C) return false;
        const proto = C.prototype;
        const origDecode = proto.decodeAudioData;
        if (origDecode && !proto.__tlsDecodePatched) {
            proto.__tlsDecodePatched = true;
            proto.decodeAudioData = function(buffer, successCb, errorCb){
                try {
                    const self = this;
                    if (typeof successCb === 'function') {
                        return origDecode.call(self, buffer, function(audioBuffer){
                            try {
                                const lab = window.__tlsCurrentLabel;
                                if (lab && audioBuffer && audioBuffer.getChannelData) {
                                    const ch0 = audioBuffer.getChannelData(0);
                                    window.__tlsPCM[lab] = { data: Array.from(ch0), sampleRate: self.sampleRate };
                                }
                            } catch (e) {}
                            return successCb(audioBuffer);
                        }, errorCb);
                    }
                    const p = origDecode.call(self, buffer);
                    return p.then(audioBuffer => {
                        try {
                            const lab = window.__tlsCurrentLabel;
                            if (lab && audioBuffer && audioBuffer.getChannelData) {
                                const ch0 = audioBuffer.getChannelData(0);
                                window.__tlsPCM[lab] = { data: Array.from(ch0), sampleRate: self.sampleRate };
                            }
                        } catch (e) {}
                        return audioBuffer;
                    });
                } catch (e) {
                    return origDecode.apply(this, arguments);
                }
            }
        }
        const origCreate = proto.createBufferSource;
        if (origCreate && !proto.__tlsCreatePatched) {
            proto.__tlsCreatePatched = true;
            proto.createBufferSource = function(){
                const node = origCreate.call(this);
                try {
                    const origStart = node.start.bind(node);
                    node.start = function(){
                        try {
                            const lab = window.__tlsCurrentLabel;
                            if (lab && node.buffer && node.buffer.getChannelData) {
                                const ch0 = node.buffer.getChannelData(0);
                                window.__tlsPCM[lab] = { data: Array.from(ch0), sampleRate: node.context.sampleRate };
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
        if (window.__tlsDeepHooksInstalled) return true;
        window.__tlsPCM = window.__tlsPCM || {};
        window.__tlsDeepHooksInstalled = true;
        const Ctor = window.AudioContext || window.webkitAudioContext;
        function downsampleAndStore(label, audioBuffer) {
            try {
                const sr = audioBuffer.sampleRate;
                const step = Math.max(1, Math.floor(sr / 22050));
                const ch0 = audioBuffer.getChannelData(0);
                const out = [];
                for (let i = 0; i < ch0.length; i += step) out.push(ch0[i]);
                window.__tlsPCM[label] = { sampleRate: sr/step, data: out };
            } catch (e) { /* noop */ }
        }
        async function decodeAndStore(label, arrayBuffer) {
            try {
                const ctx = window.__tlsCtx || new Ctor();
                window.__tlsCtx = ctx;
                const buf = arrayBuffer.slice ? arrayBuffer.slice(0) : arrayBuffer;
                const ab = await ctx.decodeAudioData(buf);
                downsampleAndStore(label, ab);
            } catch (e) { /* noop */ }
        }
        if (!window.__tlsFetchPatched) {
            window.__tlsFetchPatched = true;
            const origFetch = window.fetch;
            window.fetch = async function() {
                const label = window.__tlsCurrentLabel || 'U';
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
        if (!window.__tlsXHRPatched) {
            window.__tlsXHRPatched = true;
            const OrigXHR = window.XMLHttpRequest;
            function wrapXHR() {
                const xhr = new OrigXHR();
                const label = window.__tlsCurrentLabel || 'U';
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
        if (!window.__tlsCreateObjURLPatched) {
            window.__tlsCreateObjURLPatched = true;
            const orig = URL.createObjectURL;
            URL.createObjectURL = function(obj) {
                try {
                    const label = window.__tlsCurrentLabel || 'U';
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
        if (!window.__tlsMediaSrcPatched) {
            window.__tlsMediaSrcPatched = true;
            const proto = HTMLMediaElement.prototype;
            const desc = Object.getOwnPropertyDescriptor(proto, 'src');
            if (desc && desc.set) {
                const origSet = desc.set;
                Object.defineProperty(proto, 'src', {
                    set(value) {
                        try {
                            const label = window.__tlsCurrentLabel || 'U';
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
                        const label = window.__tlsCurrentLabel || 'U';
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
    () => {{ window.__tlsCurrentLabel = '{safe_key}'; return true; }}
    """


def _js_grab_pcm_via_hooks(label_key: str, duration_ms: int, timeout_ms: int = 2500):
    safe_key = label_key.replace("'", "")
    return f"""
    async () => {{
        window.__tlsPCM = window.__tlsPCM || {{}};
        window.__tlsCurrentLabel = '{safe_key}';
        delete window.__tlsPCM['{safe_key}'];
        const t0 = performance.now();
        while ((performance.now() - t0) < {timeout_ms}) {{
            const rec = window.__tlsPCM['{safe_key}'];
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
        window.__tlsCurrentLabel = '__KEY__';
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
        const cand = container.querySelector('[data-src],[data-url],[data-audio],[data-href]');
        if (cand) return cand.getAttribute('data-src') || cand.getAttribute('data-url') || cand.getAttribute('data-audio') || cand.getAttribute('data-href');
        const a = container.querySelector('a[href$=".mp3"],a[href$=".wav"],a[href*="audio" i]');
        if (a) return a.href;
        return null;
    }
    """.replace('__KEY__', safe_key)


def _js_head_or_range_size(url: str):
    safe_url = url.replace("'", "%27")
    return f"""
    async () => {{
        const url = '{safe_url}';
        try {{
            const head = await fetch(url, {{ method: 'HEAD', credentials: 'include' }});
            if (head && head.ok) {{
                const cl = head.headers.get('content-length');
                if (cl) {{
                    const n = parseInt(cl, 10);
                    if (!Number.isNaN(n) && n > 0) return n;
                }}
            }}
        }} catch (e) {{ /* ignore */ }}
        try {{
            const res = await fetch(url, {{ method: 'GET', headers: {{ 'Range': 'bytes=0-0' }}, credentials: 'include' }});
            if (res && res.ok) {{
                const cr = res.headers.get('content-range') || '';
                const slash = cr.lastIndexOf('/')
                if (slash > -1) {{
                    const part = cr.substring(slash + 1).trim();
                    const n = parseInt(part, 10);
                    if (!Number.isNaN(n) && n > 0) return n;
                }}
                const cl = res.headers.get('content-length');
                if (cl) {{
                    const n = parseInt(cl, 10);
                    if (!Number.isNaN(n) && n > 0) return n;
                }}
            }}
        }} catch (e) {{ /* ignore */ }}
        return 0;
    }}
    """


def _header_sizes_kb_for_current(page) -> dict:
    sizes_kb = {"A": 0.0, "B": 0.0, "R": 0.0}
    try:
        srcs = _get_audio_srcs(page)
        urls = {"A": srcs.get("A"), "B": srcs.get("B"), "R": srcs.get("R")}
        ua = None
        try:
            ua = page.evaluate("() => navigator.userAgent")
        except Exception:
            ua = None
        sizes = _measure_sizes_via_http(page, urls, ua=ua)
        for k in ("A","B","R"):
            v = sizes.get(k) or 0
            try:
                sizes_kb[k] = float(int(v)) / 1024.0
            except Exception:
                sizes_kb[k] = 0.0
    except Exception:
        pass
    return sizes_kb


def _collect_media_via_perf(page) -> list[dict]:
    js = r"""
    () => {
        try {
            const all = performance.getEntriesByType('resource') || [];
            const media = all.filter(e => {
                const name = (e.name||'').toLowerCase();
                const it = (e.initiatorType||'').toLowerCase();
                return it === 'media' || /\.(wav|mp3|m4a|aac|ogg|opus|flac|webm)(\?|$)/.test(name);
            }).map(e => ({
                url: e.name || '',
                size: e.transferSize || e.encodedBodySize || e.decodedBodySize || 0,
                time: (e.duration || (e.responseEnd - e.startTime) || 0) * 1.0,
                start: e.startTime || 0
            }));
            media.sort((a,b) => (a.start||0) - (b.start||0));
            return media.slice(-3);
        } catch (err) {
            return [];
        }
    }
    """
    try:
        items = page.evaluate(js)
    except Exception:
        items = []
    out = []
    for it in (items or []):
        try:
            out.append({
                "url": it.get("url"),
                "bytes": int(float(it.get("size") or 0)),
                "time": float(it.get("time") or 0.0),
                "start": float(it.get("start") or 0.0)
            })
        except Exception:
            continue
    return out


def _collect_media_via_context(context, page, logger, timeout_s: int = 12) -> list[dict]:
    records = []
    store = {}

    def _size_from_headers(headers: dict) -> int:
        if not headers:
            return 0
        h = {str(k).lower(): v for k, v in headers.items()}
        cr = h.get('content-range')
        if cr and '/' in cr:
            try:
                total = int(cr.split('/')[-1].strip())
                return total
            except Exception:
                pass
        cl = h.get('content-length')
        try:
            return int(str(cl).strip()) if cl else 0
        except Exception:
            return 0

    def on_req(req):
        try:
            store[req] = {
                'url': req.url,
                'start': time.time(),
                'rtype': (req.resource_type or '').lower(),
            }
        except Exception:
            pass

    def on_resp(resp):
        try:
            req = resp.request
            rec = store.get(req)
            if not rec:
                return
            headers = resp.headers or {}
            size = _size_from_headers(headers)
            mime = str(headers.get('content-type') or headers.get('Content-Type') or '').lower()
            st = int(resp.status or 0)
            rec.update({'status': st, 'mime': mime, 'bytes': size})
        except Exception:
            pass

    def on_done(req):
        try:
            rec = store.get(req)
            if not rec:
                return
            rec['end'] = time.time()
            url = (rec.get('url') or '').lower()
            has_audio_ext = any(ext in url for ext in ['.wav','.mp3','.m4a','.aac','.ogg','.opus','.flac','.webm'])
            looks_audio = has_audio_ext or (rec.get('mime') or '').startswith('audio') or (rec.get('rtype') == 'media')
            st = int(rec.get('status') or 0)
            if looks_audio and st in (200,206):
                records.append(rec)
        except Exception:
            pass

    context.on('request', on_req)
    context.on('response', on_resp)
    context.on('requestfinished', on_done)

    try:
        clicked = _click_refresh(page)
        if not clicked:
            page.evaluate("() => { const as = Array.from(document.querySelectorAll('audio')); as.forEach(a=>{try{a.load&&a.load()}catch{}}); }")
    except Exception:
        pass

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if len(records) >= 3:
            break
        try:
            page.wait_for_timeout(200)
        except Exception:
            pass

    try:
        context.remove_listener('request', on_req)
        context.remove_listener('response', on_resp)
        context.remove_listener('requestfinished', on_done)
    except Exception:
        pass

    return records


def _decide_by_cdp_media(page, logger, timeout_s: int = 15) -> Optional[str]:
    try:
        session = page.context.new_cdp_session(page)
    except Exception:
        return None
    try:
        session.send("Network.enable", {})
        session.send("Network.setCacheDisabled", {"cacheDisabled": True})
        try:
            session.send("Network.clearBrowserCache", {})
        except Exception:
            pass
        session.send("Target.setAutoAttach", {
            "autoAttach": True,
            "waitForDebuggerOnStart": False,
            "flatten": True
        })
    except Exception:
        pass

    entries = {}

    def on_request(e):
        try:
            req_id = e.get("requestId")
            req = e.get("request", {})
            url = (req.get("url") or "")
            rtype = (e.get("type") or "").lower()
            data = entries.setdefault(req_id, {})
            data.update({
                "url": url,
                "start": float(e.get("timestamp") or 0.0),
                "rtype": rtype,
            })
        except Exception:
            pass

    def on_response(e):
        try:
            req_id = e.get("requestId")
            resp = e.get("response", {})
            status = int(resp.get("status") or 0)
            mime = (resp.get("mimeType") or "").lower()
            headers = resp.get("headers") or {}
            cl = headers.get("content-length") or headers.get("Content-Length")
            data = entries.setdefault(req_id, {})
            data["status"] = status
            data["mime"] = mime
            if cl is not None:
                try:
                    data["bytes_header"] = int(str(cl).strip())
                except Exception:
                    pass
        except Exception:
            pass

    def on_finished(e):
        try:
            req_id = e.get("requestId")
            ts = float(e.get("timestamp") or 0.0)
            enc = e.get("encodedDataLength")
            data = entries.setdefault(req_id, {})
            data["end"] = ts
            try:
                if isinstance(enc, (int, float)):
                    data["bytes_encoded"] = int(enc)
            except Exception:
                pass
        except Exception:
            pass

    def on_data(e):
        try:
            req_id = e.get("requestId")
            data_len = e.get("dataLength")
            enc_len = e.get("encodedDataLength")
            d = entries.setdefault(req_id, {})
            prev = int(d.get("bytes_data") or 0)
            add = 0
            try:
                if isinstance(enc_len, (int, float)) and enc_len > 0:
                    add = int(enc_len)
                elif isinstance(data_len, (int, float)) and data_len > 0:
                    add = int(data_len)
            except Exception:
                add = 0
            d["bytes_data"] = prev + add
        except Exception:
            pass

    def _apply_headers_to_entry(req_id, headers):
        if not headers:
            return
        d = entries.setdefault(req_id, {})
        h = {str(k).lower(): v for k, v in headers.items()}
        cl = h.get("content-length")
        if cl is not None:
            try:
                d["bytes_header"] = int(str(cl).strip())
            except Exception:
                pass
        cr = h.get("content-range")
        if cr and "/" in cr:
            try:
                total = cr.split("/")[-1].strip()
                if total.isdigit():
                    d["bytes_total"] = int(total)
            except Exception:
                pass

    session.on("Network.requestWillBeSent", on_request)
    session.on("Network.responseReceived", lambda e: (on_response(e), _apply_headers_to_entry(e.get("requestId"), (e.get("response") or {}).get("headers"))) )
    session.on("Network.responseReceivedExtraInfo", lambda e: _apply_headers_to_entry(e.get("requestId"), e.get("headers")))
    session.on("Network.loadingFinished", on_finished)
    session.on("Network.dataReceived", on_data)

    def _send_to_target(session_id: str, method: str, params: dict | None = None):
        try:
            msg = {"id": int(time.time()*1000)%1000000, "method": method}
            if params:
                msg["params"] = params
            session.send("Target.sendMessageToTarget", {"sessionId": session_id, "message": json.dumps(msg)})
        except Exception:
            pass

    session.on("Target.attachedToTarget", lambda e: _send_to_target(e.get("sessionId"), "Network.enable", {}))

    def _on_msg_from_target(e):
        try:
            raw = e.get("message")
            if not raw:
                return
            msg = json.loads(raw)
            method = msg.get("method")
            params = msg.get("params") or {}
            if method == "Network.requestWillBeSent":
                on_request(params)
            elif method == "Network.responseReceived":
                on_response(params)
                try:
                    _apply_headers_to_entry(params.get("requestId"), ((params.get("response") or {}).get("headers") or {}))
                except Exception:
                    pass
            elif method == "Network.loadingFinished":
                on_finished(params)
            elif method == "Network.dataReceived":
                on_data(params)
        except Exception:
            pass
    session.on("Target.receivedMessageFromTarget", _on_msg_from_target)

    tried_refresh = False
    try:
        tried_refresh = _click_refresh(page)
    except Exception:
        tried_refresh = False
    if not tried_refresh:
        try:
            session.send("Page.reload", {"ignoreCache": True})
        except Exception:
            try:
                page.reload(wait_until="domcontentloaded")
            except Exception:
                pass

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(0.1)
        fins = []
        for d in entries.values():
            if ("start" in d) and ("end" in d):
                st = int(d.get("status") or 0)
                ok_status = (st == 206 or st == 200)
                size = int(d.get("bytes_total") or d.get("bytes_header") or d.get("bytes_encoded") or d.get("bytes_data") or 0)
                url = (d.get("url") or "").lower()
                mime = (d.get("mime") or "").lower()
                rtype = (d.get("rtype") or "").lower()
                has_audio_ext = any(ext in url for ext in [
                    ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".webm"
                ])
                looks_audio = has_audio_ext or mime.startswith("audio") or (rtype == "media")
                if ok_status and looks_audio and not mime.startswith("image"):
                    fins.append(d)
        if len(fins) >= 3:
            fins.sort(key=lambda x: x.get("start", 0.0))
            fins = fins[-3:]
            A, B, R = fins[0], fins[1], fins[2]
            def size_kb(d):
                sz = int(d.get("bytes_total") or d.get("bytes_header") or d.get("bytes_encoded") or d.get("bytes_data") or 0)
                return sz / 1024.0
            def time_ms(d):
                return max(0.0, (float(d.get("end") or 0.0) - float(d.get("start") or 0.0)) * 1000.0)
            sizes = [size_kb(A), size_kb(B), size_kb(R)]
            times = [time_ms(A), time_ms(B), time_ms(R)]
            r_idx = int(max(range(3), key=lambda i: sizes[i]))
            if r_idx != 2:
                order = [0,1,2]
                order.remove(r_idx)
                order.append(r_idx)
                A, B, R = [ [A,B,R][i] for i in order ]
                sizes = [ sizes[i] for i in order ]
                times = [ times[i] for i in order ]
            sa, sb, sr = sizes[0], sizes[1], sizes[2]
            ta, tb, tr = times[0], times[1], times[2]
            def closeness(sx, tx):
                ns = abs(sx - sr) / max(sr, 1e-6)
                nt = abs(tx - tr) / max(tr, 1e-6)
                return 0.7 * ns + 0.3 * nt
            ca = closeness(sa, ta)
            cb = closeness(sb, tb)
            if abs(ca - cb) <= 0.01:
                return "Tie"
            elif ca < cb:
                return "Version A"
            else:
                return "Version B"
    return None


def main():
    parser = argparse.ArgumentParser(description="Automatiza comparaciones de calidad de audio (TLS)")
    parser.add_argument("--headed", action="store_true", help="Abrir navegador con UI")
    parser.add_argument("--delay-seconds", type=int, default=1, help="Retardo humano por iteración (s)")
    parser.add_argument("--max-iters", type=int, default=3, help="Máximo de iteraciones (0 = ilimitado)")
    parser.add_argument("--log-file", type=str, default=str(paths.LOGS_DIR / "run.log"), help="Ruta del log (por defecto artifacts/tls_compara_audios/logs/run.log)")
    parser.add_argument("--header-first", action="store_true", help="Preferir tamaños totales por headers (Content-Range/Length) usando los src del DOM")
    parser.add_argument("--urls", nargs='*', help="Opcional: pasar 3 URLs WAV (A B R) para calcular tamaños por headers sin navegador")
    parser.add_argument("--audit-csv", type=str, default=str(paths.OUTPUTS_DIR / "audit" / "decisions.csv"), help="Ruta de CSV para auditar decisiones/medidas (default en artifacts)")
    parser.add_argument("--audit-limit", type=int, default=0, help="Máximo de filas a guardar en CSV (0 = todas)")
    parser.add_argument("--audit-batch", type=int, default=1, help="Escribir el CSV cada N iteraciones (1 = cada iteración)")
    parser.add_argument("--url", type=str, default="https://www.multimango.com/tasks/080825-audio-quality-compare", help="URL de la tarea")
    args = parser.parse_args()

    log_path = Path(args.log_file) if args.log_file else None
    logger = setup_logger(log_path)

    default_csv = paths.OUTPUTS_DIR / "audit" / "decisions.csv"
    csv_path = Path(args.audit_csv) if args.audit_csv else default_csv
    csv_rows: list[dict] = []

    if args.urls and len(args.urls) >= 3:
        urls_list = args.urls[:3]
        urls = {"A": urls_list[0], "B": urls_list[1], "R": urls_list[2]}
        def size_for(u: str) -> int:
            try:
                s = requests.Session()
                try:
                    r = s.head(u, timeout=10, allow_redirects=True)
                    cl = r.headers.get('Content-Length') or r.headers.get('content-length')
                    if cl:
                        return int(str(cl).strip())
                except Exception:
                    pass
                try:
                    r = s.get(u, headers={"Range": "bytes=0-0"}, stream=True, timeout=15)
                    cr = r.headers.get('Content-Range') or r.headers.get('content-range')
                    if cr and '/' in cr:
                        return int(cr.split('/')[-1].strip())
                    cl2 = r.headers.get('Content-Length') or r.headers.get('content-length')
                    if cl2:
                        return int(str(cl2).strip())
                except Exception:
                    pass
            except Exception:
                return 0
            return 0
        sizes = {k: size_for(v) for k, v in urls.items()}
        kb = {k: (v/1024.0 if v else 0.0) for k, v in sizes.items()}
        print(f"Header sizes -> R:{kb['R']:.1f} kB A:{kb['A']:.1f} kB B:{kb['B']:.1f} kB (bytes R:{sizes['R']} A:{sizes['A']} B:{sizes['B']})")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed, devtools=False)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.set_default_timeout(2000)
            page.set_default_navigation_timeout(10000)
        except Exception:
            pass
        page.goto(args.url, wait_until="domcontentloaded")

        if not wait_for_audio_panel(page, timeout_s=15):
            logger.error("No se encontró el panel de audio. Verifica login o URL.")
            return

        iterations = 0
        while args.max_iters == 0 or iterations < args.max_iters:
            decision = None
            iter_sizes_kb = None
            iter_source = None

            if args.header_first and not decision:
                try:
                    srcs = _get_audio_srcs(page)
                    urls = {"A": srcs.get("A"), "B": srcs.get("B"), "R": srcs.get("R")}
                    ua = None
                    try:
                        ua = page.evaluate("() => navigator.userAgent")
                    except Exception:
                        ua = None
                    sizes = _measure_sizes_via_http(page, urls, ua=ua)
                    times = _perf_times_for_urls(page, urls)
                    vals = [sizes.get("A",0), sizes.get("B",0), sizes.get("R",0)]
                    tvals = [times.get("A",0.0), times.get("B",0.0), times.get("R",0.0)]
                    if sum(1 for v in vals if v>0) >= 2:
                        sizes_kb = [v/1024.0 for v in vals]
                        r_idx = int(max(range(3), key=lambda i: sizes_kb[i]))
                        order = [0,1,2]
                        if r_idx != 2:
                            order.remove(r_idx)
                            order.append(r_idx)
                            sizes_kb = [sizes_kb[i] for i in order]
                            tvals = [tvals[i] for i in order]
                        sa,sb,sr = sizes_kb[0], sizes_kb[1], sizes_kb[2]
                        ta,tb,tr = tvals[0], tvals[1], tvals[2]
                        def closeness(sx, tx):
                            ns = abs(sx - sr) / max(sr, 1e-6)
                            nt = abs(tx - tr) / max(tr, 1e-6)
                            return 0.7*ns + 0.3*nt
                        ca,cb = closeness(sa,ta), closeness(sb,tb)
                        decision = 'Tie' if abs(ca-cb)<=0.01 else ('Version A' if ca<cb else 'Version B')
                        iter_source = 'header-first'
                        iter_sizes_kb = (sr, sa, sb)
                        logger.debug(f"Header media (kB/ms) -> R:({sr:.0f}kB,{tr:.0f}ms) A:({sa:.0f}kB,{ta:.0f}ms) B:({sb:.0f}kB,{tb:.0f}ms) => {decision}")
                except Exception:
                    decision = None

            try:
                dec_net = _decide_by_cdp_media(page, logger, timeout_s=10)
            except Exception:
                dec_net = None
            if dec_net:
                decision = dec_net
                iter_source = iter_source or 'cdp'

            if not decision:
                try:
                    last3 = _perf_get_last3_media_urls(page)
                    if len(last3) == 3:
                        urls = {"A": last3[0], "B": last3[1], "R": last3[2]}
                        ua = None
                        try:
                            ua = page.evaluate("() => navigator.userAgent")
                        except Exception:
                            ua = None
                        sizes = _measure_sizes_via_http(page, urls, ua=ua)
                        times = _perf_times_for_urls(page, urls)
                        vals = [sizes.get("A",0), sizes.get("B",0), sizes.get("R",0)]
                        tvals = [times.get("A",0.0), times.get("B",0.0), times.get("R",0.0)]
                        if sum(1 for v in vals if v>0) >= 2:
                            sizes_kb = [v/1024.0 for v in vals]
                            times_ms = tvals
                            r_idx = int(max(range(3), key=lambda i: sizes_kb[i]))
                            order = [0,1,2]
                            if r_idx != 2:
                                order.remove(r_idx)
                                order.append(r_idx)
                                sizes_kb = [sizes_kb[i] for i in order]
                                times_ms = [times_ms[i] for i in order]
                            sa,sb,sr = sizes_kb
                            ta,tb,tr = times_ms
                            def closeness(sx, tx):
                                ns = abs(sx - sr) / max(sr, 1e-6)
                                nt = abs(tx - tr) / max(tr, 1e-6)
                                return 0.7*ns + 0.3*nt
                            ca,cb = closeness(sa,ta), closeness(sb,tb)
                            decision = 'Tie' if abs(ca-cb)<=0.01 else ('Version A' if ca<cb else 'Version B')
                            iter_source = 'perf-http'
                            iter_sizes_kb = (sr, sa, sb)
                            logger.debug(f"Perf last3+HTTP -> R:{sr:.0f}kB A:{sa:.0f}kB B:{sb:.0f}kB => {decision}")
                except Exception:
                    decision = None

            if not decision:
                try:
                    srcs = _get_audio_srcs(page)
                    urls = {"A": srcs.get("A"), "B": srcs.get("B"), "R": srcs.get("R")}
                    ua = None
                    try:
                        ua = page.evaluate("() => navigator.userAgent")
                    except Exception:
                        ua = None
                    sizes = _measure_sizes_via_http(page, urls, ua=ua)
                    times = _perf_times_for_urls(page, urls)
                    vals = [sizes.get("A",0), sizes.get("B",0), sizes.get("R",0)]
                    tvals = [times.get("A",0.0), times.get("B",0.0), times.get("R",0.0)]
                    if sum(1 for v in vals if v>0) >= 2 and all(t>=0 for t in tvals):
                        sizes_kb = [val/1024.0 for val in vals]
                        times_ms = tvals
                        r_idx = int(max(range(3), key=lambda i: sizes_kb[i]))
                        order = [0,1,2]
                        if r_idx != 2:
                            order.remove(r_idx)
                            order.append(r_idx)
                            sizes_kb = [sizes_kb[i] for i in order]
                            times_ms = [times_ms[i] for i in order]
                        sa,sb,sr = sizes_kb[0], sizes_kb[1], sizes_kb[2]
                        ta,tb,tr = times_ms[0], times_ms[1], times_ms[2]
                        def closeness(sx, tx):
                            ns = abs(sx - sr) / max(sr, 1e-6)
                            nt = abs(tx - tr) / max(tr, 1e-6)
                            return 0.7*ns + 0.3*nt
                        ca = closeness(sa,ta)
                        cb = closeness(sb,tb)
                        if abs(ca-cb) <= 0.01:
                            decision = "Tie"
                        elif ca < cb:
                            decision = "Version A"
                        else:
                            decision = "Version B"
                        iter_source = 'dom-http'
                        iter_sizes_kb = (sr, sa, sb)
                        logger.debug(f"DOM srcs+HTTP -> R:{sr:.0f}kB A:{sa:.0f}kB B:{sb:.0f}kB => {decision}")
                except Exception:
                    decision = None
                if not decision:
                    logger.warning("No se detectaron 3 entradas Media tras CDP/Page/Perf. Declarando Tie.")
                    decision = "Tie"

            if not iter_sizes_kb:
                try:
                    hdr = _header_sizes_kb_for_current(page)
                    iter_sizes_kb = (hdr.get('R', 0.0), hdr.get('A', 0.0), hdr.get('B', 0.0))
                    if (iter_sizes_kb[0] == 0.0 and iter_sizes_kb[1] == 0.0 and iter_sizes_kb[2] == 0.0):
                        try:
                            last3 = _perf_get_last3_media_urls(page)
                            if len(last3) == 3:
                                urls = {"A": last3[0], "B": last3[1], "R": last3[2]}
                                ua = None
                                try:
                                    ua = page.evaluate("() => navigator.userAgent")
                                except Exception:
                                    ua = None
                                sizes = _measure_sizes_via_http(page, urls, ua=ua)
                                iter_sizes_kb = (float(int(sizes.get('R') or 0))/1024.0,
                                                 float(int(sizes.get('A') or 0))/1024.0,
                                                 float(int(sizes.get('B') or 0))/1024.0)
                                if not iter_source:
                                    iter_source = 'perf-http'
                        except Exception:
                            pass
                except Exception:
                    pass

            wait_for_audio_panel(page, timeout_s=3)
            if not click_decision(page, decision):
                logger.warning("No se pudo hacer clic en la decisión. Abortando.")
                break
            submit_btn = _get_submit_button(page)
            if not _wait_submit_enabled(submit_btn, timeout_ms=8000):
                logger.warning("Botón Submit no habilitado a tiempo.")
                break
            time.sleep(0.3)
            if not submit_and_next(page):
                logger.warning("No se pudo enviar/avanzar.")
                break

            try:
                if not iter_sizes_kb:
                    hdr = _header_sizes_kb_for_current(page)
                    iter_sizes_kb = (hdr.get('R', 0.0), hdr.get('A', 0.0), hdr.get('B', 0.0))
            except Exception:
                iter_sizes_kb = iter_sizes_kb or (0.0, 0.0, 0.0)
            try:
                sr_kb, sa_kb, sb_kb = iter_sizes_kb or (0.0, 0.0, 0.0)
                logger.info(f"Iter {iterations + 1} -> Sizes kB R:{sr_kb:.0f} A:{sa_kb:.0f} B:{sb_kb:.0f} | Decision: {decision}")
                if csv_path:
                    row = {
                        "iter": iterations + 1,
                        "decision": decision,
                        "sizeR_kB": round(float(sr_kb), 1),
                        "sizeA_kB": round(float(sa_kb), 1),
                        "sizeB_kB": round(float(sb_kb), 1),
                        "source": iter_source or "unknown",
                        "timestamp": time.time(),
                    }
                    csv_rows.append(row)
                    if args.audit_limit and len(csv_rows) > args.audit_limit:
                        csv_rows = csv_rows[-args.audit_limit:]
                    if (args.audit_batch <= 1) or (((iterations + 1) % args.audit_batch) == 0):
                        try:
                            csv_path.parent.mkdir(parents=True, exist_ok=True)
                            with csv_path.open("w", newline="", encoding="utf-8") as f:
                                writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                                writer.writeheader()
                                writer.writerows(csv_rows)
                        except Exception:
                            pass
            except Exception:
                pass

            iterations += 1
            time.sleep(max(0, args.delay_seconds))

        try:
            context.close()
            browser.close()
        except Exception:
            pass

    logger.info("Proceso completado.")


if __name__ == "__main__":
    main()
