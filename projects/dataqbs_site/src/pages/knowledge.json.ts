/**
 * Blocks public access to knowledge.json.
 * The file no longer exists in public/ — knowledge is served from KV.
 * This route exists as a safeguard in case old CDN-cached versions are hit.
 */
import type { APIRoute } from 'astro';

export const prerender = false;

export const GET: APIRoute = () => {
  return new Response(JSON.stringify({ error: 'Not found' }), {
    status: 404,
    headers: { 'Content-Type': 'application/json' },
  });
};
