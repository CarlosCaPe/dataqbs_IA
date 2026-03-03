import { writable, derived } from 'svelte/store';
import { translations, supportedLocales, type Locale, type Translations } from './translations';

const LOCALE_EVENT = 'locale-change';

// ── Detect browser locale → supported locale ─────────
function detectLocale(): Locale {
  if (typeof navigator === 'undefined') return 'en';
  const raw = navigator.language?.slice(0, 2)?.toLowerCase() ?? 'en';
  return (supportedLocales as readonly string[]).includes(raw) ? (raw as Locale) : 'en';
}

// ── Writable locale store ────────────────────────────
export const locale = writable<Locale>(detectLocale());

// ── Cross-island sync flag ───────────────────────────
let _syncing = false;

// ── Persist + sync across Astro islands ──────────────
if (typeof localStorage !== 'undefined') {
  const saved = localStorage.getItem('locale');
  if (saved && (supportedLocales as readonly string[]).includes(saved)) {
    locale.set(saved as Locale);
  }

  locale.subscribe((v) => {
    localStorage.setItem('locale', v);
    document.documentElement.lang = v;
    if (!_syncing) {
      _syncing = true;
      window.dispatchEvent(new CustomEvent(LOCALE_EVENT, { detail: v }));
      _syncing = false;
    }
  });

  // Listen for locale changes from OTHER islands
  window.addEventListener(LOCALE_EVENT, ((e: CustomEvent<string>) => {
    if (_syncing) return;
    const incoming = e.detail as Locale;
    if (!(supportedLocales as readonly string[]).includes(incoming)) return;
    _syncing = true;
    locale.set(incoming);
    _syncing = false;
  }) as EventListener);
}

// ── Derived translations store ───────────────────────
export const t = derived<typeof locale, Translations>(locale, ($locale) => {
  return translations[$locale] ?? translations.en;
});
