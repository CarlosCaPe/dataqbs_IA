<script lang="ts">
  import { t } from '../i18n/store';
</script>

<section class="card p-6 space-y-4">
  <h2 class="section-heading-sm">{$t.profile.about}</h2>
  <p class="text-sm text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">
    {$t.profile.summary}
  </p>
  <blockquote class="border-l-4 border-primary-500 pl-4 py-1">
    <p class="text-slate-500 dark:text-slate-400 text-sm italic leading-relaxed">
      "{$t.profile.vision}"
    </p>
  </blockquote>
</section>
