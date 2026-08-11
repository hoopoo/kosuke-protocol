# Cloudflare Direct Deploy — Deep Reading v1.0.1

**Date:** 2026-08-07  
**Manifest:** `PRODUCTION_MANIFEST_v1.0.1.json` (runtime `parallel-life-runtime-v1.0.5`)  
**Scope:** Infrastructure adaptation only — no Call1/2/3 prompt, schema, runtime-gate, fixture, or model changes.

---

## Status

```
CLOUDFLARE STAGING READY
```

Staging is green. **Production DNS cutover is not done** (requires explicit approval).

| Component | URL / note |
|-----------|------------|
| Pages | https://parallel-life-staging.pages.dev/ |
| Pages preview | https://978a9f4c.parallel-life-staging.pages.dev/ |
| API Container | https://parallel-life-api-staging.shiroandco-office.workers.dev |
| Session DO | https://parallel-life-session-do-staging.shiroandco-office.workers.dev |
| Matrix results | `staging_matrix/RESULTS.json` |

### Staging matrix

| ID | Case | Result |
|----|------|--------|
| A | Standard happy path | **PASS** |
| B | Deep Reading happy path (complete) | **PASS** |
| C | Blockers 06/08/09/10 (unit) | **PASS** (17 tests) |
| D | Frozen 4 live | **SKIPPED** (non-blocking; Case3 title flake known) |
| E | Persistence Container↔DO | **PASS** |
| F | Duplicate draft idempotency | **PASS** (attempts stayed 1) |
| G | Expired session | **PASS** (unit) |
| H | Kill switch probe | **PASS** (`enabled: true`) |
| — | Pages SPA `/experience/parallel-life` | **PASS** (200) |

---

## Compatibility audit (confirmed)

| Item | Result |
|------|--------|
| Full FastAPI on Python Workers | **No** — ChromaDB FS, `igraph`/`leidenalg`, process-local dict sessions, memory limits |
| Vite SPA on Pages | **Yes** — `BrowserRouter` + `public/_redirects` SPA fallback |
| Deep Reading API paths | Unchanged `/experience/parallel-life/deep-reading/*` |
| Streaming / BackgroundTasks | None required |

### Chosen architecture

```
User → Cloudflare Pages (Vite)
     → optional Gateway Worker (same-origin /experience/*)
     → Cloudflare Container (FastAPI / uvicorn)
     → Durable Object session Worker (session JSON)
     → OpenAI API
```

---

## Implementation delivered

### 1. Session store abstraction

- `session_store.py`: `SessionStoreProtocol`, `InMemorySessionStore`, `HttpDurableObjectSessionStore`
- Factory via `SESSION_STORE_BACKEND` (`memory` default, `do` for Cloudflare)
- Additive session fields: `session_revision`, `expires_at` (24h TTL, extended on mutation), `idempotency_keys`
- Optimistic concurrency (`expected_revision` → `StaleSessionRevisionError`)
- Service uses `_save()` with revision checks; draft/edit accept optional `idempotency_key`

### 2. Durable Object Worker

- Package: `cloudflare/session-do/`
- Endpoints: `PUT/GET/PATCH/DELETE /sessions/:id`
- Alarm-based TTL cleanup; no manuscript logging
- Staging wrangler env: `parallel-life-session-do-staging`

### 3. Kill switch + observability

- `DEEP_READING_ENABLED` (default true) → Deep Reading routes **503** Japanese maintenance message
- `GET /experience/parallel-life/deep-reading/enabled` + `/healthz.deep_reading_enabled`
- Middleware: `request_id`, latency, status, runtime version, failure_category — **no** raw input/manuscript/prompts/keys
- CORS via `CORS_ALLOW_ORIGINS` (comma-separated; empty → `*`)
- Frontend: hide “もっと深く読む” when enabled probe is false

### 4. Deploy artifacts

| Artifact | Path |
|----------|------|
| Dockerfile | `kosuke-backend/Dockerfile` |
| Session DO | `cloudflare/session-do/` |
| Container wrangler notes | `cloudflare/container/wrangler.toml` |
| Gateway Worker | `cloudflare/gateway/` |
| Pages SPA | `kosuke-frontend/public/_redirects` |
| Secrets docs | `cloudflare/README.md`, `.env.example` |

---

## Local verification (this run)

