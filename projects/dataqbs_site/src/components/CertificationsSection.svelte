<script lang="ts">
  import { t } from '../i18n/store';
  import { certifications } from '../data/certs';

  const INITIAL_COUNT = 2;
  let showAll = false;
  $: displayed = showAll ? certifications : certifications.slice(0, INITIAL_COUNT);
</script>

<section id="certifications" class="card p-6">
  <h2 class="section-heading-sm mb-4">
    <svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
    </svg>
    {$t.sections.certifications}
  </h2>

  <div class="space-y-4">
    {#each displayed as cert, i}
      <div class="flex items-start gap-4 p-4 rounded-lg bg-slate-50 dark:bg-slate-700/40 border border-slate-100 dark:border-slate-700 animate-fade-in" style="animation-delay: {i * 60}ms">
        <!-- Logo / Emoji -->
        <div class="flex-shrink-0 w-12 h-12 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 flex items-center justify-center text-2xl shadow-sm">
          {cert.logo || '🏅'}
        </div>

        <!-- Details -->
        <div class="flex-1 min-w-0">
          <h3 class="font-semibold text-slate-900 dark:text-white text-sm leading-snug">
            {cert.name}
          </h3>

          <p class="text-sm text-slate-600 dark:text-slate-300 mt-0.5">
            {cert.issuer}
          </p>

          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {$t.cert.issuedBy} {cert.issuer} · {cert.year}
            {#if cert.expired}
              <span class="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
                Expired
              </span>
            {:else if cert.expiresYear}
              <span class="ml-1 text-slate-400 dark:text-slate-500">
                · Expires {cert.expiresYear}
              </span>
            {/if}
          </p>

          {#if cert.credentialId}
            <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
              Credential ID: {cert.credentialId}
            </p>
          {/if}
        </div>

        <!-- Verify link -->
        {#if cert.credentialUrl}
          <a
            href={cert.credentialUrl}
            target="_blank"
            rel="noopener"
            class="flex-shrink-0 text-xs text-primary-600 dark:text-primary-400 hover:underline font-medium self-center"
          >
            {$t.cert.verify} ↗
          </a>
        {/if}
      </div>
    {/each}
  </div>

  <!-- Show all / Show less button (LinkedIn-style) -->
  {#if certifications.length > INITIAL_COUNT}
    <div class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-700 text-center">
      <button on:click={() => (showAll = !showAll)} class="text-sm font-semibold text-slate-600 dark:text-slate-300 hover:text-primary-600 dark:hover:text-primary-400 transition-colors w-full py-2 flex items-center justify-center gap-1.5">
        {#if showAll}
          {$t.timeline.showLess}
        {:else}
          {$t.timeline.showAllCertifications.replace('{count}', String(certifications.length))}
        {/if}
        <svg class="w-4 h-4 transition-transform" class:rotate-180={showAll} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    </div>
  {/if}
</section>
