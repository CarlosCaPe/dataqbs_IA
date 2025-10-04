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
    """Click the decision button (Version A, Version B, Tie/Empate) in the UI.
    Waits briefly for the button to become visible/clickable.
    """
    candidates = []
    if decision == "Version A":
        candidates = ["Version A", "Versión A", "A"]
    elif decision == "Version B":
        candidates = ["Version B", "Versión B", "B"]
    else:  # Tie
        candidates = ["Tie", "Empate"]

    # Poll up to ~5s for a visible button
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
from urllib.parse import urlparse
import requests


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


def _header_sizes_kb_for_current(page) -> dict:
    """Return header-based total sizes in kB for current A/B/R audio srcs.
    Uses HEAD/Content-Length or GET Range/Content-Range as needed.
    """
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


def wait_for_audio_panel(page, timeout_s: int = 30) -> bool:
    end = time.time() + timeout_s
    labels = [
        # Audio controls
        "Reference Audio", "Reference", "Referencia", "Original",
        "Audio A", "Audio B", "A", "B",
        # Decision buttons
        "Version A", "Version B", "Tie", "Empate"
    ]
    while time.time() < end:
        try:
            # direct audio element present is a strong signal
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
def _click_refresh(page) -> bool:
    """Try to click the task's Refresh control to load new audio clips.
    Returns True if a click was attempted successfully.
    """
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

def _collect_media_via_page(page, logger, timeout_s: int = 12) -> list[dict]:
    """Fallback: use Playwright page events to capture media/audios.
    Returns a list of dicts with url, start, end, status, mime, bytes, rtype.
    """
    start_deadline = time.time() + timeout_s
    store = {}
    results = []

    def _try_size_from_headers(headers: dict) -> int:
        if not headers:
            return 0
        h = {str(k).lower(): v for k, v in headers.items()}
        # Content-Range total
        cr = h.get("content-range")
        if cr and "/" in cr:
            try:
                total = cr.split("/")[-1].strip()
                if total.isdigit():
                    return int(total)
            except Exception:
                pass
        cl = h.get("content-length")
        try:
            return int(str(cl).strip()) if cl else 0
        except Exception:
            return 0

    def on_request(req):
        try:
            url = (req.url or "")
            rtype = (req.resource_type or "").lower()
            # Track all potentially relevant requests; filter later by response
            store[req] = {
                "url": url,
                "start": time.time(),
                "rtype": rtype,
            }
        except Exception:
            pass

    def _finalize_from_resp(req, resp):
        try:
            rec = store.get(req)
            if not rec:
                return
            status = int(resp.status or 0)
            headers = resp.headers or {}
            size = _try_size_from_headers(headers)
            ctype = str(headers.get("content-type") or headers.get("Content-Type") or "").lower()
            mime = ctype
            rec.update({
                "end": time.time(),
                "status": status,
                "mime": mime,
                "bytes": size,
            })
            url_lower = rec["url"].lower()
            has_audio_ext = any(ext in url_lower for ext in [
                ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".webm"
            ])
            looks_audio = has_audio_ext or mime.startswith("audio") or (rec.get("rtype") == "media")
            ok_status = status in (200, 206)
            if looks_audio and ok_status:
                results.append(rec)
        except Exception:
            pass

    def on_finished(req):
        try:
            resp = req.response()
            if resp:
                _finalize_from_resp(req, resp)
        except Exception:
            pass

    def on_response(resp):
        try:
            req = resp.request
            if req in store:
                _finalize_from_resp(req, resp)
        except Exception:
            pass

    page.on("request", on_request)
    page.on("requestfinished", on_finished)
    page.on("response", on_response)

    # Trigger refresh for new items
    tried_refresh = False
    # Helper JS to force reload audio elements with cache-busting
    js_force_reload = r"""
    () => {
        try {
            const audios = Array.from(document.querySelectorAll('audio'));
            for (const a of audios) {
                const src = a.currentSrc || a.src || '';
                if (!src) continue;
                const bust = src + (src.includes('?') ? '&' : '?') + 'rnd=' + Date.now();
                try { a.pause && a.pause(); } catch {}
                try { a.src = bust; } catch {}
                try { a.load && a.load(); } catch {}
            }
            return audios.length;
        } catch (e) { return -1; }
    }
    """
    # Try page Refresh; if not available, force reload audios; do both if possible
    try:
        tried_refresh = _click_refresh(page)
        if not tried_refresh:
            page.evaluate(js_force_reload)
        else:
            page.wait_for_timeout(400)
            page.evaluate(js_force_reload)
    except Exception:
        try:
            page.evaluate(js_force_reload)
        except Exception:
            pass

    while time.time() < start_deadline:
        if len(results) >= 3:
            break
        try:
            page.wait_for_timeout(200)
        except Exception:
            pass

    # Detach listeners
    try:
        page.remove_listener("request", on_request)
        page.remove_listener("requestfinished", on_finished)
        page.remove_listener("response", on_response)
    except Exception:
        pass

    return results

