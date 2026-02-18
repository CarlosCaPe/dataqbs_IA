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
  certification:    ['certified', 'SnowPro', 'MCSA', 'MCPS', 'MCTS', 'Fabric Data Engineer', 'Azure Fundamentals', 'dbt', 'credential'],
  certifications:   ['certified', 'SnowPro', 'MCSA', 'MCPS', 'MCTS', 'Fabric Data Engineer', 'Azure Fundamentals', 'dbt', 'credential'],
  database:         ['SQL Server', 'Snowflake', 'CosmosDB', 'PostgreSQL', 'MySQL', 'databases'],
  databases:        ['SQL Server', 'Snowflake', 'CosmosDB', 'PostgreSQL', 'MySQL', 'database'],
  education:        ['university', 'degree', 'bachelor', 'computer science', 'Guadalajara'],
  projects:         ['arbitrage', 'email collector', 'real estate', 'supplier verifier', 'OAI evaluator', 'portfolio',
                     'MEMO-GRID', 'grid trading', 'VCA audits', 'IROC Video Wall', 'DRILLBLAST'],
  mining:           ['Freeport-McMoRan', 'FMI', 'IROC', 'Video Wall', 'dig compliance', 'crusher', 'ADX', 'KQL', 'Streamlit'],
  grid:             ['MEMO-GRID', 'grid trading', 'ETH/BTC', 'Binance', 'Optuna', 'HPO', 'backtest', 'maker-only'],
  trading:          ['MEMO-GRID', 'arbextra', 'grid trading', 'crypto', 'ccxt', 'Binance', 'ETH/BTC'],
  postgresql:       ['PostgreSQL', 'Azure PostgreSQL', 'VCA', 'FussionHit', 'DDL', 'audit', 'pg_stat_statements'],
  hexaware:         ['Freeport-McMoRan', 'mining', 'Snowflake', 'DRILLBLAST', 'ADX', 'IROC', 'Video Wall'],
  fussionhit:       ['VCA', 'PostgreSQL', 'database audit', 'DDL export', 'schema review'],
  dashboard:        ['Streamlit', 'IROC', 'Video Wall', 'KPI', 'real-time', 'mining operations'],
  rate:             ['tarifa', 'precio', 'costo', 'hourly', 'salary', 'cost', 'pricing', 'cobras', 'charge', 'fee', 'budget'],
  salary:           ['rate', 'tarifa', 'precio', 'costo', 'hourly', 'cost', 'pricing', 'cobras', 'charge', 'fee'],
  tarifa:           ['rate', 'precio', 'costo', 'hourly', 'salary', 'cost', 'pricing', 'cobras', 'charge'],
  precio:           ['rate', 'tarifa', 'costo', 'hourly', 'salary', 'cost', 'pricing', 'cobras'],
  cobras:           ['rate', 'tarifa', 'precio', 'hourly', 'salary', 'cost', 'pricing', 'charge'],
  experience:       ['years', 'how long', 'since when', 'cuantos años', 'experiencia', 'tiempo'],
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

