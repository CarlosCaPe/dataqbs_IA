// ==UserScript==
// @name         DevTools Network Media Extractor
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Extract audio file sizes and durations from Chrome DevTools Network > Media panel
// @author       GitHub Copilot
// @match        *://*/*
// @grant        GM_setClipboard
// ==/UserScript==

(function () {
    'use strict';

    // Wait for DevTools to load
    function waitForDevToolsPanel() {
        const panel = document.querySelector('.network-log-grid');
        if (!panel) {
            setTimeout(waitForDevToolsPanel, 1000);
            return;
        }
        injectButton(panel);
    }

    // Inject export button
    function injectButton(panel) {
        if (document.getElementById('media-extract-btn')) return;
        const btn = document.createElement('button');
        btn.id = 'media-extract-btn';
        btn.textContent = 'Extract Media Data';
        btn.style.position = 'absolute';
        btn.style.top = '10px';
        btn.style.right = '10px';
        btn.style.zIndex = 9999;
        btn.onclick = extractMediaData;
        panel.appendChild(btn);
    }

    // Extract media data from the table
    function extractMediaData() {
        const rows = document.querySelectorAll('.network-log-grid .data-grid-data-row');
        const results = [];
        rows.forEach(row => {
            const cells = row.querySelectorAll('.data-grid-cell');
            let url = '', size = '', duration = '';
            cells.forEach(cell => {
                if (cell.textContent.match(/\.wav|\.mp3|\.aac|\.ogg|\.m4a/i)) {
                    url = cell.textContent.trim();
                }
                if (cell.textContent.match(/kB|KB/)) {
                    size = cell.textContent.trim();
                }
                if (cell.textContent.match(/ms|s/)) {
                    duration = cell.textContent.trim();
                }
            });
            if (url && size) {
                results.push({ url, size, duration });
            }
        });
        if (results.length === 0) {
            alert('No media entries found. Make sure you are in the Network > Media panel.');
            return;
        }
        const output = results.map(r => `${r.url},${r.size},${r.duration}`).join('\n');
        if (typeof GM_setClipboard !== 'undefined') {
            GM_setClipboard(output);
            alert('Media data copied to clipboard!');
        } else {
            prompt('Copy media data:', output);
        }
    }

    waitForDevToolsPanel();
})();
