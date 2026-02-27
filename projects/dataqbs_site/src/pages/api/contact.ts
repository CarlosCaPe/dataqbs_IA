/**
 * POST /api/contact
 *
 * Receives contact form submissions.
 * Sends email notification via Resend API.
 * Stores in KV if available.
 * Optionally includes chat transcript as attachment.
 */
import type { APIRoute } from 'astro';

export const prerender = false;

interface ContactPayload {
  name: string;
  email: string;
  message: string;
  locale: string;
  turnstileToken?: string;
  chatTranscript?: string;
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

// HTML-encode for safe interpolation in email body
function htmlEncode(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const DESTINATION_EMAIL = 'carlos.carrillo@dataqbs.com';

// ── Rate limiter (in-memory, per-deployment) ─────────
const rateLimitMap = new Map<string, number[]>();
const CONTACT_MAX_PER_MIN = 3; // 3 submissions per minute per IP

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const timestamps = rateLimitMap.get(ip) ?? [];
  const recent = timestamps.filter((t) => now - t < 60_000);
  rateLimitMap.set(ip, recent);
  if (recent.length >= CONTACT_MAX_PER_MIN) return true;
  recent.push(now);
  rateLimitMap.set(ip, recent);
  return false;
}

// ── Turnstile verification ───────────────────────────
async function verifyTurnstile(token: string, secret: string, ip: string): Promise<boolean> {
  try {
    const res = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ secret, response: token, remoteip: ip }),
    });
    const data = await res.json() as { success: boolean };
    return data.success;
  } catch (err) {
    console.error('[CONTACT] Turnstile verification error:', err);
    return false;
  }
}


/**
 * Send email via Resend API.
 * Requires RESEND_API_KEY env var and a verified domain in Resend.
 */
async function sendEmailResend(
  apiKey: string,
  from: string,
  subject: string,
  htmlBody: string,
  replyTo: string,
): Promise<{ ok: boolean; error?: string }> {
  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from,
        to: [DESTINATION_EMAIL],
        reply_to: replyTo,
        subject,
        html: htmlBody,
      }),
    });
    if (!res.ok) {
      const errBody = await res.text();
      console.error('[CONTACT] Resend API error:', res.status, errBody);
      return { ok: false, error: errBody };
    }
    return { ok: true };
  } catch (err) {
    console.error('[CONTACT] Resend fetch error:', err);
    return { ok: false, error: String(err) };
  }
}

export const POST: APIRoute = async ({ request, locals }) => {
  const env = (locals as any).runtime?.env ?? {};

  let body: ContactPayload;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'Invalid JSON' }, 400);
  }

  // Validate raw length before sanitization
  if ((body.message ?? '').length > 5000) {
    return json({ error: 'Message too long (max 5000 chars)' }, 400);
  }

  const name = sanitize(body.name ?? '', 100);
  const email = sanitize(body.email ?? '', 200);
  const message = sanitize(body.message ?? '', 5000);
  const chatTranscript = sanitize(body.chatTranscript ?? '', 20000);
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

  if (isRateLimited(clientIP)) {
    return json({ error: 'Too many submissions. Please wait a minute.' }, 429);
  }

  // Verify Turnstile token (if secret is configured)
  const turnstileSecret = env.TURNSTILE_SECRET_KEY;
  if (turnstileSecret) {
    const token = body.turnstileToken;
    if (!token) {
      return json({ error: 'Security verification required.' }, 400);
    }
    const valid = await verifyTurnstile(token, turnstileSecret, clientIP);
    if (!valid) {
      return json({ error: 'Security verification failed.' }, 403);
    }
  }

  // Build record
  const record = {
    name,
    email,
    message,
    chatTranscript: chatTranscript || undefined,
    locale,
    ip: clientIP,
    timestamp: new Date().toISOString(),
    userAgent: request.headers.get('user-agent') ?? '',
  };

  // Store in KV if available
  const kv = env.CONTACT_STORE as any;
  if (kv) {
    const key = `contact:${Date.now()}:${crypto.randomUUID().slice(0, 8)}`;
    await kv.put(key, JSON.stringify(record), {
      expirationTtl: 60 * 60 * 24 * 90, // 90 days
    });
  }

  // Always log (visible in CF Workers logs)
  console.log('[CONTACT FORM]', JSON.stringify(record));

  // Send email notification via Resend
  const subject = `[dataqbs.com] New message from ${name}`;
  const hasChatTranscript = !!chatTranscript;
  const htmlBody = `
    <div style="font-family:sans-serif;max-width:600px;">
      <h2>New Contact from dataqbs.com</h2>
      <p><strong>Name:</strong> ${htmlEncode(name)}</p>
      <p><strong>Email:</strong> <a href="mailto:${htmlEncode(email)}">${htmlEncode(email)}</a></p>
      <p><strong>Locale:</strong> ${htmlEncode(locale)}</p>
      <p><strong>IP:</strong> ${htmlEncode(clientIP)}</p>
      <p><strong>Time:</strong> ${htmlEncode(record.timestamp)}</p>
      <hr/>
      <h3>Message</h3>
      <p style="white-space:pre-wrap;">${htmlEncode(message)}</p>
      ${hasChatTranscript ? `<hr/><h3>Chat Transcript</h3><pre style="white-space:pre-wrap;font-size:13px;background:#f5f5f5;padding:12px;border-radius:6px;">${htmlEncode(chatTranscript)}</pre>` : ''}
    </div>
  `;

  const resendKey = env.RESEND_API_KEY;
  let emailSent = false;

  if (resendKey) {
    // Use verified domain sender, or Resend's onboarding address
    const fromAddr = env.EMAIL_FROM ?? 'dataqbs.com <onboarding@resend.dev>';
    const result = await sendEmailResend(resendKey, fromAddr, subject, htmlBody, email);
    emailSent = result.ok;
    if (!result.ok) {
      console.error('[CONTACT] Email delivery failed:', result.error);
    }
  } else {
    console.warn('[CONTACT] RESEND_API_KEY not configured. Message logged only.');
  }

  return json({
    success: true,
    emailSent,
    message: emailSent ? 'Message sent. Thank you!' : 'Message received (email delivery pending config).',
  });
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
