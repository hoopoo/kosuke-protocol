# Custom Domain Cutover Procedure (DO NOT RUN AUTOMATICALLY)

Prepared: 2026-08-08 (JST)  
Current public origins (keep as rollback targets):

| Service | Current URL |
|---------|-------------|
| Pages | https://parallel-life.pages.dev/ |
| API | https://parallel-life-api.shiroandco-office.workers.dev |
| Session DO | https://parallel-life-session-do.shiroandco-office.workers.dev |

**Do not execute this procedure until a hostname is confirmed and recommendation is CUTOVER READY.**

Placeholder hostnames (replace before execution):

- `PAGES_HOST` — e.g. `parallel-life.example.com` (frontend)
- `API_HOST` — e.g. `api.parallel-life.example.com` (optional; or keep workers.dev API)

Recommended topology (reversible):

```
Browser → https://PAGES_HOST (Cloudflare Pages custom domain)
       → https://API_HOST   (Worker custom domain / route)
       → Session DO remains on workers.dev (not browser-facing)
```

---

## Preconditions (checklist)

- [ ] Production healthz 200, `deep_reading_enabled: true`
- [ ] No active 5xx/1101 spike in last monitoring window
- [ ] Container live instances well below `max_instances` (prod=10)
- [ ] Staging Frozen-4 still green / no new regressions
- [ ] Intended `PAGES_HOST` / `API_HOST` confirmed with DNS access
- [ ] Rollback contacts ready; kill-switch path known

---

## Step A — Prepare CORS (API)

Update production `CORS_ALLOW_ORIGINS` to include the new Pages origin **before** browsers hit it:

```toml
# cloudflare/api-container/wrangler.toml [env.production]
# Append, do not remove pages.dev yet:
CORS_ALLOW_ORIGINS = "https://parallel-life.pages.dev,https://PAGES_HOST"
```

```bash
cd cloudflare/api-container
npx wrangler deploy --env production
# Verify:
curl -sS -A 'Mozilla/5.0' https://parallel-life-api.shiroandco-office.workers.dev/healthz
```

Do **not** remove `https://parallel-life.pages.dev` until post-cutover smoke passes.

---

## Step B — (If using custom API host) Attach API Worker route

Option 1 — Worker Custom Domain (preferred if zone is on Cloudflare):

```bash
cd cloudflare/api-container
# Via Dashboard: Workers → parallel-life-api → Settings → Domains & Routes
#   Add Custom Domain: API_HOST
# Or wrangler routes in wrangler.toml [env.production] once hostname is known, then:
npx wrangler deploy --env production
```

Option 2 — keep API on `*.workers.dev` and only attach Pages custom domain (simplest).  
Then rebuild frontend with existing API URL (no FE rebuild required if already pointing at workers.dev).

Verify API on new host (if attached):

```bash
curl -sS -A 'Mozilla/5.0' https://API_HOST/healthz
# Expect: {"status":"ok","deep_reading_enabled":true,"env":"production"}
```

Session DO stays internal; do **not** put DO on a public marketing domain.

---

## Step C — Frontend API base URL

If API host changes, rebuild Pages with the new origin (no app-logic changes):

```bash
cd kosuke-frontend
export VITE_API_URL='https://API_HOST'   # or keep workers.dev URL
npm ci
npm run build
npx wrangler pages deploy dist --project-name parallel-life --branch main --commit-dirty=true
```

If API remains on workers.dev, skip rebuild.

---

## Step D — Attach Pages custom domain (reversible)

Dashboard (recommended):

1. Cloudflare Dashboard → Workers & Pages → `parallel-life`
2. Custom domains → Set up a custom domain → `PAGES_HOST`
3. If zone is on same account: Cloudflare adds the CNAME/route automatically
4. If external DNS: add the CNAME Cloudflare shows; keep TTL low (≤300s)

CLI alternative (when hostname known):

```bash
npx wrangler pages domain add PAGES_HOST --project-name parallel-life
```

**Do not delete** the `parallel-life.pages.dev` deployment.

---

## Step E — Immediate post-cutover smoke (public host)

From `https://PAGES_HOST`:

1. Homepage loads
2. Nested SPA route `/experience/parallel-life` (hard refresh)
3. Standard Parallel Life once
4. Deep Reading Call1 → confirmation
5. One complete Deep Reading (Call2+Call3) if time allows
6. Case09 still safe-stops
7. Archive/export once
8. Mobile viewport sanity

API checks:

```bash
curl -sS -A 'Mozilla/5.0' https://API_HOST/healthz
curl -sS -A 'Mozilla/5.0' https://API_HOST/experience/parallel-life/deep-reading/enabled
```

---

## Step F — Rollback (prefer reversible)

**First action if Deep Reading broken but infra OK:**

```bash
# Set DEEP_READING_ENABLED=false in [env.production] vars, redeploy API
cd cloudflare/api-container
# edit wrangler.toml DEEP_READING_ENABLED = "false"
npx wrangler deploy --env production
```

**If domain/route broken:**

1. Remove or disable `PAGES_HOST` custom domain (Pages stays on `*.pages.dev`)
2. Remove Worker custom domain/route for `API_HOST` if added
3. Point users/bookmarks back to https://parallel-life.pages.dev/
4. Keep prior Worker versions; do not delete deployments

DNS rollback: restore previous CNAME/A records (low TTL makes this fast).

---

## Explicit non-actions

- Do not change prompts, schemas, runtime gates, fixtures, or model pins
- Do not reuse staging Session DO / staging token
- Do not delete staging or previous production deployments during cutover
- Do not run load tests during cutover