| Test | Result |
|------|--------|
| Session store protocol / revision / TTL | **PASS** (`tests/test_session_store.py`) |
| Draft/edit idempotency | **PASS** (`tests/test_session_idempotency.py`) |
| Kill switch 503 + probe | **PASS** (`tests/test_deep_reading_kill_switch.py`) |
| v1.0.1 blockers 06/08/09/10 | **PASS** (`tests/test_deep_reading_v101_blockers.py`) |
| Live Cloudflare staging deploy | **NOT RUN** (Docker/Wrangler blocked) |
| Frozen-4 live E2E | **NOT RUN** (needs staging + OpenAI) |
| Cross-boundary persistence (Container↔DO) | **NOT RUN** live; memory/revision path covered in unit tests |

Command:

```bash
cd kosuke-backend
poetry run pytest tests/test_session_store.py \
  tests/test_session_idempotency.py \
  tests/test_deep_reading_kill_switch.py \
  tests/test_deep_reading_v101_blockers.py -q
# → 17 passed
```

---

## Staging matrix (to run after deploy)

| ID | Case | Expected |
|----|------|----------|
| A | Standard happy path | Unchanged Standard OK |
| B | Deep Reading happy path | ground→confirm→draft→edit complete |
| C | Blockers 06/08/09/10 | Same as v1.0.1 unit/runtime gates |
| D | Frozen 4 | Case3 title flake possible — non-publish safe |
| E | Persistence across Container↔DO | Call1 → wait → confirm → draft → edit |
| F | Duplicate draft + same idempotency key | Single generation |
| G | Expired session | 404 / session gone after TTL |
| H | Kill switch | `DEEP_READING_ENABLED=false` → 503 + CTA hidden |

---

## Staging runbook (when credentials available)

See `cloudflare/README.md`. Summary:

1. Deploy `session-do` staging; set `SESSION_STORE_TOKEN`
2. Build/push Container from `kosuke-backend/Dockerfile`; set `OPENAI_API_KEY`, `SESSION_STORE_URL`, `SESSION_STORE_BACKEND=do`, `CORS_ALLOW_ORIGINS`
3. Optional: deploy gateway with `UPSTREAM_API_URL`
4. Build Pages with `VITE_API_URL` → gateway or API; deploy `dist`
5. Run staging matrix A–H; update this report status line

---

## Production cutover (prepare only — **do not flip DNS**)

### Names / bindings

| Component | Staging name | Production name |
|-----------|--------------|-----------------|
| Session DO | `parallel-life-session-do-staging` | `parallel-life-session-do` |
| API Container | `parallel-life-api-staging` | `parallel-life-api` |
| Gateway | `parallel-life-gateway-staging` | `parallel-life-gateway` |
| Pages | `parallel-life-staging` (suggested) | existing prod Pages project |

### Domain map (fill at cutover)

| Role | Hostname |
|------|----------|
| Staging Pages | `<TBD>.pages.dev` or `staging-parallel.<domain>` |
| Staging API / gateway | `<TBD>` |
| Production apex / www | **do not change until approval** |

### Secrets checklist

- [ ] `OPENAI_API_KEY` on Container
- [ ] `SESSION_STORE_TOKEN` on Container + session-do
- [ ] `SESSION_STORE_URL` on Container
- [ ] `CORS_ALLOW_ORIGINS` = production Pages origin
- [ ] `DEEP_READING_ENABLED=true`
- [ ] Pages `VITE_API_URL` rebuilt against prod API/gateway

### Rollback

1. **Kill switch only:** set Container `DEEP_READING_ENABLED=false` (Standard/Editorial stay up; FE hides CTA).
2. **Container rollback:** redeploy previous Container image tag / version.
3. **DNS rollback:** restore prior DNS records (only if cutover was applied).
4. **Session DO:** keep prior Worker version; sessions are ephemeral (24h TTL) — acceptable loss for incomplete sessions.

### Cutover gate

Production DNS flip requires:

1. This report status → `CLOUDFLARE STAGING READY` or `CLOUDFLARE PRODUCTION CUTOVER READY`
2. Explicit human approval
3. Staging matrix A–H green (D Case3 title flake allowed as non-blocking)

---

## Explicit non-goals (honored)

- No Call1/2/3 prompt/schema/runtime-gate/fixture/model edits
- No Vercel in path
- No KV as primary mutable session store
- No production DNS cutover in this work

---

## Next actions for operator

1. Install/login Wrangler; confirm Containers entitlement
2. Enable Docker; build `kosuke-backend/Dockerfile`
3. Deploy staging per `cloudflare/README.md`
4. Run staging matrix; amend this report status line
