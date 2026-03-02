<script lang="ts">
  import { t, locale } from '../../i18n/store';
  import { onMount } from 'svelte';

  export let propertyTitle: string = '';
  export let propertyId: string = '';

  // ── Contact constants (single source of truth) ───
  const WHATSAPP_NUMBER = '5213313233421';
  const CONTACT_EMAIL   = 'carlos.carrillo@dataqbs.com';

  let name = '';
  let email = '';
  let message = '';
  let sending = false;
  let sent = false;
  let errorMsg = '';
  let turnstileError = false;
  const maxMessageLength = 5000;

  // ── Turnstile ────────────────────────────────────
  const TURNSTILE_SITEKEY = '0x4AAAAAACjWMTF9SAi1pa7U';
  let turnstileToken: string | null = null;

  // Contact channels with property context baked in
  $: whatsappMsg = encodeURIComponent(
    `${$t.re.requestInfo}: ${propertyTitle}`
  );
  $: whatsappUrl = `https://wa.me/${WHATSAPP_NUMBER}?text=${whatsappMsg}`;

  $: emailSubject = encodeURIComponent(`${$t.re.requestInfo}: ${propertyTitle}`);
  $: emailUrl = `mailto:${CONTACT_EMAIL}?subject=${emailSubject}`;

  function renderTurnstile() {
    const container = document.getElementById('re-contact-turnstile');
    if (!container || !(window as any).turnstile) return false;
    (window as any).turnstile.render(container, {
      sitekey: TURNSTILE_SITEKEY,
      callback: (token: string) => { turnstileToken = token; turnstileError = false; },
      'error-callback': () => { turnstileToken = null; turnstileError = true; },
      theme: document.documentElement.classList.contains('dark') ? 'dark' : 'light',
      size: 'invisible',
    });
    return true;
  }

  onMount(() => {
    if (!TURNSTILE_SITEKEY) return;
    if (renderTurnstile()) return;
    // Poll every 500ms until Turnstile script loads (max 10s)
    let attempts = 0;
    const interval = setInterval(() => {
      attempts++;
      if (renderTurnstile() || attempts >= 20) {
        clearInterval(interval);
        if (attempts >= 20 && !turnstileToken) turnstileError = true;
      }
    }, 500);
  });

  async function handleSubmit() {
    if (!name.trim() || !email.trim() || !message.trim()) return;
    // Client-side email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      errorMsg = $t.contact.error;
      return;
    }
    if (message.length > maxMessageLength) {
      errorMsg = `Max ${maxMessageLength} characters`;
      return;
    }

    sending = true;
    errorMsg = '';

    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          message: `[realestate — ${propertyId}] ${propertyTitle}\n\n${message.trim()}`,
          locale: $locale,
          turnstileToken: turnstileToken || '',
        }),
      });

      if (res.ok) {
        sent = true;
        name = '';
        email = '';
        message = '';
      } else {
        const data = await res.json().catch(() => ({}));
        errorMsg = (data as Record<string, string>).error || $t.contact.error;
      }
    } catch {
      errorMsg = $t.contact.error;
    } finally {
      sending = false;
    }
  }
</script>