def _collect_media_via_perf(page) -> list[dict]:
    """Passive fallback: read Performance resource entries and filter media/audio.
    Returns up to the last 3 entries with fields: url, size(bytes), time(ms), start(s).
    """
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
    # Normalize to expected structure
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
    """Capture audio-like network traffic at BrowserContext level (covers iframes).
    Returns list of dicts: {url, start, end, status, mime, bytes}
    """
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

    # Trigger in-page Refresh; if missing, force audio reload
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

def _js_get_audio_srcs_by_label():
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
            // search within same container then ancestors
            let n = el;
            for (let depth=0; depth<4 && n; depth++, n=n.parentElement){
                const a = n.querySelector('audio');
                if (a) return a.currentSrc || a.src || null;
            }
            // fallback: any audio in document
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
        data = page.evaluate(_js_get_audio_srcs_by_label())
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    # Normalize
    A = data.get('A') if isinstance(data, dict) else None
    B = data.get('B') if isinstance(data, dict) else None
    R = data.get('R') if isinstance(data, dict) else None
    all_urls = []
    try:
        all_urls = data.get('all') or []
    except Exception:
        all_urls = []
    # If any missing, try to use first three audios
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
        # Range is not added by default here; we first try HEAD for total size.
        "Referer": page.url,
    }
    if ua:
        headers_base["User-Agent"] = ua
    for key, url in urls.items():
        if not url:
            continue
        try:
            parsed = urlparse(url)
            cookies = _cookies_for_url(page, url)
            s = requests.Session()
            # Build cookie header
            cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()]) if cookies else None
            headers = dict(headers_base)
            if cookie_header:
                headers["Cookie"] = cookie_header
            total = 0
            # 1) Try HEAD first: for S3 this typically returns 200 and full Content-Length
            try:
                head_headers = dict(headers)
                head_headers.pop("Range", None)
                head_resp = s.head(url, headers=head_headers, timeout=8, allow_redirects=True)
                cl = head_resp.headers.get('Content-Length') or head_resp.headers.get('content-length')
                if cl:
                    total = int(str(cl).strip())
            except Exception:
                total = 0

            # 2) If HEAD didn't yield, try Range GET to obtain Content-Range: bytes 0-0/TOTAL (or sometimes 0-end/TOTAL)
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


def _js_fetch_pcm_from_src(url: str):
        safe_url = url.replace("'", "%27")
        return f"""
        async () => {{
            try {{
                const url = '{safe_url}';
                if (!url || url.toLowerCase().endsWith('.m3u8')) return null;
                const Ctor = window.AudioContext || window.webkitAudioContext;
                const ctx = new Ctor();
                const res = await fetch(url, {{ credentials: 'include' }});
                if (!res.ok) {{ try {{ ctx.close(); }} catch (e) {{}} return null; }}
                const arr = await res.arrayBuffer();
                const ab = await ctx.decodeAudioData(arr.slice(0));
                const ch = ab.numberOfChannels > 0 ? 0 : 0;
                const data = ab.getChannelData(ch);
                const step = Math.max(1, Math.floor(ab.sampleRate / 22050));
                const out = [];
                for (let i=0;i<data.length;i+=step) out.push(data[i]);
                const result = {{ sampleRate: ab.sampleRate/step, data: out }};
                try {{ ctx.close(); }} catch (e) {{}}
                return result;
            }} catch (e) {{ return null; }}
        }}
        """


def _js_fetch_byte_length(url: str):
        safe_url = url.replace("'", "%27")
        return f"""
        async () => {{
            try {{
                const res = await fetch('{safe_url}', {{ credentials: 'include' }});
                if (!res.ok) return 0;
                const buf = await res.arrayBuffer();
                return buf.byteLength || 0;
            }} catch (e) {{ return 0; }}
        }}
        """


def _js_head_or_range_size(url: str):
        safe_url = url.replace("'", "%27")
        return f"""
        async () => {{
            const url = '{safe_url}';
            try {{
                // Try HEAD first
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
                // Fallback: Range GET to obtain Content-Range: bytes 0-0/TOTAL
                const res = await fetch(url, {{ method: 'GET', headers: {{ 'Range': 'bytes=0-0' }}, credentials: 'include' }});
                if (res && res.ok) {{
                    const cr = res.headers.get('content-range') || '';
                    const slash = cr.lastIndexOf('/');
                    if (slash > -1) {{
                        const part = cr.substring(slash + 1).trim();
                        const n = parseInt(part, 10);
                        if (!Number.isNaN(n) && n > 0) return n;
                    }}
                    // As a last resort, try content-length
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


def _js_pause_for_label(label_key: str):
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
            const el = container.querySelector('audio') || document.querySelector('audio');
            if (el) { try { el.pause(); } catch (e) {} }
            return true;
        }
        """.replace('__KEY__', safe_key)


