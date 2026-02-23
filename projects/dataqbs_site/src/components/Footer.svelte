<script lang="ts">
  import { t } from '../i18n/store';
</script>

<footer class="border-t border-slate-200 dark:border-slate-700 mt-12 py-8">
  <div class="max-w-4xl mx-auto px-4 sm:px-6 text-center space-y-2">
    <p class="text-sm text-slate-500 dark:text-slate-400">
      {$t.footer.rights}
    </p>
    <p class="text-xs text-slate-400 dark:text-slate-500">
      {$t.footer.builtWith}
    </p>
  </div>
</footer>
