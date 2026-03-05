---
paths:
  - "src/pages/api/**/*.ts"
  - "src/components/**/*.svelte"
  - "src/middleware.ts"
---

# Security Rules for dataqbs_site

## Five-Layer Defense (Contact Form)
Every public endpoint must implement these layers in order:

1. **Turnstile** — Server-side validation via `TURNSTILE_SECRET_KEY`
2. **Honeypot** — Hidden `website` field; reject if filled
3. **Speed check** — `_loadedAt` timestamp; reject if < 3 seconds
4. **Origin header** — Must match `https://www.dataqbs.com` (or `http://localhost` in dev)
5. **Rate limiting** — 3 requests/minute per IP (in-memory + WAF rule in CF dashboard)

## Silent Rejection Pattern
When rejecting bots (honeypot/speed check), return fake success:
```typescript
return new Response(JSON.stringify({ success: true }), {
  status: 200,
  headers: { 'Content-Type': 'application/json' }
});
```

## CSP Nonce
`src/middleware.ts` generates per-request nonce for `script-src`. Never use `unsafe-inline`.

## DOMPurify
`src/lib/markdown.ts` sanitizes all `{@html}` output. Never bypass the allowlist.

## System Prompt Safety
`chat.ts` system prompt must never contain:
- Phone numbers
- Exact pricing/rates
- Formulas for calculating costs
- PII of any kind

## Knowledge Store
`knowledge.json` is in KV (`KNOWLEDGE_STORE` binding), NOT in `public/`.
Route `src/pages/knowledge.json.ts` blocks public access.

## CORS
Always locked to `https://www.dataqbs.com`. Never set to `*`.

## Headers (`public/_headers`)
Required headers for all routes:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Adding New API Endpoints Checklist
- [ ] Add Turnstile validation
- [ ] Set CORS to production domain only
- [ ] Add rate limiting
- [ ] Sanitize all user inputs
- [ ] Never log or expose API keys in responses
