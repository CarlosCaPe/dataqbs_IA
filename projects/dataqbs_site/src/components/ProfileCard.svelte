<script lang="ts">
  import { t, locale } from '../i18n/store';
  import { profile, socialLinks } from '../data/cv';
  import { certifications } from '../data/certs';

  $: cvUrl = profile.cvUrls?.[$locale] ?? profile.cvUrl;

  const iconMap: Record<string, string> = {
    github: 'M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.009-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z',
    linkedin: 'M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z',
    email: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    globe: 'M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9',
  };
</script>

<!-- LinkedIn-style Profile Hero Card -->
<section class="card overflow-hidden">
  <!-- Banner (4:1 ratio like LinkedIn) -->
  <div class="relative">
    <div class="aspect-[4/1] overflow-hidden bg-slate-700">
      <img
        src={profile.banner}
        alt={$t.profile.coverAlt}
        class="w-full h-full object-cover"
        loading="eager"
      />
    </div>

    <!-- Profile photo overlapping the banner -->
    <div class="absolute -bottom-16 left-6">
      <div class="w-36 h-36 rounded-full border-4 border-white dark:border-slate-800 overflow-hidden shadow-xl bg-slate-200 dark:bg-slate-700">
        <img
          src={profile.photo}
          alt={profile.name}
          class="w-full h-full object-cover"
          loading="eager"
        />
      </div>
    </div>
  </div>

  <!-- Profile info (below banner, with padding-top for the overflowing photo) -->
  <div class="pt-20 px-6 pb-6">
    <!-- Name row -->
    <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
      <!-- Left: Name, headline, location -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white">{profile.name}</h1>
          <span class="text-sm text-slate-500 dark:text-slate-400">({profile.pronouns})</span>
          <!-- Verified badge -->
          <svg class="w-5 h-5 text-primary-600 dark:text-primary-400 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
            <path d="m11.99 22-1.23-.44C6.11 19.81 2.99 16 2.99 11V5L12 2l9 3v6c0 5-3.11 8.81-7.74 10.56zM5 6.44V11c0 4.11 2.6 7.35 6.46 8.8l.54.2.58-.2C16.41 18.35 19 15.1 19 11V6.44l-7-2.32zM17 8h-2.57l-4.02 5.01-2.18-2.18-1.41 1.41 3.75 3.75 6.43-8z"/>
          </svg>
        </div>

        <p class="text-base text-slate-700 dark:text-slate-200 mt-1 leading-snug">
          {$t.profile.headline}
        </p>

        <!-- Location + Contact info -->
        <div class="flex items-center gap-2 mt-2 text-sm text-slate-500 dark:text-slate-400 flex-wrap">
          <span class="flex items-center gap-1">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            {$t.profile.location}
          </span>
          <span class="text-slate-300 dark:text-slate-600">&middot;</span>
          <a href="mailto:carlos.carrillo@dataqbs.com" class="text-primary-600 dark:text-primary-400 hover:underline font-medium">
            {$t.profile.contactInfo}
          </a>
        </div>

        <!-- Connections -->
        <p class="text-sm text-primary-600 dark:text-primary-400 font-medium mt-1">
          {profile.connections} {$t.profile.connections}
        </p>
      </div>

      <!-- Right: dataqbs brand -->
      <div class="flex-shrink-0 lg:text-right">
        <span class="inline-flex items-center gap-2 rounded-lg p-1 -m-1">
          <span class="text-sm font-semibold text-primary-600 dark:text-primary-400">dataqbs</span>
        </span>
      </div>
    </div>

    <!-- Open to Work badge -->
    {#if profile.openToWork && profile.openToWork.length > 0}
      <div class="mt-4 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800/40">
        <p class="text-sm font-semibold text-emerald-800 dark:text-emerald-300 mb-0.5">{$t.profile.openToWork}</p>
        <p class="text-xs text-emerald-700 dark:text-emerald-400">
          {profile.openToWork.join(', ')} {$t.profile.roles}
        </p>
      </div>
    {/if}

    <!-- Action buttons (LinkedIn-style) -->
    <div class="flex flex-wrap gap-2 mt-4">
      <!-- Contact Me button → scrolls to contact form -->
      <button
        on:click={() => document.getElementById('contact')?.scrollIntoView({ behavior: 'smooth' })}
        class="btn-primary"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        {$t.profile.contactMe}
      </button>
      <a href={cvUrl} target="_blank" rel="noopener" class="btn-secondary">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        {$t.profile.viewCV}
      </a>
      {#each socialLinks as link}
        <a
          href={link.url}
          target={link.platform === 'Email' ? '_self' : '_blank'}
          rel="noopener"
          class="btn-secondary"
          title={link.label}
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24"
            fill={link.platform === 'GitHub' || link.platform === 'LinkedIn' ? 'currentColor' : 'none'}
            stroke={link.platform === 'GitHub' || link.platform === 'LinkedIn' ? 'none' : 'currentColor'}
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={iconMap[link.icon]} />
          </svg>
          <span class="hidden sm:inline">{link.platform}</span>
        </a>
      {/each}
    </div>
  </div>
</section>
