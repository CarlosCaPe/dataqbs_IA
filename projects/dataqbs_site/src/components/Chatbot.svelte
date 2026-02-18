<script lang="ts">
  import { t, locale } from '../i18n/store';
  import { sendChatMessage, RateLimiter } from '../lib/chat';
  import { renderMarkdown } from '../lib/markdown';
  import type { ChatMessage, ChatStatus } from '../lib/types';
  import { onMount, tick } from 'svelte';

  // ── State ────────────────────────────────────────
  let messages: ChatMessage[] = [];
  let inputValue = '';
  let status: ChatStatus = 'idle';
  let isOpen = false;
  let turnstileToken: string | null = null;
  let turnstileWidgetId: string | null = null;
  let messagesContainer: HTMLDivElement;
  let inputElement: HTMLInputElement;

  const rateLimiter = new RateLimiter(12);

  // ── Turnstile ────────────────────────────────────
  onMount(() => {
    messages = [
      {
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
      },
    ];
  });

  function initTurnstile() {
    if (turnstileToken || turnstileWidgetId) return;
    const container = document.getElementById('turnstile-container');
    if (!container || !(window as any).turnstile) return;

    status = 'verifying';
    turnstileWidgetId = (window as any).turnstile.render(container, {
      sitekey: '0x4AAAAAAAAAAAAAAAAAAAAAAA',
      callback: (token: string) => {
        turnstileToken = token;
        status = 'ready';
      },
      'error-callback': () => {
        status = 'error';
      },
      theme: document.documentElement.classList.contains('dark') ? 'dark' : 'light',
      size: 'invisible',
    });
  }

  // ── Send message ─────────────────────────────────
  async function handleSend() {
    const msg = inputValue.trim();
    if (!msg || status === 'sending' || status === 'streaming') return;

    if (!rateLimiter.canSend()) {
      status = 'error';
      return;
    }

    if (!turnstileToken && status === 'idle') {
      initTurnstile();
      await new Promise((r) => setTimeout(r, 1500));
    }

    const userMsg: ChatMessage = { role: 'user', content: msg, timestamp: Date.now() };
    messages = [...messages, userMsg];
    inputValue = '';
    status = 'sending';
    rateLimiter.record();
    await scrollToBottom();

    const assistantMsg: ChatMessage = { role: 'assistant', content: '', timestamp: Date.now() };
    messages = [...messages, assistantMsg];

    await sendChatMessage({
      message: msg,
      history: messages.filter((m) => m.role !== 'system'),
      locale: $locale,
      turnstileToken: turnstileToken ?? undefined,
      onChunk: (text) => {
        status = 'streaming';
        messages = messages.map((m, i) =>
          i === messages.length - 1 ? { ...m, content: text } : m,
        );
        scrollToBottom();
      },
      onDone: (fullText) => {
        status = 'ready';
        messages = messages.map((m, i) =>
          i === messages.length - 1 ? { ...m, content: fullText } : m,
        );
        scrollToBottom();
      },
      onError: (error) => {
        status = 'error';
        messages = messages.map((m, i) =>
          i === messages.length - 1 ? { ...m, content: `⚠️ ${error}` } : m,
        );
        scrollToBottom();
      },
    });
  }

  // ── Suggestion chips ─────────────────────────────
  function sendSuggestion(text: string) {
    inputValue = text;
    handleSend();
  }

  // ── Export chat history for contact form ──────────
  function getChatTranscript(): string {
    return messages
      .filter((m) => m.content)
      .map((m) => `${m.role === 'user' ? 'User' : 'Carlos AI'}: ${m.content}`)
      .join('\n\n');
  }

  // Expose transcript globally for contact form
  $: if (typeof window !== 'undefined') {
    (window as any).__chatTranscript = messages.length > 1 ? getChatTranscript() : '';
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  async function scrollToBottom() {
    await tick();
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  function toggleChat() {
    isOpen = !isOpen;
    if (isOpen) {
      tick().then(() => inputElement?.focus());
    }
  }
</script>

<!-- ── Desktop: collapsible right-edge tab + panel ───── -->
<div class="hidden lg:block fixed top-24 right-0 z-40 transition-transform duration-300 ease-in-out"
  class:translate-x-full={!isOpen}
  class:translate-x-0={isOpen}
  style="width: 380px;"
>
  <!-- The tab handle (always visible, sticking out to the left) -->
  <button
    on:click={toggleChat}
    class="absolute -left-10 top-4 w-10 h-24 flex flex-col items-center justify-center gap-1
           bg-primary-600 hover:bg-primary-700 text-white rounded-l-lg shadow-lg
           transition-colors duration-200 z-50"
    aria-label={isOpen ? $t.chat.closeChat : $t.chat.openChat}
  >
    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
    <span class="text-xs font-bold writing-vertical">AI</span>
  </button>

  <!-- Chat panel -->
  <div class="flex flex-col h-[calc(100vh-7rem)] bg-white dark:bg-slate-800 border-l border-t border-b border-slate-200 dark:border-slate-700 rounded-l-xl shadow-2xl">
    <!-- Header -->
    <div class="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
        <h3 class="font-semibold text-sm text-slate-900 dark:text-white">{$t.chat.title}</h3>
      </div>
      <button on:click={toggleChat} class="btn-ghost p-1" aria-label={$t.chat.closeChat}>
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Messages -->
    <div bind:this={messagesContainer} class="flex-1 overflow-y-auto p-4 space-y-4">
      {#each messages as msg, i}
        <div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up">
          <div
            class="max-w-[85%] rounded-2xl px-4 py-2.5 text-sm
              {msg.role === 'user'
                ? 'bg-primary-600 text-white rounded-br-md'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-bl-md'}"
          >
            {#if msg.role === 'assistant' && i === 0}
              <div class="chat-markdown">{@html renderMarkdown($t.chat.welcome)}</div>
            {:else if msg.role === 'assistant' && msg.content}
              <div class="chat-markdown">{@html renderMarkdown(msg.content)}</div>
            {:else if msg.role === 'assistant' && !msg.content}
              <div class="flex items-center gap-1.5 py-1">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
              </div>
            {:else}
              {msg.content}
            {/if}
          </div>
        </div>
      {/each}

      <!-- Suggestion chips (show only when no user messages yet) -->
      {#if messages.length <= 1}
        <div class="flex flex-wrap gap-2 mt-2">
          <button on:click={() => sendSuggestion($t.chat.suggestion1)}
            class="text-xs px-3 py-1.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/40 transition-colors">
            💬 {$t.chat.suggestion1}
          </button>
          <button on:click={() => sendSuggestion($t.chat.suggestion2)}
            class="text-xs px-3 py-1.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/40 transition-colors">
            🏢 {$t.chat.suggestion2}
          </button>
          <button on:click={() => sendSuggestion($t.chat.suggestion3)}
            class="text-xs px-3 py-1.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/40 transition-colors">
            ❄️ {$t.chat.suggestion3}
          </button>
          <button on:click={() => sendSuggestion($t.chat.suggestion4)}
            class="text-xs px-3 py-1.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/40 transition-colors">
            🎓 {$t.chat.suggestion4}
          </button>
        </div>
      {/if}
    </div>

    <!-- Turnstile (invisible) -->
    <div id="turnstile-container" class="hidden"></div>

    <!-- Input -->
    <div class="p-3 border-t border-slate-200 dark:border-slate-700">
      <p class="text-[10px] text-slate-400 dark:text-slate-500 text-center mb-1.5">🔒 {$t.chat.privacyNote}</p>
      {#if status === 'error' && !rateLimiter.canSend()}
        <p class="text-xs text-amber-600 dark:text-amber-400 mb-2 text-center">{$t.chat.rateLimit}</p>
      {/if}
      <div class="flex gap-2">
        <input
          bind:this={inputElement}
          bind:value={inputValue}
          on:keydown={handleKeydown}
          placeholder={$t.chat.placeholder}
          class="input-field flex-1"
          disabled={status === 'sending' || status === 'streaming'}
        />
        <button
          on:click={handleSend}
          class="btn-primary px-3"
          disabled={!inputValue.trim() || status === 'sending' || status === 'streaming'}
          aria-label={$t.chat.send}
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</div>

<!-- ── Mobile: FAB + drawer ───────────────────────── -->
<div class="lg:hidden">
  <!-- FAB -->
  {#if !isOpen}
    <button
      on:click={toggleChat}
      class="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-primary-600 text-white shadow-lg
             hover:bg-primary-700 active:bg-primary-800 transition-all duration-200
             flex items-center justify-center"
      aria-label={$t.chat.openChat}
    >
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    </button>
  {/if}

  <!-- Drawer overlay -->
  {#if isOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" on:click={toggleChat}></div>

    <div class="fixed bottom-0 left-0 right-0 z-50 h-[85vh] flex flex-col rounded-t-2xl bg-white dark:bg-slate-800 shadow-2xl animate-slide-up">
      <!-- Drawer header -->
      <div class="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          <h3 class="font-semibold text-sm">{$t.chat.title}</h3>
        </div>
        <button on:click={toggleChat} class="btn-ghost p-1" aria-label={$t.chat.closeChat}>
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Messages (mobile) -->
      <div bind:this={messagesContainer} class="flex-1 overflow-y-auto p-4 space-y-4">
        {#each messages as msg, i}
          <div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
            <div
              class="max-w-[85%] rounded-2xl px-4 py-2.5 text-sm
                {msg.role === 'user'
                  ? 'bg-primary-600 text-white rounded-br-md'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-bl-md'}"
            >
              {#if msg.role === 'assistant' && i === 0}
                <div class="chat-markdown">{@html renderMarkdown($t.chat.welcome)}</div>
              {:else if msg.role === 'assistant' && msg.content}
                <div class="chat-markdown">{@html renderMarkdown(msg.content)}</div>
              {:else if msg.role === 'assistant' && !msg.content}
                <div class="flex items-center gap-1.5 py-1">
                  <div class="typing-dot"></div>
                  <div class="typing-dot"></div>
                  <div class="typing-dot"></div>
                </div>
              {:else}
                {msg.content}
              {/if}
            </div>
          </div>
        {/each}

        <!-- Suggestion chips (mobile, show only when no user messages yet) -->
        {#if messages.length <= 1}
          <div class="flex flex-wrap gap-2 mt-2">
            <button on:click={() => sendSuggestion($t.chat.suggestion1)}
              class="text-xs px-3 py-1.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/40 transition-colors">
              💬 {$t.chat.suggestion1}
            </button>
            <button on:click={() => sendSuggestion($t.chat.suggestion2)}
              class="text-xs px-3 py-1.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/40 transition-colors">
              🏢 {$t.chat.suggestion2}
            </button>
            <button on:click={() => sendSuggestion($t.chat.suggestion3)}
              class="text-xs px-3 py-1.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/40 transition-colors">
              ❄️ {$t.chat.suggestion3}
            </button>
            <button on:click={() => sendSuggestion($t.chat.suggestion4)}
              class="text-xs px-3 py-1.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/40 transition-colors">
              🎓 {$t.chat.suggestion4}
            </button>
          </div>
        {/if}
      </div>

      <!-- Turnstile mobile -->
      <div id="turnstile-container-mobile" class="hidden"></div>

      <!-- Input (mobile) -->
      <div class="p-3 border-t border-slate-200 dark:border-slate-700 pb-safe">
        <p class="text-[10px] text-slate-400 dark:text-slate-500 text-center mb-1.5">🔒 {$t.chat.privacyNote}</p>
        <div class="flex gap-2">
          <input
            bind:this={inputElement}
            bind:value={inputValue}
            on:keydown={handleKeydown}
            placeholder={$t.chat.placeholder}
            class="input-field flex-1"
            disabled={status === 'sending' || status === 'streaming'}
          />
          <button
            on:click={handleSend}
            class="btn-primary px-3"
            disabled={!inputValue.trim() || status === 'sending' || status === 'streaming'}
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .writing-vertical {
    writing-mode: vertical-rl;
    text-orientation: upright;
    letter-spacing: -0.05em;
  }
</style>
