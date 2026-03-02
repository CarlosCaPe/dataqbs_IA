<script lang="ts">
  import { t, locale } from '../../i18n/store';
  import PropertyGallery from './PropertyGallery.svelte';

  export let property: Record<string, any>;
  export let basePath: string = '';

  // Language note for non-Spanish users
  $: showLangNote = $locale !== 'es';
  const langNotes: Record<string, string> = {
    en: 'This listing is in Spanish. Contact us for assistance in English.',
    de: 'Diese Anzeige ist auf Spanisch. Kontaktieren Sie uns für Hilfe auf Deutsch.',
  };

  // Group features by category
  $: featureGroups = (property.features || []).reduce(
    (acc: Record<string, string[]>, f: { name: string; category: string }) => {
      const cat = f.category || 'General';
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(f.name);
      return acc;
    },
    {} as Record<string, string[]>
  );

  $: operation = property.operations?.[0];
  $: priceFormatted = operation?.formatted_amount || '';
  $: pricePerM2 = operation?.price_per_m2
    ? `$${Math.round(operation.price_per_m2).toLocaleString('es-MX')} MXN/m²`
    : null;

  // Map feature categories to i18n keys
  function getCategoryLabel(cat: string): string {
    const map: Record<string, string> = {
      Exterior: $t.rs.exterior,
      Interior: $t.rs.interior,
      Equipamiento: $t.rs.equipment,
      Seguridad: $t.rs.security,
      Estatus: $t.rs.status,
    };
    return map[cat] || cat;
  }

  // Category icons
  function getCategoryIcon(cat: string): string {
    const map: Record<string, string> = {
      Exterior: '🏡',
      Interior: '🛋️',
      Equipamiento: '⚡',
      Seguridad: '🔒',
      Estatus: '✅',
    };
    return map[cat] || '📋';
  }

  // Parse description into readable sections (strip emojis for cleanliness)
  $: descriptionFormatted = property.description || '';
</script>

