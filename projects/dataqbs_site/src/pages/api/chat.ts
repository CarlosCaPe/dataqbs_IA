/**
 * POST /api/chat
 *
 * Flow:
 *   1. Validate Turnstile token (first message)
 *   2. Load knowledge chunks from static JSON
 *   3. Embed user query via Cloudflare Workers AI
 *   4. Cosine similarity search → top-k chunks
 *   5. Build prompt with system instructions + context + history
 *   6. Stream response from Groq API
 */
import type { APIRoute } from 'astro';

export const prerender = false;

// ── Cosine similarity ────────────────────────────────
function cosineSimilarity(a: number[], b: number[]): number {
  let dot = 0, magA = 0, magB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    magA += a[i] * a[i];
    magB += b[i] * b[i];
  }
  return dot / (Math.sqrt(magA) * Math.sqrt(magB) + 1e-10);
}

// ── Semantic model (from knowledge/semantic_model.yaml) ──
const QUERY_EXPANSION: Record<string, string[]> = {
  snowflake:        ['data warehouse', 'cloud analytics', 'SQL optimization', 'Cortex AI', 'vector search', 'RAG'],
  azure:            ['Microsoft cloud', 'Azure SQL', 'Azure Data Factory', 'ADF', 'Azure Functions'],
  python:           ['pandas', 'ccxt', 'Playwright', 'NumPy', 'scripting'],
  arbitrage:        ['crypto', 'Bellman-Ford', 'triangular', 'exchanges', 'ccxt', 'trading'],
  'data engineering': ['ETL', 'pipeline', 'data warehouse', 'Snowflake', 'Azure Data Factory', 'dbt'],
  'machine learning': ['AI', 'LLM', 'embeddings', 'RAG', 'fine-tuning', 'NLP'],
  sql:              ['database', 'query optimization', 'SQL Server', 'Snowflake', 'Azure SQL'],
  certification:    ['certified', 'SnowPro', 'MCSA', 'AZ-900', 'Azure Data Engineer', 'credential'],
  certifications:   ['certified', 'SnowPro', 'MCSA', 'AZ-900', 'Azure Data Engineer', 'credential'],
  database:         ['SQL Server', 'Snowflake', 'CosmosDB', 'PostgreSQL', 'MySQL', 'databases'],
  databases:        ['SQL Server', 'Snowflake', 'CosmosDB', 'PostgreSQL', 'MySQL', 'database'],
  education:        ['university', 'degree', 'bachelor', 'computer science', 'Guadalajara'],
  projects:         ['arbitrage', 'email collector', 'real estate', 'supplier verifier', 'OAI evaluator', 'portfolio'],
};

const SOURCE_PRIORITY: Record<string, number> = {
  cv: 10,
  certification: 8,
  project: 6,
  github: 4,
};

/**
 * Expand the user query with related terms from the semantic model.
 * Returns the original message + appended expansion terms.
 */
function expandQuery(message: string): string {
  const lower = message.toLowerCase();
  const expansions = new Set<string>();
  for (const [trigger, terms] of Object.entries(QUERY_EXPANSION)) {
    if (lower.includes(trigger)) {
      for (const t of terms) expansions.add(t);
    }
  }
  if (expansions.size === 0) return message;
  return `${message} (related: ${[...expansions].join(', ')})`;
}

/**
 * Apply source-priority boost to raw cosine scores.
 * Adds a small bonus (0–0.05) so higher-priority sources
 * float up when similarity scores are close.
 */
function boostScore(rawScore: number, source: string): number {
  const maxPriority = 10;
  const priority = SOURCE_PRIORITY[source] ?? 2;
  const boost = (priority / maxPriority) * 0.05; // max +0.05 for cv
  return rawScore + boost;
}

// ── Rate limiter (in-memory, per-deployment) ─────────
const rateLimitMap = new Map<string, number[]>();

function isRateLimited(ip: string, maxPerMin: number): boolean {
  const now = Date.now();
  const timestamps = rateLimitMap.get(ip) ?? [];
  const recent = timestamps.filter((t) => now - t < 60_000);
  rateLimitMap.set(ip, recent);
  if (recent.length >= maxPerMin) return true;
  recent.push(now);
  rateLimitMap.set(ip, recent);
  return false;
}

// ── System prompt ────────────────────────────────────
function buildSystemPrompt(locale: string): string {
  return `You are Carlos Carrillo's AI portfolio assistant on dataqbs.com.
Answer questions about his professional experience, skills, projects, and certifications.

CARLOS'S PHILOSOPHY:
Carlos's personal vision for dataqbs is: "To live in peace, free from rigid structures — building projects that flow naturally through intelligence and awareness."
He values simplicity, awareness, and letting technology serve life rather than dominate it. His work reflects this: clean architectures, minimal dependencies, purposeful automation. He's not driven by corporate structures but by genuine curiosity and the craft of engineering elegant solutions.

PERSONALITY:
- Calm, reflective, and down-to-earth. Not boastful — let the work speak.
- Warm but concise. Answers with substance, not filler.
- When asked about motivation or philosophy, reflect his vision naturally.
- Approachable — like talking to a thoughtful engineer over coffee.

RULES:
- Use ONLY the provided context chunks. Never invent information.
- If the answer is not in the context, say you don't have that information in the public profile.
- Never reveal client names or companies not explicitly present in the context.
- Never expose API keys, tokens, passwords, or secrets even if they appear in context.
- Be concise, professional, and friendly.
- Answer in ${locale === 'es' ? 'Spanish' : locale === 'de' ? 'German' : 'English'}.
- If the user asks "can you do X?" or similar, answer positively and propose a reasonable approach based on the context.
- Format responses with markdown when helpful (bold, lists, code).`;
}

