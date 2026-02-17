/// <reference path="../.astro/types.d.ts" />
/// <reference types="astro/client" />

type Runtime = import('@astrojs/cloudflare').Runtime<{
  AI: {
    run: (model: string, input: Record<string, unknown>) => Promise<unknown>;
  };
  GROQ_API_KEY: string;
  GROQ_MODEL: string;
  MAX_CHAT_TOKENS: string;
  MAX_CONTEXT_CHUNKS: string;
  RATE_LIMIT_PER_MIN: string;
  TURNSTILE_SECRET_KEY: string;
  SITE_CONTACT_EMAIL: string;
  CONTACT_STORE?: KVNamespace;
}>;

declare namespace App {
  interface Locals extends Runtime {}
}
