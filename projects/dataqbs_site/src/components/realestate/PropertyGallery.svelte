<script lang="ts">
  import { t } from '../../i18n/store';

  export let images: Array<{
    title: string;
    url: string;
    position: number;
    category: string;
  }> = [];

  export let basePath: string = '';

  let currentIndex = 0;
  let showLightbox = false;
  let touchStartX = 0;
  let touchEndX = 0;

  $: sortedImages = [...images].sort((a, b) => a.position - b.position);
  $: total = sortedImages.length;
  $: currentImage = sortedImages[currentIndex];

  function next() {
    currentIndex = (currentIndex + 1) % total;
  }

  function prev() {
    currentIndex = (currentIndex - 1 + total) % total;
  }

  function goTo(index: number) {
    currentIndex = index;
  }

  function openLightbox(index: number) {
    currentIndex = index;
    showLightbox = true;
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    showLightbox = false;
    document.body.style.overflow = '';
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!showLightbox) return;
    if (e.key === 'ArrowRight') next();
    if (e.key === 'ArrowLeft') prev();
    if (e.key === 'Escape') closeLightbox();
  }

  function handleTouchStart(e: TouchEvent) {
    touchStartX = e.changedTouches[0].screenX;
  }

  function handleTouchEnd(e: TouchEvent) {
    touchEndX = e.changedTouches[0].screenX;
    const diff = touchStartX - touchEndX;
    if (Math.abs(diff) > 50) {
      if (diff > 0) next();
      else prev();
    }
  }

  function getImageUrl(img: { url: string }) {
    const filename = img.url.replace('inputImages/', '');
    // Security: sanitize filename to prevent path traversal
    const sanitized = filename
      .replace(/\.\./g, '')            // strip ..
      .replace(/%2e%2e/gi, '')         // strip URL-encoded ..
      .replace(/[<>"'\\]/g, '')        // strip dangerous chars + backslash
      .replace(/\0/g, '')             // strip null bytes
      .replace(/\/\//g, '/')          // collapse double slashes
      .replace(/[?#].*/g, '');        // strip query strings and fragments
    // Validate basePath starts with expected prefix
    const safeBase = basePath.startsWith('/realestate/') ? basePath : '/realestate';
    return `${safeBase}/${sanitized}`;
  }

  function photoOfLabel(n: number, tot: number): string {
    return $t.re.photoOf.replace('{n}', String(n)).replace('{total}', String(tot));
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<!-- Main Gallery Grid -->
<div class="space-y-4">
  <!-- Hero Image -->
  {#if sortedImages.length > 0}
    <div class="relative group cursor-pointer rounded-xl overflow-hidden"
         on:click={() => openLightbox(0)}
         on:keydown={(e) => e.key === 'Enter' && openLightbox(0)}
         role="button" tabindex="0">
      <img
        src={getImageUrl(sortedImages[0])}
        alt={sortedImages[0].title}
        class="w-full h-64 sm:h-80 md:h-96 object-cover transition-transform duration-300 group-hover:scale-105 pointer-events-none select-none"
        loading="eager"
        draggable="false"
        on:contextmenu|preventDefault
      />
      <div class="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      <div class="absolute bottom-4 left-4 right-4 flex justify-end items-end opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <span class="text-white/80 text-xs bg-black/50 px-2 py-1 rounded-full">
          {photoOfLabel(1, total)}
        </span>
      </div>
    </div>
  {/if}

  <!-- Thumbnail Grid -->
  {#if sortedImages.length > 1}
    <div class="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 gap-2">
      {#each sortedImages.slice(1, 13) as img, i}
        <button
          on:click={() => openLightbox(i + 1)}
          class="relative group rounded-lg overflow-hidden aspect-square focus:outline-none focus:ring-2 focus:ring-re-500"
        >
          <img
            src={getImageUrl(img)}
            alt={img.title}
            class="w-full h-full object-cover transition-transform duration-200 group-hover:scale-110 pointer-events-none select-none"
            loading="lazy"
            draggable="false"
          />
          <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-200" />
        </button>
      {/each}
      {#if sortedImages.length > 13}
        <button
          on:click={() => openLightbox(13)}
          class="relative group rounded-lg overflow-hidden aspect-square bg-slate-800 flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-re-500"
        >
          <span class="text-white font-semibold text-sm">+{sortedImages.length - 13}</span>
        </button>
      {/if}
    </div>
  {/if}
</div>

<!-- Lightbox -->
{#if showLightbox}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="fixed inset-0 z-50 bg-black/95 flex flex-col items-center justify-center"
       role="dialog" aria-modal="true" aria-label="Image gallery"
       on:touchstart={handleTouchStart}
       on:touchend={handleTouchEnd}>

    <!-- Close button -->
    <button
      on:click={closeLightbox}
      class="absolute top-4 right-4 z-60 text-white/80 hover:text-white p-2 rounded-full hover:bg-white/10 transition-colors"
      aria-label="Close"
    >
      <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>

    <!-- Counter -->
    <div class="absolute top-4 left-4 text-white/70 text-sm font-medium">
      {photoOfLabel(currentIndex + 1, total)}
    </div>

    <!-- Main image -->
    <div class="flex-1 flex items-center justify-center w-full px-14 py-16">
      {#if currentImage}
        <img
          src={getImageUrl(currentImage)}
          alt={currentImage.title}
          class="max-h-full max-w-full object-contain rounded-lg shadow-2xl animate-fade-in pointer-events-none select-none"
          draggable="false"
          on:contextmenu|preventDefault
        />
      {/if}
    </div>

    <!-- Caption hidden by design -->

    <!-- Prev button -->
    <button
      on:click|stopPropagation={prev}
      class="absolute left-3 top-1/2 -translate-y-1/2 text-white/70 hover:text-white p-2 rounded-full hover:bg-white/10 transition-colors"
      aria-label="Previous"
    >
      <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
    </button>

    <!-- Next button -->
    <button
      on:click|stopPropagation={next}
      class="absolute right-3 top-1/2 -translate-y-1/2 text-white/70 hover:text-white p-2 rounded-full hover:bg-white/10 transition-colors"
      aria-label="Next"
    >
      <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
      </svg>
    </button>

    <!-- Dots -->
    <div class="absolute bottom-4 flex gap-1.5 overflow-x-auto max-w-[80vw] px-4 py-2">
      {#each sortedImages as _, i}
        <button
          on:click|stopPropagation={() => goTo(i)}
          class="w-2 h-2 rounded-full transition-all duration-200 flex-shrink-0
            {i === currentIndex ? 'bg-re-500 scale-125' : 'bg-white/40 hover:bg-white/70'}"
          aria-label="Go to photo {i + 1}"
        />
      {/each}
    </div>
  </div>
{/if}