<div class="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">

  <!-- ── Header: Title + Price ──────────────────────── -->
  <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
    <div class="space-y-2">
      <div class="flex items-center gap-2">
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rs-100 text-rs-800 dark:bg-rs-900/30 dark:text-rs-300">
          {$t.rs.sale}
        </span>
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300">
          {property.property_type}
          {#if property.property_subtype}
            — {property.property_subtype}
          {/if}
        </span>
      </div>
      <h1 class="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white leading-tight">
        {property.title}
      </h1>
      <p class="text-slate-500 dark:text-slate-400 text-sm flex items-center gap-1">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        {property.location?.name || ''}
      </p>
    </div>
    <div class="flex flex-col items-end gap-1 flex-shrink-0">
      <span class="text-3xl sm:text-4xl font-bold text-rs-600 dark:text-rs-400">
        {priceFormatted}
      </span>
      {#if pricePerM2}
        <span class="text-sm text-slate-500 dark:text-slate-400">
          {pricePerM2}
        </span>
      {/if}
    </div>
  </div>

  <!-- Language Note for non-Spanish users -->
  {#if showLangNote}
    <div class="flex items-center gap-2 px-4 py-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/30 text-sm text-amber-800 dark:text-amber-200">
      <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{langNotes[$locale] || langNotes.en}</span>
    </div>
  {/if}

  <!-- ── Gallery ────────────────────────────────────── -->
  <PropertyGallery images={property.property_images || []} {basePath} />

  <!-- ── Quick Specs ────────────────────────────────── -->
  <div class="card p-6">
    <h2 class="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
      📐 {$t.rs.overview}
    </h2>
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
      {#if property.bedrooms != null}
        <div class="flex flex-col items-center p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50">
          <span class="text-2xl">🛏️</span>
          <span class="text-2xl font-bold text-slate-900 dark:text-white">{property.bedrooms}</span>
          <span class="text-xs text-slate-500 dark:text-slate-400">{$t.rs.bedrooms}</span>
        </div>
      {/if}
      {#if property.bathrooms != null}
        <div class="flex flex-col items-center p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50">
          <span class="text-2xl">🚿</span>
          <span class="text-2xl font-bold text-slate-900 dark:text-white">
            {property.bathrooms}{#if property.half_bathrooms}.5{/if}
          </span>
          <span class="text-xs text-slate-500 dark:text-slate-400">{$t.rs.bathrooms}</span>
        </div>
      {/if}
      {#if property.parking_spaces != null}
        <div class="flex flex-col items-center p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50">
          <span class="text-2xl">🚗</span>
          <span class="text-2xl font-bold text-slate-900 dark:text-white">{property.parking_spaces}</span>
          <span class="text-xs text-slate-500 dark:text-slate-400">{$t.rs.parking}</span>
        </div>
      {/if}
      {#if property.lot_size != null}
        <div class="flex flex-col items-center p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50">
          <span class="text-2xl">📏</span>
          <span class="text-2xl font-bold text-slate-900 dark:text-white">{property.lot_size}</span>
          <span class="text-xs text-slate-500 dark:text-slate-400">{$t.rs.lotSize} ({property.lot_size_unit})</span>
        </div>
      {/if}
      {#if property.construction_size != null}
        <div class="flex flex-col items-center p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50">
          <span class="text-2xl">🏗️</span>
          <span class="text-2xl font-bold text-slate-900 dark:text-white">{property.construction_size}</span>
          <span class="text-xs text-slate-500 dark:text-slate-400">{$t.rs.construction} ({property.construction_size_unit})</span>
        </div>
      {/if}
      {#if property.floors != null}
        <div class="flex flex-col items-center p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50">
          <span class="text-2xl">🏢</span>
          <span class="text-2xl font-bold text-slate-900 dark:text-white">{property.floors}</span>
          <span class="text-xs text-slate-500 dark:text-slate-400">{$t.rs.floors}</span>
        </div>
      {/if}
      {#if property.year_built != null}
        <div class="flex flex-col items-center p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50">
          <span class="text-2xl">📅</span>
          <span class="text-2xl font-bold text-slate-900 dark:text-white">{property.year_built}</span>
          <span class="text-xs text-slate-500 dark:text-slate-400">{$t.rs.yearBuilt}</span>
        </div>
      {/if}
      {#if property.age != null}
        <div class="flex flex-col items-center p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50">
          <span class="text-2xl">⏳</span>
          <span class="text-2xl font-bold text-slate-900 dark:text-white">{property.age}</span>
          <span class="text-xs text-slate-500 dark:text-slate-400">{$t.rs.age} ({$t.rs.years})</span>
        </div>
      {/if}
      {#if property.floor != null}
        <div class="flex flex-col items-center p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50">
          <span class="text-2xl">🔢</span>
          <span class="text-2xl font-bold text-slate-900 dark:text-white">{property.floor}</span>
          <span class="text-xs text-slate-500 dark:text-slate-400">{$t.rs.floor}</span>
        </div>
      {/if}
    </div>
  </div>

  <!-- ── Description ────────────────────────────────── -->
  <div class="card p-6">
    <h2 class="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
      📝 {$t.rs.description}
    </h2>
    <div class="prose prose-slate dark:prose-invert max-w-none text-sm leading-relaxed">
      {#each descriptionFormatted.split('\n') as line}
        {#if line.trim() === ''}
          <br />
        {:else if line.startsWith('•')}
          <p class="ml-4 mb-1 text-slate-600 dark:text-slate-300">{line}</p>
        {:else if line.match(/^[🏡🛏️⚡🔒📍✅📐💰📈🏠🔝🚗🏢]/u)}
          <p class="font-semibold text-slate-800 dark:text-slate-200 mt-3 mb-1">{line}</p>
        {:else}
          <p class="text-slate-600 dark:text-slate-300 mb-1">{line}</p>
        {/if}
      {/each}
    </div>
  </div>

  <!-- ── Features ───────────────────────────────────── -->
  {#if Object.keys(featureGroups).length > 0}
    <div class="card p-6">
      <h2 class="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
        ✨ {$t.rs.features}
      </h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {#each Object.entries(featureGroups) as [category, features]}
          <div>
            <h3 class="text-sm font-semibold text-rs-600 dark:text-rs-400 uppercase tracking-wider mb-2 flex items-center gap-1">
              {getCategoryIcon(category)} {getCategoryLabel(category)}
            </h3>
            <ul class="space-y-1.5">
              {#each features as feature}
                <li class="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <svg class="w-4 h-4 text-rs-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                  </svg>
                  {feature}
                </li>
              {/each}
            </ul>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- ── Location ───────────────────────────────────── -->
  {#if property.location}
    <div class="card p-6">
      <h2 class="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
        📍 {$t.rs.location}
      </h2>
      <div class="space-y-3">
        <div class="flex flex-wrap gap-2 text-sm">
          {#if property.location.neighborhood}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
              📌 {property.location.neighborhood}
            </span>
          {/if}
          {#if property.location.municipality}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
              🏙️ {property.location.municipality}
            </span>
          {/if}
          {#if property.location.state}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
              🗺️ {property.location.state}
            </span>
          {/if}
          {#if property.location.postal_code}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
              ✉️ CP {property.location.postal_code}
            </span>
          {/if}
        </div>

        <!-- Nearby Places -->
        {#if property.nearby_places?.length > 0}
          <div class="mt-4">
            <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
              {$t.rs.nearby}
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {#each property.nearby_places as place}
                <div class="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-700/50 text-sm">
                  <span class="text-slate-700 dark:text-slate-300">{place.name}</span>
                  <span class="text-slate-400 dark:text-slate-500 text-xs ml-2 flex-shrink-0">
                    {place.distance_km} km
                  </span>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- ── Tags ───────────────────────────────────────── -->
  {#if property.tags?.length > 0}
    <div class="card p-6">
      <h2 class="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
        🏷️ {$t.rs.tags}
      </h2>
      <div class="flex flex-wrap gap-2">
        {#each property.tags as tag}
          <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-rs-100 text-rs-700 dark:bg-rs-900/30 dark:text-rs-300">
            {tag}
          </span>
        {/each}
      </div>
    </div>
  {/if}

  <!-- ── CTA ────────────────────────────────────────── -->
  <div class="card p-6 bg-gradient-to-r from-rs-600 to-rs-700 dark:from-rs-700 dark:to-rs-800 border-rs-500">
    <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
      <div>
        <h2 class="text-xl font-bold text-white">
          {$t.rs.requestInfo}
        </h2>
        <p class="text-rs-100 text-sm mt-1">
          {property.title_short || property.title}
        </p>
      </div>
      <a
        href="mailto:carlos.carrillo@dataqbs.com?subject={encodeURIComponent($t.rs.requestInfo + ': ' + (property.title_short || property.title))}"
        rel="noopener noreferrer"
        class="inline-flex items-center gap-2 px-6 py-3 rounded-lg font-semibold text-sm bg-white text-rs-700 hover:bg-rs-50 active:bg-rs-100 transition-all duration-150 shadow-lg hover:shadow-xl"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        {$t.rs.contactUs}
      </a>
    </div>
  </div>

  <!-- ── Footer ─────────────────────────────────────── -->
  <footer class="border-t border-slate-200 dark:border-slate-700 pt-8 pb-4">
    <div class="text-center space-y-2">
      <div class="flex items-center justify-center gap-2">
        <img src="/rs-favicon.svg" alt="realstate" class="w-6 h-6" />
        <span class="font-bold text-rs-600 dark:text-rs-400">realstate</span>
      </div>
      <p class="text-sm text-slate-500 dark:text-slate-400">
        © {new Date().getFullYear()} realstate
      </p>
    </div>
  </footer>
</div>