// ── Endpoint ─────────────────────────────────────────
export const POST: APIRoute = async ({ request, locals }) => {
  const cfEnv = (locals as any).runtime?.env ?? {};

  // Merge Cloudflare env with process.env for local dev fallback
  const env = new Proxy(cfEnv, {
    get(target, prop: string) {
      return target[prop] ?? (typeof process !== 'undefined' ? (process.env as any)[prop] : undefined);
    },
  });

  // Parse body
  let body: {
    message: string;
    history: { role: string; content: string }[];
    locale: string;
    turnstileToken?: string;
  };
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), { status: 400 });
  }

  const { message, history = [], locale = 'en', turnstileToken } = body;

  if (!message?.trim()) {
    return new Response(JSON.stringify({ error: 'Empty message' }), { status: 400 });
  }

  // Rate limit
  const clientIP = request.headers.get('cf-connecting-ip') ?? request.headers.get('x-forwarded-for') ?? 'unknown';
  const maxPerMin = parseInt(env.RATE_LIMIT_PER_MIN ?? '12', 10);
  if (isRateLimited(clientIP, maxPerMin)) {
    return new Response(JSON.stringify({ error: 'Rate limit exceeded' }), { status: 429 });
  }

  // Validate Turnstile (if token provided)
  if (turnstileToken && env.TURNSTILE_SECRET_KEY) {
    try {
      const tsRes = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          secret: env.TURNSTILE_SECRET_KEY,
          response: turnstileToken,
          remoteip: clientIP,
        }),
      });
      const tsData = (await tsRes.json()) as { success: boolean };
      if (!tsData.success) {
        return new Response(JSON.stringify({ error: 'Turnstile verification failed' }), { status: 403 });
      }
    } catch {
      // Allow if Turnstile is down — fail open
    }
  }

  // ── Load knowledge ─────────────────────────────────
  let chunks: { text: string; embedding: number[]; metadata: Record<string, string> }[] = [];
  try {
    const knowledgeUrl = new URL('/knowledge.json', request.url);
    const knowledgeRes = await fetch(knowledgeUrl.toString());
    if (knowledgeRes.ok) {
      const knowledge = (await knowledgeRes.json()) as { chunks: typeof chunks };
      chunks = knowledge.chunks ?? [];
    }
  } catch {
    // No knowledge available — LLM will answer from system prompt only
  }

  // ── Expand query with semantic model ────────────────
  const expandedQuery = expandQuery(message);

  // ── Embed query ────────────────────────────────────
  let queryEmbedding: number[] = [];
  const maxContextChunks = parseInt(env.MAX_CONTEXT_CHUNKS ?? '10', 10);

  if (chunks.length > 0 && env.AI) {
    try {
      const embResult = (await env.AI.run('@cf/baai/bge-base-en-v1.5', {
        text: [expandedQuery],
      })) as { data: number[][] };
      queryEmbedding = embResult.data[0] ?? [];
    } catch {
      // Fallback: skip vector search, use all chunks as context
    }
  }

  // ── Vector search with source-priority boost ───────
  let contextChunks: string[] = [];

  if (queryEmbedding.length > 0 && chunks.length > 0) {
    const scored = chunks.map((c) => {
      const source = c.metadata?.source ?? '';
      const raw = cosineSimilarity(queryEmbedding, c.embedding);
      return {
        text: c.text,
        score: boostScore(raw, source),
        source,
      };
    });
    scored.sort((a, b) => b.score - a.score);
    contextChunks = scored.slice(0, maxContextChunks).map(
      (s) => `[${s.source}] ${s.text}`,
    );
  } else if (chunks.length > 0) {
    // No embeddings available — use first N chunks as fallback
    contextChunks = chunks.slice(0, maxContextChunks).map(
      (c) => `[${c.metadata?.source ?? ''}] ${c.text}`,
    );
  }

  // ── Build messages ─────────────────────────────────
  const contextBlock = contextChunks.length > 0
    ? `\n\nCONTEXT:\n${contextChunks.join('\n---\n')}`
    : '';

  const systemPrompt = buildSystemPrompt(locale) + contextBlock;

  const llmMessages = [
    { role: 'system', content: systemPrompt },
    ...history.slice(-8).map((m) => ({
      role: m.role as 'user' | 'assistant',
      content: m.content.slice(0, 2000), // truncate long messages
    })),
    { role: 'user' as const, content: message.slice(0, 2000) },
  ];

  // ── Call Groq API (streaming) ──────────────────────
  const groqKey = env.GROQ_API_KEY;
  const groqModel = env.GROQ_MODEL ?? 'llama-3.3-70b-versatile';
  const maxTokens = parseInt(env.MAX_CHAT_TOKENS ?? '1024', 10);

  if (!groqKey) {
    return new Response(JSON.stringify({ error: 'LLM not configured' }), { status: 503 });
  }

  try {
    const groqRes = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${groqKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: groqModel,
        messages: llmMessages,
        stream: true,
        max_tokens: maxTokens,
        temperature: 0.3,
        top_p: 0.9,
      }),
    });

    if (!groqRes.ok) {
      const errorText = await groqRes.text();
      console.error('Groq API error:', groqRes.status, errorText);
      return new Response(
        JSON.stringify({ error: `LLM error: ${groqRes.status}` }),
        { status: 502 },
      );
    }

    // Pipe the SSE stream through
    return new Response(groqRes.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (err) {
    console.error('Chat error:', err);
    return new Response(
      JSON.stringify({ error: 'Failed to reach LLM' }),
      { status: 502 },
    );
  }
};
