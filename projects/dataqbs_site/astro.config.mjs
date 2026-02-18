import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';
import tailwind from '@astrojs/tailwind';
import cloudflare from '@astrojs/cloudflare';

export default defineConfig({
  site: 'https://www.dataqbs.com',
  output: 'hybrid',
  adapter: cloudflare({
    platformProxy: { enabled: true },
  }),
  integrations: [svelte(), tailwind({ applyBaseStyles: false })],
  vite: {
    ssr: {
      external: ['node:buffer', 'node:crypto', 'cloudflare:email'],
    },
  },
});