<section id="contact" class="space-y-6">
  <!-- Section heading -->
  <h2 class="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
    ✉️ {$t.re.contactUs}
  </h2>

  <div class="grid gap-5 lg:grid-cols-2">
    <!-- ── Form ─────────────────────────────────────── -->
    <div class="p-5 rounded-xl bg-slate-50 dark:bg-slate-700/40 border border-slate-200 dark:border-slate-700">
      {#if sent}
        <div class="text-center py-8 animate-fade-in">
          <div class="text-4xl mb-3">✅</div>
          <p class="text-slate-700 dark:text-slate-200 font-medium">{$t.contact.success}</p>
          <button on:click={() => (sent = false)}
            class="mt-4 px-4 py-2 rounded-lg text-sm font-medium text-re-600 dark:text-re-400 border border-re-300 dark:border-re-700 hover:bg-re-50 dark:hover:bg-re-900/20 transition-colors">
            ← {$t.re.requestInfo}
          </button>
        </div>
      {:else}
        <form on:submit|preventDefault={handleSubmit} class="space-y-4">
          <!-- Property badge (read-only context) -->
          <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-re-50 dark:bg-re-900/20 border border-re-200 dark:border-re-800/40 text-sm">
            <span class="text-re-600 dark:text-re-400">🏠</span>
            <span class="text-re-700 dark:text-re-300 font-medium truncate">{propertyTitle}</span>
          </div>

          <div>
            <label for="re-name" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {$t.contact.nameLabel}
            </label>
            <input
              id="re-name"
              bind:value={name}
              placeholder={$t.contact.namePlaceholder}
              class="w-full px-3 py-2 rounded-lg text-sm bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-re-500 focus:border-re-500 outline-none transition-colors"
              required
            />
          </div>
          <div>
            <label for="re-email" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {$t.contact.emailLabel}
            </label>
            <input
              id="re-email"
              type="email"
              bind:value={email}
              placeholder={$t.contact.emailPlaceholder}
              class="w-full px-3 py-2 rounded-lg text-sm bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-re-500 focus:border-re-500 outline-none transition-colors"
              required
            />
          </div>
          <div>
            <label for="re-message" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {$t.contact.messageLabel}
            </label>
            <textarea
              id="re-message"
              bind:value={message}
              placeholder={$t.contact.messagePlaceholder}
              rows="4"
              class="w-full px-3 py-2 rounded-lg text-sm bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-re-500 focus:border-re-500 outline-none transition-colors resize-none"
              required
              maxlength={maxMessageLength}
            ></textarea>
            <p class="text-xs text-slate-400 dark:text-slate-500 text-right mt-0.5">{message.length}/{maxMessageLength}</p>
          </div>

          {#if errorMsg}
            <p class="text-sm text-red-600 dark:text-red-400">{errorMsg}</p>
          {/if}

          {#if turnstileError}
            <p class="text-sm text-amber-600 dark:text-amber-400">⚠️ Security widget failed to load. Please refresh the page.</p>
          {/if}

          <!-- Turnstile invisible widget -->
          <div id="re-contact-turnstile" class="hidden"></div>

          <button type="submit"
            class="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-semibold text-sm bg-re-600 text-white hover:bg-re-700 active:bg-re-800 disabled:opacity-50 transition-colors"
            disabled={sending}>
            {#if sending}
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
            {/if}
            {$t.contact.send}
          </button>
        </form>
      {/if}
    </div>

    <!-- ── Direct contact channels ──────────────────── -->
    <div class="p-5 rounded-xl bg-slate-50 dark:bg-slate-700/40 border border-slate-200 dark:border-slate-700 space-y-3">
      <h3 class="font-semibold text-slate-900 dark:text-white mb-3">{$t.contact.linksHeading}</h3>

      <!-- WhatsApp -->
      <a
        href={whatsappUrl}
        target="_blank"
        rel="noopener noreferrer"
        class="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors group"
      >
        <div class="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center text-green-600 dark:text-green-400 group-hover:scale-110 transition-transform">
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-slate-900 dark:text-white">WhatsApp</p>
        <p class="text-xs text-slate-500 dark:text-slate-400">+52 1 331 323 3421</p>
        </div>
        <svg class="w-4 h-4 text-slate-400 group-hover:text-green-500 transition-colors flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </a>

      <!-- Email -->
      <a
        href={emailUrl}
        rel="noopener noreferrer"
        class="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors group"
      >
        <div class="w-10 h-10 rounded-full bg-re-100 dark:bg-re-900/30 flex items-center justify-center text-re-600 dark:text-re-400 group-hover:scale-110 transition-transform">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-slate-900 dark:text-white">Email</p>
        <p class="text-xs text-slate-500 dark:text-slate-400">{CONTACT_EMAIL}</p>
        </div>
        <svg class="w-4 h-4 text-slate-400 group-hover:text-re-500 transition-colors flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </a>
    </div>
  </div>
</section>
