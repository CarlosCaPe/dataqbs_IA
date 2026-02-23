<script lang="ts">
  import { t, locale } from '../i18n/store';
  import { experience } from '../data/cv';
  import { experienceTranslations } from '../data/cv_translations';

  const localeMap: Record<string, string> = { en: 'en-US', es: 'es-MX', de: 'de-DE' };

  const INITIAL_COUNT = 3;
  let showAll = false;
  let expandedIndex: number | null = null;

  // Reactive translations — re-computes whenever $locale changes
  $: localizedExperience = experience.map((exp, i) => {
    const tr = ($locale !== 'en') ? experienceTranslations[$locale]?.[i] : null;
    return {
      ...exp,
      description: tr?.description ?? exp.description,
      achievements: (tr?.achievements?.length) ? tr.achievements : exp.achievements,
    };
  });

  $: displayed = showAll ? localizedExperience : localizedExperience.slice(0, INITIAL_COUNT);

  function toggle(i: number) {
    expandedIndex = expandedIndex === i ? null : i;
  }

  function formatPeriod(start: string, end: string | null, loc: string, present: string): string {
    const bcp = localeMap[loc] || 'en-US';
    const s = new Date(start + '-01').toLocaleDateString(bcp, { year: 'numeric', month: 'short' });
    const e = end ? new Date(end + '-01').toLocaleDateString(bcp, { year: 'numeric', month: 'short' }) : present;
    return `${s} — ${e}`;
  }

  const typeColors: Record<string, string> = {
    'full-time': 'badge-blue',
    'contract': 'badge-purple',
    'freelance': 'badge-amber',
    'self-employed': 'badge-green',
  };
</script>

<section id="experience" class="card p-6">
  <h2 class="section-heading-sm mb-4">
    <svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
    {$t.sections.experience}
  </h2>

  <div class="relative">
    <!-- Timeline line -->
    <div class="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-200 dark:bg-slate-700"></div>

    <div class="space-y-6">
      {#each displayed as exp, i}
        <div class="relative pl-10 animate-fade-in" style="animation-delay: {i * 80}ms">
          <!-- Timeline dot -->
          <div class="absolute left-2.5 top-2 w-3 h-3 rounded-full border-2 border-primary-500 bg-white dark:bg-slate-900 z-10"></div>

          <div class="p-5 rounded-lg bg-slate-50 dark:bg-slate-700/40 border border-slate-100 dark:border-slate-700">
            <!-- Header -->
            <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-2">
              <div>
                <h3 class="font-semibold text-slate-900 dark:text-white text-lg">{exp.role}</h3>
                <p class="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-2 mt-0.5">
                  {exp.hidden ? $t.timeline.confidential : exp.company}
                  <span class={typeColors[exp.type] || 'badge-blue'}>{$t.experienceType[exp.type] ?? exp.type}</span>
                </p>
              </div>
              <div class="text-sm text-slate-500 dark:text-slate-400 whitespace-nowrap flex items-center gap-1">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                {formatPeriod(exp.period.start, exp.period.end, $locale, $t.timeline.present)}
              </div>
            </div>

            <!-- Location -->
            <p class="text-xs text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              </svg>
              {exp.location}
            </p>

            <!-- Description -->
            <p class="text-sm text-slate-600 dark:text-slate-300 mb-3">{exp.description}</p>

            <!-- Expandable achievements -->
            {#if exp.achievements.length > 0}
              <button
                on:click={() => toggle(i)}
                class="text-xs text-primary-600 dark:text-primary-400 hover:underline mb-3 flex items-center gap-1"
              >
                <svg class="w-3.5 h-3.5 transition-transform" class:rotate-90={expandedIndex === i} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
                {expandedIndex === i ? $t.timeline.showLess : $t.timeline.showMore}
              </button>

              {#if expandedIndex === i}
                <ul class="space-y-1.5 mb-3 animate-slide-up">
                  {#each exp.achievements as ach}
                    <li class="text-sm text-slate-600 dark:text-slate-300 flex items-start gap-2">
                      <span class="text-primary-500 mt-1.5 flex-shrink-0">
                        <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 8 8"><circle cx="4" cy="4" r="3"/></svg>
                      </span>
                      {ach}
                    </li>
                  {/each}
                </ul>
              {/if}
            {/if}

            <!-- Tech tags -->
            <div class="flex flex-wrap gap-1.5">
              {#each exp.technologies as tech}
                <span class="badge-blue">{tech}</span>
              {/each}
            </div>
          </div>
        </div>
      {/each}
    </div>
  </div>

  <!-- Show all / Show less (LinkedIn-style) -->
  {#if experience.length > INITIAL_COUNT}
    <div class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-700 text-center">
      <button on:click={() => (showAll = !showAll)} class="text-sm font-semibold text-slate-600 dark:text-slate-300 hover:text-primary-600 dark:hover:text-primary-400 transition-colors w-full py-2 flex items-center justify-center gap-1.5">
        {#if showAll}
          {$t.timeline.showLess}
        {:else}
          {$t.timeline.showAllExperiences.replace('{count}', String(experience.length))}
        {/if}
        <svg class="w-4 h-4 transition-transform" class:rotate-180={showAll} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    </div>
  {/if}
</section>
