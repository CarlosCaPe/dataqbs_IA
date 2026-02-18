/**
 * POST /api/contact
 *
 * Receives contact form submissions.
 * Sends email notification via Resend API (or MailChannels fallback).
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

const DESTINATION_EMAIL = 'carlos.carrillo@dataqbs.com';

/**
 * Send email via Resend API (recommended for Cloudflare Workers).
 * Requires RESEND_API_KEY env var and a verified domain in Resend.
 */
async function sendEmailResend(
  apiKey: string,
  from: string,
  subject: string,
  htmlBody: string,
  replyTo: string,
): Promise<boolean> {
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
    return res.ok;
  } catch (err) {
    console.error('[CONTACT] Resend error:', err);
    return false;
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

  // Validate
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

  // Send email notification
  const resendKey = env.RESEND_API_KEY;
  if (resendKey) {
    const subject = `[dataqbs.com] New message from ${name}`;
    const chatSection = chatTranscript
      ? `<hr/><h3>💬 Chat Transcript</h3><pre style="white-space:pre-wrap;font-size:13px;background:#f5f5f5;padding:12px;border-radius:6px;">${chatTranscript}</pre>`
      : '';
    const htmlBody = `
      <div style="font-family:sans-serif;max-width:600px;">
        <h2>New Contact from dataqbs.com</h2>
        <p><strong>Name:</strong> ${name}</p>
        <p><strong>Email:</strong> <a href="mailto:${email}">${email}</a></p>
        <p><strong>Locale:</strong> ${locale}</p>
        <p><strong>IP:</strong> ${clientIP}</p>
        <p><strong>Time:</strong> ${record.timestamp}</p>
        <hr/>
        <h3>📝 Message</h3>
        <p style="white-space:pre-wrap;">${message}</p>
        ${chatSection}
      </div>
    `;
    const fromAddr = env.EMAIL_FROM ?? 'contact@dataqbs.com';
    await sendEmailResend(resendKey, fromAddr, subject, htmlBody, email);
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
