# Deployment Rules

## Build Process
```bash
cd projects/dataqbs_site
npm run build            # or: npx astro build
```

## Pre-Deploy Checklist
- [ ] `npm run build` completes without errors
- [ ] Check `dist/` folder exists with `index.html`
- [ ] No secrets in code (gitleaks pre-commit should catch)
- [ ] TypeScript errors resolved

## Deploy Command
```bash
npx wrangler pages deploy dist --project-name dataqbs-site
```

## Environment Variables
Set in Cloudflare Pages dashboard (Settings → Environment variables):
- `GROQ_API_KEY` — LLM API key
- `TURNSTILE_SECRET_KEY` — Captcha validation
- `RESEND_API_KEY` — Email sending
- `FROM_EMAIL` — Sender address
- `TO_EMAIL` — Recipient address

Never commit these to `.env` or `.dev.vars`.

## After Deploy
1. Verify preview URL (format: `https://<hash>.dataqbs-site.pages.dev`)
2. Test contact form submission
3. Test chatbot response
4. Check CV renders correctly
5. Verify PDF download links work

## Production URL
https://www.dataqbs.com

## Rollback
Previous deployments available in Cloudflare Pages dashboard.
Click any deployment → "Make active" to rollback.

## Rate Limiting
WAF rule in Cloudflare dashboard: 15 req/10s on `/api/*`
