# Cloudflare Direct Deploy — Parallel Life / Deep Reading

Architecture:

1. **Pages** — `kosuke-frontend` Vite SPA (`public/_redirects` SPA fallback)
2. **Containers** — `kosuke-backend/Dockerfile` FastAPI + uvicorn (Chroma, Standard, Editorial, Deep Reading)
3. **Durable Objects** — `cloudflare/session-do` session persistence
4. **Gateway (optional)** — `cloudflare/gateway` same-origin `/experience/*` proxy

## Secrets (never commit)

| Secret / env | Where | Notes |
|---|---|---|
| `OPENAI_API_KEY` | Container | Required for Deep Reading LLM calls |
| `SESSION_STORE_TOKEN` | Container + session-do Worker | Shared bearer token |
| `SESSION_STORE_URL` | Container | `https://<session-do-staging>.workers.dev` |
| `SESSION_STORE_BACKEND` | Container | `do` in staging/prod; `memory` locally |
| `DEEP_READING_ENABLED` | Container | Kill switch (`false` → 503 + FE hides CTA) |
| `DEEP_READING_CONTEXT_PACK_ENABLED` | Container | v1.1-exp Context Pack (`true` on staging only; keep `false` in production) |
| `CORS_ALLOW_ORIGINS` | Container | Staging/prod Pages origin(s), comma-separated |
| `UPSTREAM_API_URL` | Gateway Worker | Container base URL |
| `VITE_API_URL` | Pages build | Staging API or gateway origin |

## Staging deploy (runbook)

```bash
# 1) Session DO
cd cloudflare/session-do
npm install
npx wrangler secret put SESSION_STORE_TOKEN --env staging
npm run deploy:staging
# note workers.dev URL → SESSION_STORE_URL

# 2) API Container (account must have Containers)
cd ../../kosuke-backend
docker build -t parallel-life-api:staging .
# Register/push per Cloudflare Containers docs for your account, then set env/secrets:
#   OPENAI_API_KEY, SESSION_STORE_URL, SESSION_STORE_TOKEN,
#   SESSION_STORE_BACKEND=do, CORS_ALLOW_ORIGINS=<pages origin>, ENV=staging

# 3) Optional gateway
cd ../cloudflare/gateway
npm install
# set UPSTREAM_API_URL to Container URL
npm run deploy:staging

# 4) Pages
cd ../../kosuke-frontend
# VITE_API_URL=<gateway or container URL> npm run build
# npx wrangler pages deploy dist --project-name parallel-life-staging
```

## Local defaults

- `SESSION_STORE_BACKEND=memory` (no Cloudflare required)
- `DEEP_READING_ENABLED=true`

## Production cutover

Documented in `kosuke-backend/e2e_reports/deep-reading-v1.0.1-cloudflare/CLOUDFLARE_DEPLOYMENT_REPORT.md`.
**Do not flip production DNS until staging report is reviewed.**
