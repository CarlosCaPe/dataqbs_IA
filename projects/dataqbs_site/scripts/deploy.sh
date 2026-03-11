#!/usr/bin/env bash
# ── dataqbs.com Full Deploy Pipeline ──────────────────────────
# Builds knowledge, uploads to KV, builds site, deploys, purges cache.
#
# Usage:
#   ./scripts/deploy.sh              # full pipeline
#   ./scripts/deploy.sh --skip-knowledge  # skip knowledge rebuild (faster)
#
# Required env vars (in .env):
#   CF_API_TOKEN         — Cloudflare API token
#   CF_ACCOUNT_ID        — Cloudflare account ID
#   CF_ZONE_ID           — Cloudflare zone ID for dataqbs.com (for cache purge)
#   CF_CACHE_PURGE_TOKEN — API token with Zone:Cache Purge permission (optional, falls back to CF_API_TOKEN)
#
# KV namespace: 74ce589850ed4c808275116ffdb322e1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# ── Load .env ─────────────────────────────────────────
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

# ── Resolve fnm/nvm PATH ─────────────────────────────
if command -v fnm &>/dev/null; then
  eval "$(fnm env --use-on-cd 2>/dev/null)" || true
fi

# ── Config ────────────────────────────────────────────
KV_NAMESPACE_ID="74ce589850ed4c808275116ffdb322e1"
CF_ZONE_ID="${CF_ZONE_ID:-abd61a0bad72409331284b4d55bc0b12}"
CACHE_TOKEN="${CF_CACHE_PURGE_TOKEN:-${CF_API_TOKEN:-}}"
SKIP_KNOWLEDGE=false

for arg in "$@"; do
  case "$arg" in
    --skip-knowledge) SKIP_KNOWLEDGE=true ;;
  esac
done

# ── Colors ────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

step() { echo -e "\n${GREEN}▶ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
fail() { echo -e "${RED}✖ $1${NC}"; exit 1; }

# ── Preflight checks ─────────────────────────────────
command -v npx &>/dev/null || fail "npx not found. Install Node.js via fnm/nvm."
command -v python3 &>/dev/null || fail "python3 not found."
[[ -n "${CF_API_TOKEN:-}" ]] || fail "CF_API_TOKEN not set. Add it to .env"
[[ -n "${CF_ACCOUNT_ID:-}" ]] || fail "CF_ACCOUNT_ID not set. Add it to .env"

# ── Step 1: Rebuild knowledge ────────────────────────
if [[ "$SKIP_KNOWLEDGE" == "false" ]]; then
  step "1/5 Rebuilding knowledge base..."
  python3 scripts/build_knowledge.py
else
  step "1/5 Skipping knowledge rebuild (--skip-knowledge)"
fi

# ── Step 2: Upload to KV ─────────────────────────────
step "2/5 Uploading knowledge to KV..."
npx wrangler kv:key put \
  --namespace-id "$KV_NAMESPACE_ID" \
  knowledge \
  --path public/knowledge.json

# ── Step 3: Build site ───────────────────────────────
step "3/5 Building site..."
npx astro build

# ── Step 4: Deploy to Cloudflare Pages ───────────────
step "4/5 Deploying to Cloudflare Pages..."
DEPLOY_OUTPUT=$(npx wrangler pages deploy dist \
  --project-name dataqbs-site \
  --commit-dirty=true 2>&1)
echo "$DEPLOY_OUTPUT"

# Extract deployment URL
DEPLOY_URL=$(echo "$DEPLOY_OUTPUT" | grep -oP 'https://[a-z0-9]+\.dataqbs-site\.pages\.dev' || true)

# ── Step 5: Purge Cloudflare cache ───────────────────
step "5/5 Purging Cloudflare cache..."
if [[ -n "$CACHE_TOKEN" ]]; then
  PURGE_RESULT=$(curl -s -X POST \
    "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
    -H "Authorization: Bearer ${CACHE_TOKEN}" \
    -H "Content-Type: application/json" \
    --data '{"purge_everything": true}' 2>&1)

  if echo "$PURGE_RESULT" | grep -q '"success"[[:space:]]*:[[:space:]]*true'; then
    echo -e "${GREEN}✓ Cache purged successfully${NC}"
  else
    warn "Cache purge failed (token may lack Zone:Cache Purge permission)"
    warn "To fix: create a separate API token in CF dashboard with:"
    warn "  - Zone > Cache Purge > Purge"
    warn "  - Zone > Zone > Read"
    warn "  Then set CF_CACHE_PURGE_TOKEN in .env"
    echo "$PURGE_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('errors',[]),indent=2))" 2>/dev/null || true
  fi
else
  warn "No cache purge token configured. Skipping cache purge."
  warn "Add CF_CACHE_PURGE_TOKEN to .env for automatic cache clearing."
fi

# ── Done ─────────────────────────────────────────────
echo -e "\n${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Deploy complete!                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
[[ -n "${DEPLOY_URL:-}" ]] && echo -e "Preview: ${DEPLOY_URL}"
echo -e "Production: https://www.dataqbs.com"
