<script lang="ts">
  import { t } from '../i18n/store';
  import { projects } from '../data/projects';

  let showAll = false;

  $: featured = projects.filter((p) => p.featured);
  $: displayed = showAll ? projects : featured;

  const categoryColors: Record<string, string> = {
    'fintech': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
    'ai-ml': 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
    'automation': 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    'data-engineering': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    'devops': 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300',
    'tools': 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300',
  };

  const categoryLabels: Record<string, string> = {
    'fintech': 'FinTech',
    'ai-ml': 'AI / ML',
    'automation': 'Automation',
    'data-engineering': 'Data Eng.',
    'devops': 'DevOps',
    'tools': 'Tools',
  };
</script>

<section id="projects" class="card p-6">
  <h2 class="section-heading-sm mb-4">
    <svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
    {showAll ? $t.sections.allProjects : $t.sections.featuredProjects}
  </h2>

  <div class="grid gap-5 sm:grid-cols-2">
    {#each displayed as project, i}
      <article class="p-5 flex flex-col animate-fade-in rounded-lg bg-slate-50 dark:bg-slate-700/40 border border-slate-100 dark:border-slate-700" style="animation-delay: {i * 60}ms">
        <!-- Header -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <h3 class="font-semibold text-slate-900 dark:text-white">{project.name}</h3>
          <span class="badge text-xs flex-shrink-0 {categoryColors[project.category] || ''}">
            {categoryLabels[project.category] || project.category}
          </span>
        </div>

        <!-- Description -->
        <p class="text-sm text-slate-600 dark:text-slate-300 mb-3 flex-1">
          {project.longDescription || project.description}
        </p>

        <!-- Highlights -->
        {#if project.highlights.length > 0}
          <ul class="space-y-1 mb-3">
            {#each project.highlights.slice(0, 3) as h}
              <li class="text-xs text-slate-500 dark:text-slate-400 flex items-start gap-1.5">
                <span class="text-primary-500 mt-0.5">▸</span>
                {h}
              </li>
            {/each}
          </ul>
        {/if}

        <!-- Tech tags -->
        <div class="flex flex-wrap gap-1.5 mb-4">
          {#each project.technologies as tech}
            <span class="badge-blue">{tech}</span>
          {/each}
        </div>

        <!-- Links -->
        <div class="flex gap-2 mt-auto pt-2 border-t border-slate-100 dark:border-slate-700">
          {#if project.github}
            <a href={project.github} target="_blank" rel="noopener" class="btn-ghost text-xs flex items-center gap-1.5">
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.009-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
              </svg>
              {$t.project.viewCode}
            </a>
          {/if}
          {#if project.demo}
            <a href={project.demo} target="_blank" rel="noopener" class="btn-ghost text-xs flex items-center gap-1.5">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              {$t.project.liveDemo}
            </a>
          {/if}
        </div>
      </article>
    {/each}
  </div>

  <!-- Toggle all/featured -->
  {#if projects.length > featured.length}
    <div class="mt-6 text-center">
      <button on:click={() => (showAll = !showAll)} class="btn-secondary">
        {showAll ? $t.sections.featuredProjects : $t.sections.allProjects}
        <svg class="w-4 h-4 transition-transform" class:rotate-180={showAll} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    </div>
  {/if}
</section>