def _js_capture_analyser_pcm(label_key: str, duration_ms: int = 1500):
        safe_key = label_key.replace("'", "")
        return r"""
        async () => {
            try {
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
                const audio = container.querySelector('audio') || document.querySelector('audio');
                if (!audio) return null;
                try { audio.crossOrigin = audio.crossOrigin || 'anonymous'; } catch (e) {}
                try { await audio.play(); } catch (e) {}
                const Ctx = window.AudioContext || window.webkitAudioContext;
                const ctx = new Ctx();
                const src = ctx.createMediaElementSource(audio);
                const analyser = ctx.createAnalyser();
                analyser.fftSize = 2048;
                const buf = new Float32Array(analyser.fftSize);
                src.connect(analyser);
                analyser.connect(ctx.destination);
                const stepMs = 40;
                const loops = Math.max(1, Math.floor(__DUR__ / stepMs));
                const out = [];
                for (let i = 0; i < loops; i++) {
                    analyser.getFloatTimeDomainData(buf);
                    for (let j = 0; j < buf.length; j += 4) out.push(buf[j]);
                    await new Promise(r => setTimeout(r, stepMs));
                }
                try { audio.pause(); } catch (e) {}
                const sr = ctx.sampleRate / 4;
                try { src.disconnect(); analyser.disconnect(); ctx.close(); } catch (e) {}
                return { sampleRate: sr, data: out };
            } catch (e) { return null; }
        }
        """.replace('__KEY__', safe_key).replace('__DUR__', str(int(duration_ms)))


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


def _best_lag(ref: np.ndarray, x: np.ndarray, max_lag: int = 2048) -> int:
    """Return lag (ref delayed positive) that maximizes mean product (correlation)."""
    a = _normalize(ref)
    b = _normalize(x)
    n = min(len(a), len(b))
    if n < 64:
        return 0
    a = a[:n]
    b = b[:n]
    L = int(min(max_lag, n - 1))
    best_lag = 0
    best_val = -1e9
    # Evaluate correlations for lags in [-L, L]
    for lag in range(-L, L + 1):
        if lag >= 0:
            aa = a[lag:]
            bb = b[: len(aa)]
        else:
            bb = b[-lag:]
            aa = a[: len(bb)]
        m = len(aa)
        if m < 64:
            continue
        val = float(np.mean(aa * bb))
        if val > best_val:
            best_val = val
            best_lag = lag
    return best_lag


def _align_by_lag(ref: np.ndarray, x: np.ndarray, max_lag: int = 2048) -> tuple[np.ndarray, np.ndarray]:
    """Align x to ref by best lag and return overlapping segments of equal length."""
    if len(ref) == 0 or len(x) == 0:
        return np.asarray([], dtype=np.float32), np.asarray([], dtype=np.float32)
    lag = _best_lag(ref, x, max_lag=max_lag)
    a = ref
    b = x
    if lag >= 0:
        a2 = a[lag:]
        n = min(len(a2), len(b))
        a2 = a2[:n]
        b2 = b[:n]
    else:
        b2 = b[-lag:]
        n = min(len(a), len(b2))
        a2 = a[:n]
        b2 = b2[:n]
    return a2.astype(np.float32, copy=False), b2.astype(np.float32, copy=False)


def _peak_normalize(sig: np.ndarray) -> np.ndarray:
    """Scale by peak absolute value to fit within [-1, 1]."""
    if sig.size == 0:
        return sig.astype(np.float32)
    s = sig.astype(np.float32)
    peak = float(np.max(np.abs(s)))
    if peak > 1e-9:
        s = s / peak
    return s


def _rmse(ref: np.ndarray, x: np.ndarray) -> float:
    """Root-mean-square error after alignment and peak normalization."""
    a, b = _align_by_lag(ref, x, max_lag=2048)
    if a.size == 0 or b.size == 0:
        return 1.0
    a = _peak_normalize(a)
    b = _peak_normalize(b)
    m = min(a.size, b.size)
    if m < 64:
        return 1.0
    a = a[:m]
    b = b[:m]
    return float(np.sqrt(np.mean((a - b) ** 2)))


def _psnr_from_rmse(rmse: float, peak: float = 1.0) -> float:
    """PSNR in dB given RMSE and peak amplitude (default 1.0)."""
    if rmse <= 1e-12:
        return 100.0
    return float(20.0 * np.log10(peak / rmse))


def _symmetric_kl_spectrum(ref: np.ndarray, x: np.ndarray) -> float:
    """Compute a bounded symmetric KL divergence between power spectra (0..1)."""
    n = min(len(ref), len(x))
    if n < 256:
        return 0.0
    n = int(2 ** np.floor(np.log2(n)))
    a = _normalize(ref[:n])
    b = _normalize(x[:n])
    A = np.fft.rfft(a)
    B = np.fft.rfft(b)
    p = np.abs(A) ** 2
    q = np.abs(B) ** 2
    eps = 1e-12
    p = p + eps
    q = q + eps
    p = p / float(np.sum(p))
    q = q / float(np.sum(q))
    kl_pq = float(np.sum(p * np.log(p / q)))
    kl_qp = float(np.sum(q * np.log(q / p)))
    sym = max(0.0, 0.5 * (kl_pq + kl_qp))
    # Map to 0..1 for stability
    return float(sym / (1.0 + sym))


def _snr(ref: np.ndarray, x: np.ndarray) -> float:
    """Compute SNR in dB treating difference as noise after time alignment."""
    a, b = _align_by_lag(ref, x, max_lag=2048)
    if len(a) == 0 or len(b) == 0:
        return 0.0
    sig = _normalize(a)
    rec = _normalize(b)
    noise = sig - rec
    sp = float(np.mean(sig * sig))
    npow = float(np.mean(noise * noise))
    if npow <= 1e-12:
        return 100.0
    return float(10.0 * np.log10(sp / npow))


