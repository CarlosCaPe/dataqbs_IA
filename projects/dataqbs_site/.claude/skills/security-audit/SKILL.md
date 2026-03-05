---
name: security-audit
description: Audit contact form and API endpoints for security vulnerabilities
disable-model-invocation: true
allowed-tools: Read, Grep, Glob
---

# Security Audit for dataqbs_site

Perform security audit on public-facing endpoints.

## Six-Layer Defense Check

### 1. Turnstile Validation
- [ ] `contact.ts` validates `cf-turnstile-response` server-side
- [ ] Uses `TURNSTILE_SECRET_KEY` from environment
- [ ] Returns error if validation fails

### 2. Honeypot Field
- [ ] `ContactPayload` interface has `website?: string` field
- [ ] Form includes hidden honeypot input
- [ ] Server rejects silently if honeypot is filled

### 3. Speed Check
- [ ] `ContactPayload` interface has `_loadedAt?: number` field
- [ ] Form sends `Date.now()` timestamp
- [ ] Server rejects if submission < 3 seconds after load

### 4. Origin Header
- [ ] Server checks `request.headers.get('origin')`
- [ ] Rejects if not `https://www.dataqbs.com` (or localhost in dev)

### 5. Rate Limiting
- [ ] In-memory rate limiter (3 req/min per IP)
- [ ] WAF rule in CF dashboard (15 req/10s on `/api/*`)

### 6. Spam Detection
- [ ] `isSpamMessage()` checks entropy, repetition, special chars, word ratio
- [ ] `isBlockedEmailDomain()` blocks disposable email domains
- [ ] `BLOCKED_EMAIL_DOMAINS` array includes mailinator, tempmail, etc.
- [ ] Silent reject returns fake success to not tip off spammers

## Attack Testing Script
```bash
API="https://www.dataqbs.com/api/contact"
# No Turnstile → fail | Wrong origin → fail | Spam content → silent reject
```

## Files to Audit
```
src/pages/api/contact.ts
src/pages/api/chat.ts
src/components/ContactSection.svelte
src/middleware.ts
public/_headers
```

## CSP & Headers Check
- [ ] Middleware generates CSP nonce (no unsafe-inline)
- [ ] `_headers` has HSTS, X-Frame-Options DENY, nosniff
- [ ] CORS not set to wildcard

## Sensitive Data Check
- [ ] System prompt in chat.ts has no PII
- [ ] knowledge.json not in public/
- [ ] No API keys in client-side code
- [ ] .env and .dev.vars in .gitignore

## Anti-Bot Silent Rejection
Verify honeypot/speed check returns fake success:
```typescript
return new Response(JSON.stringify({ success: true }), {
  status: 200,
  headers: { 'Content-Type': 'application/json' }
});
```

## Report Format
After audit, report:
1. ✅ Passing checks
2. ⚠️ Warnings (non-critical improvements)
3. ❌ Failures (security issues to fix immediately)
