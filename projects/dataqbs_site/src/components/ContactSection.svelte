<script lang="ts">
  import { t, locale } from '../i18n/store';
  import { socialLinks } from '../data/cv';

  let name = '';
  let email = '';
  let message = '';
  let sending = false;
  let sent = false;
  let errorMsg = '';

  async function handleSubmit() {
    if (!name.trim() || !email.trim() || !message.trim()) return;

    sending = true;
    errorMsg = '';

    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          message: message.trim(),
          locale: $locale,
          turnstileToken: '', // could integrate Turnstile here too
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

  const platformIcons: Record<string, string> = {
    GitHub: 'M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.009-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z',
    LinkedIn: 'M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z',
    Email: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    Website: 'M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9',
  };
  const fillIcons = new Set(['GitHub', 'LinkedIn']);
</script>

<section id="contact" class="card p-6">
  <h2 class="section-heading-sm mb-4">
    <svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
    {$t.sections.contact}
  </h2>

  <div class="grid gap-6 lg:grid-cols-2">
    <!-- Contact form -->
    <div class="p-5 rounded-lg bg-slate-50 dark:bg-slate-700/40 border border-slate-100 dark:border-slate-700">
      {#if sent}
        <div class="text-center py-8 animate-fade-in">
          <div class="text-4xl mb-3">✅</div>
          <p class="text-slate-700 dark:text-slate-200 font-medium">{$t.contact.success}</p>
          <button on:click={() => (sent = false)} class="btn-secondary mt-4">
            ← {$t.contact.send}
          </button>
        </div>
      {:else}
        <form on:submit|preventDefault={handleSubmit} class="space-y-4">
          <div>
            <label for="contact-name" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {$t.contact.nameLabel}
            </label>
            <input
              id="contact-name"
              bind:value={name}
              placeholder={$t.contact.namePlaceholder}
              class="input-field"
              required
            />
          </div>
          <div>
            <label for="contact-email" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {$t.contact.emailLabel}
            </label>
            <input
              id="contact-email"
              type="email"
              bind:value={email}
              placeholder={$t.contact.emailPlaceholder}
              class="input-field"
              required
            />
          </div>
          <div>
            <label for="contact-message" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {$t.contact.messageLabel}
            </label>
            <textarea
              id="contact-message"
              bind:value={message}
              placeholder={$t.contact.messagePlaceholder}
              rows="4"
              class="input-field resize-none"
              required
            ></textarea>
          </div>
          {#if errorMsg}
            <p class="text-sm text-red-600 dark:text-red-400">{errorMsg}</p>
          {/if}
          <button type="submit" class="btn-primary w-full" disabled={sending}>
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

    <!-- Social links -->
    <div class="p-5 rounded-lg bg-slate-50 dark:bg-slate-700/40 border border-slate-100 dark:border-slate-700">
      <h3 class="font-semibold text-slate-900 dark:text-white mb-4">{$t.contact.linksHeading}</h3>
      <div class="space-y-3">
        {#each socialLinks as link}
          <a
            href={link.url}
            target={link.platform === 'Email' ? '_self' : '_blank'}
            rel="noopener"
            class="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group"
          >
            <div class="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-primary-600 dark:text-primary-400 group-hover:scale-110 transition-transform">
              <svg class="w-5 h-5" viewBox="0 0 24 24"
                fill={fillIcons.has(link.platform) ? 'currentColor' : 'none'}
                stroke={fillIcons.has(link.platform) ? 'none' : 'currentColor'}
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d={platformIcons[link.platform] || platformIcons.Website} />
              </svg>
            </div>
            <div>
              <p class="text-sm font-medium text-slate-900 dark:text-white">{link.platform}</p>
              <p class="text-xs text-slate-500 dark:text-slate-400">{link.label}</p>
            </div>
            <svg class="w-4 h-4 ml-auto text-slate-400 group-hover:text-primary-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        {/each}
      </div>
    </div>
  </div>
</section>