def compute_audio_quality(ref: np.ndarray, cand: np.ndarray) -> float:
    """Evalúa la calidad del audio candidato en comparación con el de referencia."""
    # Calcular métricas existentes
    rmse_score = _rmse(ref, cand)
    psnr_score = _psnr_from_rmse(rmse_score)
    kl_divergence = _symmetric_kl_spectrum(ref, cand)

    # Calcular nuevas métricas
    snr_score = _snr(ref, cand)
    clarity_score = _sim_freq_cos(ref, cand)  # Usar correlación espectral como claridad

    # Normalizar y ponderar las métricas
    psnr_n = min(psnr_score / 60.0, 1.0)  # Cap suave en 60 dB
    kl_n = 1.0 - min(kl_divergence, 1.0)  # Invertir para que 1 sea mejor
    snr_n = min(snr_score / 60.0, 1.0)
    clarity_n = (clarity_score + 1) / 2  # Normalizar a [0, 1]

    # Ponderación de las métricas
    score = 0.4 * psnr_n + 0.3 * snr_n + 0.2 * clarity_n + 0.1 * kl_n
    return score

def compute_audio_metrics(ref: np.ndarray, cand: np.ndarray) -> dict:
    """Devuelve un diccionario con métricas detalladas de calidad de audio."""
    rmse_score = _rmse(ref, cand)
    psnr_score = _psnr_from_rmse(rmse_score)
    kl_divergence = _symmetric_kl_spectrum(ref, cand)
    snr_score = _snr(ref, cand)
    clarity_score = _sim_freq_cos(ref, cand)

    return {
        "RMSE": rmse_score,
        "PSNR": psnr_score,
        "KL-Divergence": kl_divergence,
        "SNR": snr_score,
        "Clarity": clarity_score,
    }


def _capture_pcm(page, label: str, capture_ms: int = 1800, timeout_ms: int = 1800) -> Optional[dict]:
    """Try to capture downsampled PCM for a label ('R','A','B'), selecting it first, then fetching src, then hooks, then analyser."""
    try:
        frames = page.frames
    except Exception:
        frames = [page]
    # Install hooks
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
    # Select label and start playback first
    for fr in frames:
        try:
            fr.evaluate(_js_set_current_label(label))
            fr.evaluate(_js_click_play_for_label(label))
        except Exception:
            pass
    try:
        page.wait_for_timeout(250)
    except Exception:
        pass
    # Try to fetch/decode via detected media src near the label (after selection)
    try:
        for fr in frames:
            try:
                url = fr.evaluate(_js_get_audio_src_for_label(label))
                if url and isinstance(url, str) and not url.lower().endswith('.m3u8'):
                    got = fr.evaluate(_js_fetch_pcm_from_src(url))
                    if got and isinstance(got, dict) and got.get("data"):
                        try:
                            fr.evaluate(_js_pause_for_label(label))
                        except Exception:
                            pass
                        got["method"] = "fetch"
                        return got
            except Exception:
                continue
    except Exception:
        pass
    # Attempt via hooks
    for fr in frames:
        try:
            res = fr.evaluate(_js_grab_pcm_via_hooks(label, capture_ms, timeout_ms))
            if res and isinstance(res, dict) and res.get("data"):
                try:
                    fr.evaluate(_js_pause_for_label(label))
                except Exception:
                    pass
                res["method"] = "hooks"
                return res
        except Exception:
            continue
    # Finally, try analyser-based capture on the element directly
    for fr in frames:
        try:
            res2 = fr.evaluate(_js_capture_analyser_pcm(label, duration_ms=capture_ms))
            if res2 and isinstance(res2, dict) and res2.get("data"):
                res2["method"] = "analyser"
                return res2
        except Exception:
            continue
    return None


def _measure_media_sizes(page) -> Optional[dict]:
    """Return dict with urls and byte sizes for labels R/A/B if detectable."""
    try:
        frames = page.frames
    except Exception:
        frames = [page]
    result = {"R": None, "A": None, "B": None}
    # First, collect URLs
    for lab in ("R","A","B"):
        for fr in frames:
            try:
                url = fr.evaluate(_js_get_audio_src_for_label(lab))
                if url and isinstance(url, str):
                    result[lab] = {"url": url, "bytes": None}
                    break
            except Exception:
                continue
    # Then, fetch byte lengths
    for lab in ("R","A","B"):
        rec = result.get(lab)
        if rec and rec.get("url") and rec.get("bytes") is None:
            for fr in frames:
                try:
                    bl = fr.evaluate(_js_head_or_range_size(rec["url"]))
                    if isinstance(bl, (int, float)) and bl > 0:
                        rec["bytes"] = int(bl)
                        break
                except Exception:
                    continue
    return result


