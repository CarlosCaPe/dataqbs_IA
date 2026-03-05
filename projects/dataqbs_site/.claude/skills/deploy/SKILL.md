---
name: deploy
description: Build and deploy dataqbs_site to Cloudflare Pages
disable-model-invocation: true
allowed-tools: Bash(npm *), Bash(npx *)
---

# Deploy dataqbs_site

Deploy the portfolio website to Cloudflare Pages.

## Steps

1. **Verify working directory**
   ```bash
   cd projects/dataqbs_site
   ```

2. **Build**
   ```bash
   npm run build
   ```

3. **Check for errors**
   - If build fails, fix TypeScript/Astro errors first
   - Verify `dist/` folder contains `index.html`

4. **Deploy**
   ```bash
   npx wrangler pages deploy dist --project-name dataqbs-site
   ```

5. **Report** the preview URL from wrangler output

## Post-Deploy Verification
After deployment, remind user to test:
- Contact form submission
- Chatbot response
- CV rendering
- PDF download links

## Notes
- Preview URL format: `https://<hash>.dataqbs-site.pages.dev`
- Production URL: `https://www.dataqbs.com`
- Environment variables are set in Cloudflare Pages dashboard
