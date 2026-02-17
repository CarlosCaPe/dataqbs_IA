import { writable, derived } from 'svelte/store';
import { translations, supportedLocales, type Locale, type Translations } from './translations';

// ── Detect browser locale → supported locale ─────────
function detectLocale(): Locale {
  if (typeof navigator === 'undefined') return 'en';
  const raw = navigator.language?.slice(0, 2)?.toLowerCase() ?? 'en';
  return (supportedLocales as readonly string[]).includes(raw) ? (raw as Locale) : 'en';
}

// ── Writable locale store ────────────────────────────
export const locale = writable<Locale>(detectLocale());

// ── Persist to localStorage ──────────────────────────
if (typeof localStorage !== 'undefined') {
  const saved = localStorage.getItem('locale');
  if (saved && (supportedLocales as readonly string[]).includes(saved)) {
    locale.set(saved as Locale);
  }
  locale.subscribe((v) => localStorage.setItem('locale', v));
}

// ── Derived translations store ───────────────────────
export const t = derived<typeof locale, Translations>(locale, ($locale) => {
  return translations[$locale] ?? translations.en;
});