def _js_click_save_for_label(label_key: str):
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
            const sels = [
                'button:has-text("Save")','[role=button]:has-text("Save")','text=Save',
                'button:has-text("Guardar")','[role=button]:has-text("Guardar")','text=Guardar',
                'button:has-text("Save clip")','button:has-text("Save sample")','button:has-text("Set")'
            ];
            for (const s of sels) {
                const btn = container.querySelector(s) || document.querySelector(s);
                if (btn) { try { btn.click(); return true; } catch (e) { /*noop*/ } }
            }
            return false;
        }
        """.replace('__KEY__', safe_key)


def _js_collect_media_stats_for_label(label_key: str, wait_ms: int = 700):
        safe_key = label_key.replace("'", "")
        return r"""
        async () => {
            try {
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
                const audio = container.querySelector('audio') || document.querySelector('audio');
                if (!audio) return null;
                try { labelEl && labelEl.click && labelEl.click(); } catch (e) {}
                try { audio.preload = 'auto'; } catch (e) {}
                try { performance.clearResourceTimings(); } catch (e) {}
                try { audio.load(); } catch (e) {}
                try { await audio.play(); } catch (e) {}
                await new Promise(r => setTimeout(r, __WAIT__));
                try { audio.pause(); } catch (e) {}
                const src = audio.currentSrc || audio.src || '';
                const entriesByName = src ? performance.getEntriesByName(src) : [];
                let cand = entriesByName && entriesByName.length ? entriesByName[entriesByName.length-1] : null;
                if (!cand) {
                    const allRes = performance.getEntriesByType('resource');
                    const wavs = allRes.filter(e => (e.name||'').toLowerCase().includes('.wav') || (e.initiatorType||'')==='media');
                    cand = wavs.length ? wavs[wavs.length-1] : null;
                }
                const size = cand ? (cand.transferSize || cand.decodedBodySize || cand.encodedBodySize || 0) : 0;
                const duration = cand ? (cand.duration || 0) : 0;
                return { url: src||null, size, duration };
            } catch (e) { return null; }
        }
        """.replace('__KEY__', safe_key).replace('__WAIT__', str(int(wait_ms)))


def _measure_media_stats_via_perf(page) -> Optional[dict]:
    """Click each label and collect {size (bytes), duration (ms)} via Performance API."""
    labels = ['R','A','B']
    out = {}
    try:
        frames = page.frames
    except Exception:
        frames = [page]
    for lab in labels:
        stat = None
        for fr in frames:
            try:
                stat = fr.evaluate(_js_collect_media_stats_for_label(lab, wait_ms=800))
                if stat and isinstance(stat, dict):
                    out[lab] = stat
                    break
            except Exception:
                continue
        if lab not in out:
            out[lab] = None
    return out


def _decide_by_cdp_media(page, logger, timeout_s: int = 15) -> Optional[str]:
    """Usa CDP (Network.*) para capturar 3 WAV (A,B,Referencia) tras el refresh.
    Decide por cercanía a la referencia usando size (bytes) y time (ms).
    Mapea por orden de inicio: A, luego B, y al final Reference.
    """
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
        # Auto-attach to all sub-targets (iframes/service workers) and enable Network there too
        session.send("Target.setAutoAttach", {
            "autoAttach": True,
            "waitForDebuggerOnStart": False,
            "flatten": True
        })
    except Exception:
        pass

    entries = {}  # requestId -> dict
    counters = {"req": 0, "resp": 0, "finish": 0}

    def on_request(e):
        try:
            counters["req"] += 1
            req_id = e.get("requestId")
            req = e.get("request", {})
            url = (req.get("url") or "")
            lower = url.lower()
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
            counters["resp"] += 1
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
            counters["finish"] += 1
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
        # Normalize keys to case-insensitive lookup
        h = {str(k).lower(): v for k, v in headers.items()}
        # Content-Length
        cl = h.get("content-length")
        if cl is not None:
            try:
                d["bytes_header"] = int(str(cl).strip())
            except Exception:
                pass
        # Content-Range: bytes start-end/total
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

    # When attached to a sub-target, enable Network there as well
    session.on("Target.attachedToTarget", lambda e: _send_to_target(e.get("sessionId"), "Network.enable", {}))

    # Parse Network events from child sessions
    def _on_msg_from_target(e):
        try:
            sid = e.get("sessionId")
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

    # Prefer clicking the in-page Refresh button to load new audio items
    tried_refresh = False
    try:
        tried_refresh = _click_refresh(page)
    except Exception:
        tried_refresh = False
    if not tried_refresh:
        # Fallback to a hard reload ignoring cache
        try:
            session.send("Page.reload", {"ignoreCache": True})
        except Exception:
            try:
                page.reload(wait_until="domcontentloaded")
            except Exception:
                pass

    # Try BrowserContext-level capture first
    try:
        ctx_records = _collect_media_via_context(page.context, page, logger, timeout_s=min(6, timeout_s//2 or 5))
        if len(ctx_records) >= 3:
            ctx_records.sort(key=lambda x: x.get('start', 0.0))
            A,B,R = ctx_records[-3:]
            def size_kb_c(d): return float(int(d.get('bytes') or 0))/1024.0
            def time_ms_c(d): return max(0.0, (float(d.get('end') or 0.0)-float(d.get('start') or 0.0))*1000.0)
            sizes = [size_kb_c(A), size_kb_c(B), size_kb_c(R)]
            times = [time_ms_c(A), time_ms_c(B), time_ms_c(R)]
            r_idx = int(max(range(3), key=lambda i: sizes[i]))
            if r_idx != 2:
                order = [0,1,2]
                order.remove(r_idx)
                order.append(r_idx)
                A,B,R = [ [A,B,R][i] for i in order ]
                sizes = [ sizes[i] for i in order ]
                times = [ times[i] for i in order ]
            sa,sb,sr = sizes
            ta,tb,tr = times
            def closeness(sx,tx):
                ns = abs(sx-sr)/max(sr,1e-6)
                nt = abs(tx-tr)/max(tr,1e-6)
                return 0.7*ns + 0.3*nt
            ca,cb = closeness(sa,ta), closeness(sb,tb)
            choice = 'Tie' if abs(ca-cb)<=0.01 else ('Version A' if ca<cb else 'Version B')
            try:
                logger.debug(f"Context media (kB/ms) -> R:({sr:.0f}kB,{tr:.0f}ms) A:({sa:.0f}kB,{ta:.0f}ms) B:({sb:.0f}kB,{tb:.0f}ms) => {choice}")
            except Exception:
                pass
            return choice
    except Exception:
        pass

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(0.1)
        # Gather completed, successful media entries likely to be audio
        fins = []
        for d in entries.values():
            if ("start" in d) and ("end" in d):
                st = int(d.get("status") or 0)
                ok_status = (st == 206 or st == 200)
                # Resolve size: prefer total > header > encoded
                size = int(d.get("bytes_total") or d.get("bytes_header") or d.get("bytes_encoded") or d.get("bytes_data") or 0)
                url = (d.get("url") or "").lower()
                mime = (d.get("mime") or "").lower()
                rtype = (d.get("rtype") or "").lower()
                has_audio_ext = any(ext in url for ext in [
                    ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".webm"
                ])
                looks_audio = has_audio_ext or mime.startswith("audio") or (rtype == "media")
                if ok_status and looks_audio and not mime.startswith("image"):
                    # If no size from headers, try extra headers (responseReceivedExtraInfo)
                    # Size will be recalculated later via helper; keep entry regardless of current size
                    fins.append(d)
        # We need exactly the 3 relevant clips (A,B,Ref). Use last 3 by start time.
        if len(fins) >= 3:
            fins.sort(key=lambda x: x.get("start", 0.0))
            fins = fins[-3:]
            # Assume order A, B, Reference
            A, B, R = fins[0], fins[1], fins[2]

            def size_kb(d):
                sz = int(d.get("bytes_total") or d.get("bytes_header") or d.get("bytes_encoded") or d.get("bytes_data") or 0)
                return sz / 1024.0

            def time_ms(d):
                return max(0.0, (float(d.get("end") or 0.0) - float(d.get("start") or 0.0)) * 1000.0)

            sizes = [size_kb(A), size_kb(B), size_kb(R)]
            times = [time_ms(A), time_ms(B), time_ms(R)]
            # Heurística adicional: Reference suele ser el mayor tamaño
            r_idx = int(max(range(3), key=lambda i: sizes[i]))
            if r_idx != 2:
                # Reordenar para que R sea el último
                order = [0,1,2]
                order.remove(r_idx)
                order.append(r_idx)
                A, B, R = [ [A,B,R][i] for i in order ]
                sizes = [ sizes[i] for i in order ]
                times = [ times[i] for i in order ]
            sa, sb, sr = sizes[0], sizes[1], sizes[2]
            ta, tb, tr = times[0], times[1], times[2]

            # Normalized closeness to Reference (relative to R)
            def closeness(sx, tx):
                ns = abs(sx - sr) / max(sr, 1e-6)
                nt = abs(tx - tr) / max(tr, 1e-6)
                return 0.7 * ns + 0.3 * nt

            ca = closeness(sa, ta)
            cb = closeness(sb, tb)
            if abs(ca - cb) <= 0.01:  # 1% tolerance -> Tie
                choice = "Tie"
            elif ca < cb:
                choice = "Version A"
            else:
                choice = "Version B"
            try:
                logger.debug(
                    f"CDP media (kB/ms, 200/206) -> R:({sr:.0f}kB,{tr:.0f}ms) A:({sa:.0f}kB,{ta:.0f}ms) B:({sb:.0f}kB,{tb:.0f}ms) => {choice}"
                )
            except Exception:
                pass
            return choice
    # Debug: log what we saw if nothing decided
    try:
        dbg = []
        for d in entries.values():
            st = d.get("status")
            size = int(d.get("bytes_total") or d.get("bytes_header") or d.get("bytes_encoded") or d.get("bytes_data") or 0)
            dbg.append({
                "url": (d.get("url") or "")[-80:],
                "rtype": d.get("rtype"),
                "status": st,
                "mime": d.get("mime"),
                "size": size,
                "hasEnd": "end" in d
            })
        logger.debug(f"CDP debug counters: {counters}; entries={len(entries)}; audioLike={len(dbg)}")
        if dbg:
            logger.debug(f"CDP debug entries: {json.dumps(dbg)[:1200]}")
    except Exception:
        pass
    # Last fallback: Performance API passive media
    try:
        perf_items = _collect_media_via_perf(page)
        if len(perf_items) >= 3:
            perf_items.sort(key=lambda x: x.get("start", 0.0))
            perf_items = perf_items[-3:]
            A, B, R = perf_items[0], perf_items[1], perf_items[2]
            # Attempt to replace perf sizes (often 0) with header totals via HTTP
            ua = None
            try:
                ua = page.evaluate("() => navigator.userAgent")
            except Exception:
                ua = None
            urls_hdr = {
                "A": A.get("url"),
                "B": B.get("url"),
                "R": R.get("url"),
            }
            sizes_hdr = {}
            try:
                sizes_hdr = _measure_sizes_via_http(page, urls_hdr, ua=ua)
            except Exception:
                sizes_hdr = {}

            def size_kb_p(d, key=None):
                # Prefer header totals when available; else perf sizes
                if key and sizes_hdr and isinstance(sizes_hdr.get(key), (int, float)) and sizes_hdr.get(key, 0) > 0:
                    return float(int(sizes_hdr.get(key) or 0)) / 1024.0
                return float(int(d.get("bytes") or 0)) / 1024.0
            def time_ms_p(d):
                return float(d.get("time") or 0.0)
            sizes = [size_kb_p(A, "A"), size_kb_p(B, "B"), size_kb_p(R, "R")]
            times = [time_ms_p(A), time_ms_p(B), time_ms_p(R)]
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
                choice = "Tie"
            elif ca < cb:
                choice = "Version A"
            else:
                choice = "Version B"
            try:
                src = "Perf+HTTP" if any((sizes_hdr.get(k, 0) or 0) > 0 for k in ["A","B","R"]) else "Perf"
                logger.debug(
                    f"{src} media (kB/ms) -> R:({sr:.0f}kB,{tr:.0f}ms) A:({sa:.0f}kB,{ta:.0f}ms) B:({sb:.0f}kB,{tb:.0f}ms) => {choice}"
                )
            except Exception:
                pass
            return choice
    except Exception:
        pass
    return None
def main():
    parser = argparse.ArgumentParser(description="Automatiza comparaciones de calidad de audio en Multimango")
    parser.add_argument("--headed", action="store_true", help="Abrir navegador con UI")
    # DevTools no longer required for logging; keep flag but default unused
    parser.add_argument("--devtools", action="store_true", help="(Opcional) Abrir Chrome DevTools (diagnóstico)")
    parser.add_argument("--delay-seconds", type=int, default=1, help="Retardo humano por iteración (s)")
    parser.add_argument("--max-iters", type=int, default=3, help="Máximo de iteraciones (0 = ilimitado)")
    parser.add_argument("--log-file", type=str, default="", help="Ruta del log")
    parser.add_argument("--tie-diff", type=float, default=0.02, help="Umbral |scoreA-scoreB| para declarar Tie")
    parser.add_argument("--capture-ms", type=int, default=1800, help="Milisegundos de audio a capturar por muestra")
    parser.add_argument("--iter-timeout", type=int, default=25, help="Tiempo máximo (s) por iteración antes de abortar")
    parser.add_argument("--url", type=str, default="https://www.multimango.com/tasks/080825-audio-quality-compare", help="URL de la tarea")
    parser.add_argument("--manual-login", action="store_true", help="Permitir login manual si el panel no aparece")
    parser.add_argument("--manual-login-timeout", type=int, default=180, help="Segundos para esperar login manual")
    parser.add_argument("--network-first", action="store_true", help="Usar primero la heurística de red (size/time de WAV)")
    parser.add_argument("--header-first", action="store_true", help="Preferir tamaños totales por headers (Content-Range/Length) usando los src de audio del DOM")
    parser.add_argument("--urls", nargs='*', help="Opcional: pasar 3 URLs WAV (A B R) para calcular tamaños por headers sin navegador")
    # Audit CSV (similar a imágenes)
    parser.add_argument("--audit-csv", type=str, default="", help="Ruta de CSV para auditar decisiones/medidas")
    parser.add_argument("--audit-limit", type=int, default=0, help="Máximo de filas a guardar en CSV (0 = todas)")
    parser.add_argument("--audit-batch", type=int, default=1, help="Escribir el CSV cada N iteraciones (1 = cada iteración)")
    args = parser.parse_args()

    log_path = Path(args.log_file) if args.log_file else None
    logger = setup_logger(log_path)

    start = time.time()
    iterations = 0
    # Config de auditoría CSV
    # Default CSV under the current project folder: telus_compara_audios/audit/decisions.csv
    default_csv = (Path.cwd() / "audit" / "decisions.csv")
    csv_path = Path(args.audit_csv) if args.audit_csv else default_csv
    csv_rows: list[dict] = []

    # If --urls provided, run header-only mode and exit
    if args.urls and len(args.urls) >= 3:
        urls_list = args.urls[:3]
        urls = {"A": urls_list[0], "B": urls_list[1], "R": urls_list[2]}
        # Use requests directly (no browser). HEAD then Range GET logic.
        def size_for(u: str) -> int:
            try:
                s = requests.Session()
                # 1) HEAD
                try:
                    r = s.head(u, timeout=10, allow_redirects=True)
                    cl = r.headers.get('Content-Length') or r.headers.get('content-length')
                    if cl:
                        return int(str(cl).strip())
                except Exception:
                    pass
                # 2) Range GET
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
        # No dependence on DevTools UI anymore

        if not wait_for_audio_panel(page, timeout_s=15):
            if args.headed and args.manual_login:
                logger.info("Panel no visible. Esperando login manual…")
                try:
                    page.evaluate(_js_overlay_show("Inicia sesión y navega a la tarea. Se reanudará automáticamente…"))
                except Exception:
                    pass
                end = time.time() + float(max(30, args.manual_login_timeout))
                while time.time() < end:
                    if wait_for_audio_panel(page, timeout_s=2):
                        break
                try:
                    page.evaluate(_js_overlay_hide())
                except Exception:
                    pass
            if not wait_for_audio_panel(page, timeout_s=5):
                logger.error("No se encontró el panel de audio. Verifica login o URL.")
                return

        while args.max_iters == 0 or iterations < args.max_iters:
            iter_start = time.time()
            logger.debug(f"Iteración {iterations + 1}…")

            decision = None
            iter_sizes_kb = None  # tuple (R,A,B) in kB for the concise summary
            iter_source = None    # fuente usada para decidir (header-first/cdp/perf-http/dom-http)

            # If requested, try header-based sizes from DOM audio srcs first
            if args.header_first and not decision:
                try:
                    srcs = _get_audio_srcs(page)  # {A,B,R,all}
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
                        # Maintain mapping by remapping R as largest
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

            # Capturar 3 WAV por CDP (Network) y decidir por Size y Time
            try:
                dec_net = _decide_by_cdp_media(page, logger, timeout_s=10)
            except Exception:
                dec_net = None
            if dec_net:
                decision = dec_net
                iter_source = iter_source or 'cdp'

            # Sin fallback PCM: decisión 100% por Network (Media)
            ref_rec = a_rec = b_rec = None

            if not decision:
                # Try Perf last3 media URLs + HTTP sizes first
                try:
                    last3 = _perf_get_last3_media_urls(page)
                    if len(last3) == 3:
                        # Assume order A,B,R then remap by largest size
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
                # Final fallback: DOM srcs + HTTP HEAD/RANGE sizes + Performance durations
                try:
                    srcs = _get_audio_srcs(page)  # {A,B,R,all}
                    urls = {"A": srcs.get("A"), "B": srcs.get("B"), "R": srcs.get("R")}
                    # User-Agent from browser context if possible
                    ua = None
                    try:
                        ua = page.evaluate("() => navigator.userAgent")
                    except Exception:
                        ua = None
                    sizes = _measure_sizes_via_http(page, urls, ua=ua)
                    times = _perf_times_for_urls(page, urls)
                    # Require at least two non-zero sizes and three non-zero times
                    vals = [sizes.get("A",0), sizes.get("B",0), sizes.get("R",0)]
                    tvals = [times.get("A",0.0), times.get("B",0.0), times.get("R",0.0)]
                    if sum(1 for v in vals if v>0) >= 2 and all(t>=0 for t in tvals):
                        # remap reference as largest size
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

            # If we haven't captured sizes yet for summary, try now BEFORE submitting (DOM still on current item)
            if not iter_sizes_kb:
                try:
                    hdr = _header_sizes_kb_for_current(page)
                    # Use sizes as-is mapped by labels (R,A,B)
                    iter_sizes_kb = (hdr.get('R', 0.0), hdr.get('A', 0.0), hdr.get('B', 0.0))
                    # If still zeros, try perf last3 + HTTP as a secondary attempt
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

            # Ensure panel still visible before clicking
            wait_for_audio_panel(page, timeout_s=3)
            # Click decisión
            if not click_decision(page, decision):
                logger.warning("No se pudo hacer clic en la decisión. Abortando.")
                break

            # Enviar
            submit_btn = _get_submit_button(page)
            if not _wait_submit_enabled(submit_btn, timeout_ms=8000):
                logger.warning("Botón Submit no habilitado a tiempo.")
                break
            time.sleep(0.3)
            if not submit_and_next(page):
                logger.warning("No se pudo enviar/avanzar.")
                break

            # Per-iteration concise summary. Prefer sizes computed above; as fallback use header totals now.
            try:
                if not iter_sizes_kb:
                    hdr = _header_sizes_kb_for_current(page)
                    iter_sizes_kb = (hdr.get('R', 0.0), hdr.get('A', 0.0), hdr.get('B', 0.0))
            except Exception:
                iter_sizes_kb = iter_sizes_kb or (0.0, 0.0, 0.0)
            try:
                sr_kb, sa_kb, sb_kb = iter_sizes_kb or (0.0, 0.0, 0.0)
                logger.info(f"Iter {iterations + 1} -> Sizes kB R:{sr_kb:.0f} A:{sa_kb:.0f} B:{sb_kb:.0f} | Decision: {decision}")
                # Audit CSV row
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
                    # enforce tail limit
                    if args.audit_limit and len(csv_rows) > args.audit_limit:
                        csv_rows = csv_rows[-args.audit_limit:]
                    # write file every N iterations
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
            logger.debug(f"Iteración {iterations} OK en {time.time() - iter_start:.1f}s")
            time.sleep(max(0, args.delay_seconds))

        try:
            context.close()
            browser.close()
        except Exception:
            pass

    logger.info("Proceso completado.")

if __name__ == "__main__":
    main()