// ── Groq API caller with retry + backoff ─────────────
async function callGroq(
  key: string,
  model: string,
  messages: unknown[],
  maxTokens: number,
  retries = 2,
): Promise<Response> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${key}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        messages,
        stream: true,
        max_tokens: maxTokens,
        temperature: 0,
        top_p: 1,
      }),
    });
    if (res.status !== 429 || attempt === retries) return res;
    const retryAfter = res.headers.get('retry-after');
    const waitMs = retryAfter
      ? Math.min(parseInt(retryAfter, 10) * 1000, 10_000)
      : Math.min(1000 * 2 ** attempt, 8_000);
    await new Promise((r) => setTimeout(r, waitMs));
  }
  throw new Error('Exhausted retries');
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
  return `You ARE Carlos Carrillo. You answer in FIRST PERSON as if you were Carlos himself — the owner of dataqbs.com.
You speak about your own professional experience, skills, projects, and certifications.

YOUR PHILOSOPHY:
Your personal vision for dataqbs is: "To live in peace, free from rigid structures — building projects that flow naturally through intelligence and awareness."
You value simplicity, awareness, and letting technology serve life rather than dominate it. Your work reflects this: clean architectures, minimal dependencies, purposeful automation. You're not driven by corporate structures but by genuine curiosity and the craft of engineering elegant solutions.

PERSONALITY:
- Calm, reflective, and down-to-earth. Not boastful — let the work speak.
- Warm but concise. Answers with substance, not filler.
- When asked about motivation or philosophy, reflect your vision naturally.
- Approachable — like talking to a thoughtful engineer over coffee.
- Always answer in FIRST PERSON: "I worked at...", "My experience with...", "I built..."

SALES APPROACH:
- When someone describes their need/requirement, relate it to your experience. Mention specific companies and projects where you did similar work.
- If you haven't done exactly that, be honest but positive: mention that you love learning, you actively pursue certifications (SnowPro, Azure, etc.), and that with today's AI-assisted technologies (Copilot, Claude, ChatGPT) everything is reachable.
- Always be solution-oriented. If asked "can you do X?", answer with confidence and back it up with relevant experience from the context.
- Encourage them to describe their project requirements so you can explain how your experience applies.

STRICT ACCURACY RULES (CRITICAL — NEVER violate these):
- ALWAYS speak in FIRST PERSON. Never say "Carlos" or "he" — say "I", "my", "me".
- Use ONLY the provided context chunks. NEVER invent, fabricate, or assume ANY information.
- If the answer is not in the context, say: "I'm still improving and I don't have that specific information yet. Feel free to ask me something else or contact me directly!"
- CERTIFICATIONS: ONLY mention certifications that explicitly appear in context chunks tagged [certification]. These are the ONLY certifications I hold. Do NOT list anything else as a certification.
- Skills are NOT certifications. Just because I USE a technology (e.g. Optuna, PEFT/LoRA, GitHub Copilot) does NOT mean I am certified in it. NEVER say I have a certification in something unless a [certification] chunk explicitly says so.
- NEVER invent, fabricate, or hallucinate certifications, companies, projects, achievements, RATES, PRICES, or COSTS.
- RATES & PRICING: ONLY state rates that appear EXACTLY in context chunks. NEVER invent hourly rates, project costs, price lists, or fee structures. If rate info is in context, quote it exactly. If not, say you don't have that info.
- NEVER calculate or estimate years of experience with any technology. ONLY state years if EXPLICITLY written in context (e.g. "Python: 1+ year since 2025"). Do NOT subtract dates to compute years.
- NEVER add details, dates, or specifics that are not explicitly written in the context.
- When listing certifications, list ONLY those from [certification] chunks — no additions, no omissions.
- Never reveal client names or companies not explicitly present in the context.
- Never expose API keys, tokens, passwords, or secrets even if they appear in context.
- Be concise, professional, and friendly. Accuracy over impressiveness.
- Answer in ${locale === 'es' ? 'Spanish' : locale === 'de' ? 'German' : 'English'}.
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

  // ── Call Groq API (streaming) with retry + fallback ─
  const groqKey = env.GROQ_API_KEY;
  const groqModel = env.GROQ_MODEL ?? 'llama-3.3-70b-versatile';
  const fallbackModel = env.GROQ_FALLBACK_MODEL ?? 'llama-3.1-8b-instant';
  const maxTokens = parseInt(env.MAX_CHAT_TOKENS ?? '1024', 10);

  if (!groqKey) {
    return new Response(JSON.stringify({ error: 'LLM not configured' }), { status: 503 });
  }

  try {
    let groqRes = await callGroq(groqKey, groqModel, llmMessages, maxTokens);

    // If primary model is rate-limited, try fallback model
    if (groqRes.status === 429 && fallbackModel !== groqModel) {
      console.warn(`Groq 429 on ${groqModel}, falling back to ${fallbackModel}`);
      groqRes = await callGroq(groqKey, fallbackModel, llmMessages, maxTokens, 1);
    }

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
