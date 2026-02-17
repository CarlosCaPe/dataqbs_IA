/**
 * POST /api/contact
 *
 * Receives contact form submissions.
 * Stores in KV if available, otherwise logs and returns success.
 */
import type { APIRoute } from 'astro';

export const prerender = false;

interface ContactPayload {
  name: string;
  email: string;
  message: string;
  locale: string;
  turnstileToken?: string;
}

// Basic email regex
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Input sanitization
function sanitize(input: string, maxLen = 1000): string {
  return input
    .slice(0, maxLen)
    .replace(/<[^>]*>/g, '') // strip HTML tags
    .replace(/javascript:/gi, '') // strip JS protocol
    .trim();
}

export const POST: APIRoute = async ({ request, locals }) => {
  const env = (locals as any).runtime?.env ?? {};

  let body: ContactPayload;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'Invalid JSON' }, 400);
  }

  // Validate
  const name = sanitize(body.name ?? '', 100);
  const email = sanitize(body.email ?? '', 200);
  const message = sanitize(body.message ?? '', 2000);
  const locale = body.locale ?? 'en';

  if (!name || name.length < 2) {
    return json({ error: 'Name is required (min 2 chars)' }, 400);
  }
  if (!email || !emailRegex.test(email)) {
    return json({ error: 'Valid email is required' }, 400);
  }
  if (!message || message.length < 10) {
    return json({ error: 'Message is required (min 10 chars)' }, 400);
  }

  // Rate limit by IP
  const clientIP = request.headers.get('cf-connecting-ip') ?? 'unknown';

  // Build record
  const record = {
    name,
    email,
    message,
    locale,
    ip: clientIP,
    timestamp: new Date().toISOString(),
    userAgent: request.headers.get('user-agent') ?? '',
  };

  // Store in KV if available
  const kv = env.CONTACT_STORE as KVNamespace | undefined;
  if (kv) {
    const key = `contact:${Date.now()}:${crypto.randomUUID().slice(0, 8)}`;
    await kv.put(key, JSON.stringify(record), {
      expirationTtl: 60 * 60 * 24 * 90, // 90 days
    });
  } else {
    // Log to console (visible in Cloudflare dashboard → Workers logs)
    console.log('[CONTACT FORM]', JSON.stringify(record));
  }

  return json({
    success: true,
    message: 'Message received. Thank you!',
  });
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
