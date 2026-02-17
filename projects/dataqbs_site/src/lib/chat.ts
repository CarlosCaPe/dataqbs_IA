/**
 * Client-side chat logic: sends messages to /api/chat and reads streamed responses.
 */
import type { ChatMessage, ChatStatus } from './types';

const MAX_HISTORY = 8; // last N turns to send as context

export interface SendMessageOptions {
  message: string;
  history: ChatMessage[];
  locale: string;
  turnstileToken?: string;
  onChunk: (text: string) => void;
  onDone: (fullText: string) => void;
  onError: (error: string) => void;
}

export async function sendChatMessage(opts: SendMessageOptions): Promise<void> {
  const { message, history, locale, turnstileToken, onChunk, onDone, onError } = opts;

  // Trim history to last N messages
  const trimmedHistory = history.slice(-MAX_HISTORY).map((m) => ({
    role: m.role,
    content: m.content,
  }));

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        history: trimmedHistory,
        locale,
        turnstileToken,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const msg = (errorData as Record<string, string>).error || `Error ${response.status}`;
      onError(msg);
      return;
    }

    // Read streamed response
    const reader = response.body?.getReader();
    if (!reader) {
      onError('No response body');
      return;
    }

    const decoder = new TextDecoder();
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });

      // Parse SSE lines
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            onDone(fullText);
            return;
          }
          try {
            const parsed = JSON.parse(data);
            const delta = parsed.choices?.[0]?.delta?.content ?? '';
            if (delta) {
              fullText += delta;
              onChunk(fullText);
            }
          } catch {
            // If not JSON, treat as plain text
            fullText += data;
            onChunk(fullText);
          }
        }
      }
    }

    onDone(fullText);
  } catch (err) {
    onError(err instanceof Error ? err.message : 'Network error');
  }
}

/**
 * Simple rate limiter: tracks timestamps of recent messages.
 */
export class RateLimiter {
  private timestamps: number[] = [];
  private maxPerMinute: number;

  constructor(maxPerMinute = 12) {
    this.maxPerMinute = maxPerMinute;
  }

  canSend(): boolean {
    const now = Date.now();
    this.timestamps = this.timestamps.filter((t) => now - t < 60_000);
    return this.timestamps.length < this.maxPerMinute;
  }

  record(): void {
    this.timestamps.push(Date.now());
  }
}
