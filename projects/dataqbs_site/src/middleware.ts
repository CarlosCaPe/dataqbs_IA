/**
 * Astro middleware — injects CSP nonce into every HTML response.
 *
 * How it works:
 *   1. Generates a random nonce per request via crypto.randomUUID()
 *   2. Stores nonce in Astro.locals so Layout.astro can use it
 *   3. After response is generated, replaces <script with <script nonce="..."
 *   4. Overwrites the Content-Security-Policy header with the nonce
 *
 * This eliminates the need for 'unsafe-inline' in script-src.
 */
import { defineMiddleware } from 'astro:middleware';

export const onRequest = defineMiddleware(async (context, next) => {
  // Skip nonce injection for prerendered/static pages (served by CF Pages
  // without the worker — nonces baked at build time are useless).
  const path = context.url.pathname;
  const isStaticRoute = path.startsWith('/realestate');
  if (isStaticRoute) {
    return next();
  }

  // Generate a unique nonce for this request
  const nonce = crypto.randomUUID().replace(/-/g, '');

  // Make nonce available to Astro pages/layouts
  (context.locals as any).nonce = nonce;

  const response = await next();

  // Only process HTML responses
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('text/html')) {
    return response;
  }

  // Read the HTML body
  const html = await response.text();

  // Inject nonce into all <script> tags (inline and src)
  const nonceHtml = html
    .replace(/<script(?=[\s>])/gi, `<script nonce="${nonce}"`);

  // Build CSP with nonce instead of 'unsafe-inline'
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' https://challenges.cloudflare.com https://static.cloudflareinsights.com`,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: https:",
    "connect-src 'self' https://api.resend.com https://challenges.cloudflare.com",
    "frame-src https://challenges.cloudflare.com https://www.openstreetmap.org",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ');

  // Create new response with nonce-injected HTML and updated CSP + security headers
  const newHeaders = new Headers(response.headers);
  newHeaders.set('Content-Security-Policy', csp);
  newHeaders.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
  newHeaders.set('X-Frame-Options', 'DENY');
  newHeaders.set('X-Content-Type-Options', 'nosniff');
  newHeaders.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  newHeaders.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  newHeaders.set('X-XSS-Protection', '1; mode=block');
  // Remove permissive CORS on HTML pages (CF Pages default)
  newHeaders.delete('Access-Control-Allow-Origin');

  return new Response(nonceHtml, {
    status: response.status,
    statusText: response.statusText,
    headers: newHeaders,
  });
});
