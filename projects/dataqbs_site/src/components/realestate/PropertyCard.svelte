<script lang="ts">
  import { locale } from '../../i18n/store';

  export let slug: string;
  export let image: string;
  export let title_short: string;
  export let title_short_i18n: Record<string, string> | undefined = undefined;
  export let formatted_amount: string;

  $: localizedTitle = ($locale !== 'es' && title_short_i18n?.[$locale]) || title_short;
</script>

<a
  href={`/realestate/${slug}`}
  class="group relative block rounded-2xl overflow-hidden shadow-lg hover:shadow-2xl transition-all duration-300 aspect-[4/3]"
>
  <img
    src={image}
    alt={localizedTitle}
    class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
    loading="lazy"
  />
  <!-- Gradient overlay with title -->
  <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent opacity-80 group-hover:opacity-90 transition-opacity duration-300" />
  <div class="absolute bottom-0 left-0 right-0 p-5">
    <h2 class="text-white font-bold text-lg sm:text-xl drop-shadow-lg">
      {localizedTitle}
    </h2>
    <span class="inline-block mt-2 px-3 py-1 rounded-full text-xs font-semibold bg-re-600 text-white shadow">
      {formatted_amount}
    </span>
  </div>
</a>
