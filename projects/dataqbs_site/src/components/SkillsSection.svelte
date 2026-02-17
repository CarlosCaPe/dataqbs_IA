<script lang="ts">
  import { t } from '../i18n/store';
  import { skills } from '../data/cv';

  const levelWidth: Record<string, string> = {
    expert: 'w-full',
    advanced: 'w-3/4',
    intermediate: 'w-1/2',
  };

  const levelColor: Record<string, string> = {
    expert: 'bg-primary-500',
    advanced: 'bg-primary-400',
    intermediate: 'bg-primary-300 dark:bg-primary-600',
  };
</script>

<section id="skills" class="card p-6">
  <h2 class="section-heading-sm mb-4">
    <svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
    {$t.sections.skills}
  </h2>

  <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
    {#each skills as group, gi}
      <div class="p-5 animate-fade-in rounded-lg bg-slate-50 dark:bg-slate-700/40 border border-slate-100 dark:border-slate-700" style="animation-delay: {gi * 60}ms">
        <h3 class="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
          <span class="text-lg">{group.icon}</span>
          {group.category}
        </h3>
        <div class="space-y-3">
          {#each group.skills as skill}
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm text-slate-700 dark:text-slate-200">{skill.name}</span>
                <span class="text-xs text-slate-500 dark:text-slate-400">{$t.skill[skill.level]}</span>
              </div>
              <div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5">
                <div class="skill-level-bar {levelWidth[skill.level]} {levelColor[skill.level]} transition-all duration-500"></div>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  </div>
</section>
