<script lang="ts">
  import { onMount } from 'svelte';
  import { t, locale } from '../../i18n/store';
  import type { Locale } from '../../i18n/translations';
  import { supportedLocales } from '../../i18n/translations';

  let isDark = true;
  let langOpen = false;

  onMount(() => {
    isDark = document.documentElement.classList.contains('dark');
  });

  function toggleTheme() {
    isDark = !isDark;
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  }

  function setLocale(loc: Locale) {
    locale.set(loc);
    langOpen = false;
  }
</script>

<header class="sticky top-0 z-40 backdrop-blur-md bg-white/80 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-700/50 relative">
  <!-- Decorative RE cubes (inline SVG to avoid Firefox sizing bug with <img> SVG) -->
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="40" height="40" fill="none" class="absolute left-2 top-1/2 -translate-y-1/2 opacity-[0.06] pointer-events-none select-none" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#dc2626"/><text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-family="Inter,system-ui,sans-serif" font-weight="700" font-size="28" fill="white">RE</text></svg>
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="40" height="40" fill="none" class="absolute right-2 top-1/2 -translate-y-1/2 opacity-[0.06] pointer-events-none select-none" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#dc2626"/><text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-family="Inter,system-ui,sans-serif" font-weight="700" font-size="28" fill="white">RE</text></svg>

  <div class="max-w-5xl mx-auto px-4 sm:px-6 relative">
    <div class="flex items-center justify-between h-16">

      <!-- RS Logo -->
      <a href="/realestate" class="flex items-center gap-2 font-bold text-lg text-re-600 dark:text-re-400">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="32" height="32" fill="none" class="w-8 h-8 flex-shrink-0"><rect width="64" height="64" rx="14" fill="#dc2626"/><text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-family="Inter,system-ui,sans-serif" font-weight="700" font-size="28" fill="white">RE</text></svg>
        <span class="hidden sm:inline">realestate</span>
      </a>

      <!-- Controls -->
      <div class="flex items-center gap-2">

        <!-- Language selector -->
        <div class="relative">
          <button on:click|stopPropagation={() => (langOpen = !langOpen)}
            class="inline-flex items-center gap-2 px-3 py-2 rounded-lg font-medium text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all duration-150"
            aria-label={$t.lang.label}>
            🌐 <span class="hidden sm:inline">{$locale.toUpperCase()}</span>
          </button>
          {#if langOpen}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div class="absolute right-0 mt-2 w-36 card p-1 shadow-lg z-50" on:click|stopPropagation>
              {#each supportedLocales as loc}
                <button
                  on:click={() => setLocale(loc)}
                  class="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  class:font-semibold={$locale === loc}
                  class:text-re-600={$locale === loc}
                  class:dark:text-re-400={$locale === loc}
                >
                  {$t.lang[loc]}
                </button>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Theme toggle -->
        <button on:click={toggleTheme}
          class="inline-flex items-center gap-2 px-3 py-2 rounded-lg font-medium text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all duration-150"
          aria-label={$t.theme.toggle}>
          {#if isDark}
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          {:else}
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          {/if}
        </button>
      </div>
    </div>
  </div>
</header>

<!-- Close dropdown on outside click -->
<svelte:window on:click={() => (langOpen = false)} />
