<script lang="ts">
  import { onMount } from 'svelte';
  import { t, locale } from '../i18n/store';
  import type { Locale } from '../i18n/translations';
  import { supportedLocales } from '../i18n/translations';

  let isDark = true; // default dark
  let mobileMenuOpen = false;
  let langOpen = false;

  onMount(() => {
    // Sync with the actual DOM state set by the inline script in Layout
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

  function scrollTo(id: string) {
    mobileMenuOpen = false;
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  }

  const navItems = ['experience', 'projects', 'skills', 'contact'] as const;
</script>

<header class="sticky top-0 z-40 backdrop-blur-md bg-white/80 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-700/50">
  <!-- Decorative cubes pinned to edges -->
  <img src="/favicon.svg" alt="" class="absolute left-0 top-0 h-full w-auto opacity-[0.07] pointer-events-none select-none" aria-hidden="true" />
  <img src="/favicon.svg" alt="" class="absolute right-0 top-0 h-full w-auto opacity-[0.07] pointer-events-none select-none" aria-hidden="true" />

  <div class="max-w-4xl mx-auto px-4 sm:px-6 relative">
    <div class="flex items-center justify-between h-16">

      <!-- Logo -->
      <a href="/" class="flex items-center gap-2 font-bold text-lg text-primary-600 dark:text-primary-400">
        <img src="/favicon.svg" alt="dataqbs" class="w-8 h-8" />
        <span class="hidden sm:inline">dataqbs</span>
      </a>

      <!-- Desktop nav -->
      <nav class="hidden md:flex items-center gap-1">
        {#each navItems as item}
          <button on:click={() => scrollTo(item)} class="btn-ghost text-sm">
            {$t.nav[item]}
          </button>
        {/each}
      </nav>

      <!-- Controls -->
      <div class="flex items-center gap-2">

        <!-- Language selector -->
        <div class="relative">
          <button on:click|stopPropagation={() => (langOpen = !langOpen)} class="btn-ghost text-sm" aria-label={$t.lang.label}>
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
                  class:text-primary-600={$locale === loc}
                  class:dark:text-primary-400={$locale === loc}
                >
                  {$t.lang[loc]}
                </button>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Theme toggle -->
        <button on:click={toggleTheme} class="btn-ghost" aria-label={$t.theme.toggle}>
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

        <!-- Mobile menu button -->
        <button on:click={() => (mobileMenuOpen = !mobileMenuOpen)} class="btn-ghost md:hidden" aria-label={$t.nav.menu}>
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {#if mobileMenuOpen}
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            {:else}
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            {/if}
          </svg>
        </button>
      </div>
    </div>

    <!-- Mobile nav -->
    {#if mobileMenuOpen}
      <nav class="md:hidden pb-4 border-t border-slate-200 dark:border-slate-700 pt-3 flex flex-col gap-1 animate-slide-up">
        {#each navItems as item}
          <button on:click={() => scrollTo(item)} class="btn-ghost text-left w-full">
            {$t.nav[item]}
          </button>
        {/each}
      </nav>
    {/if}
  </div>
</header>

<!-- Close dropdown on outside click -->
<svelte:window on:click={() => (langOpen = false)} />
