# Cloudflare Production Cutover Report — Parallel Life Deep Reading v1.0.1

**Date:** 2026-08-07 (UTC) / 2026-08-08 (JST)  
**Freeze:** `PRODUCTION_MANIFEST_v1.0.1.json`  
**Final status:**

```
CLOUDFLARE PRODUCTION LIVE WITH MONITORING
```

Public custom-domain / DNS cutover was **not** performed (no intended production hostname is defined in-repo). Production is live on Cloudflare default URLs and enters the monitoring window.

---

## 1. Frozen-4 staging result

Ran against the live staging stack (`parallel-life-api-staging` + staging Session DO).

| Case | Result | Elapsed | Notes |
|------|--------|---------|-------|
| case1 | PASS | 34.69s | complete, blockers=[], idempotent draft |
| case2 | PASS | 39.79s | complete |
| case3 | PASS | 32.09s | complete; no title flake |
| case4 | PASS | 32.28s | complete |

- Session persistence Call1 → GET → confirm → Call2 → Call3: **PASS** (all four)
- Duplicate draft idempotency: **PASS** (attempts stayed at 1)
- Runtime blockers for publishable cases: **zero**
- Title validation: safe; no title-only stochastic failure this run
- Manifest pins observed in live responses match v1.0.1

Artifacts:
- `frozen4_staging/FROZEN4_SUMMARY.json`
- `frozen4_staging/run.log`

Gate decision: **production cutover allowed** (no factual/safety/storage/infra regression on staging).

---

## 2. Production bindings

| Component | Production name / URL | Binding / secret |
|-----------|----------------------|------------------|
| Pages | https://parallel-life.pages.dev/ | `VITE_API_URL` → prod API |
| Pages deploy | https://a8ac5a22.parallel-life.pages.dev | Production environment / branch `main` |
| FastAPI Container Worker | https://parallel-life-api.shiroandco-office.workers.dev | `ENV=production`, `DEEP_READING_ENABLED=true`, `SESSION_STORE_BACKEND=do`, `CORS_ALLOW_ORIGINS` |
| Session Durable Object | https://parallel-life-session-do.shiroandco-office.workers.dev | `ENVIRONMENT=production`, `SESSION_STORE_TOKEN` (secret) |
| OpenAI | Worker/Container secret | `OPENAI_API_KEY` |
| Session store | Worker/Container secrets | `SESSION_STORE_URL`, `SESSION_STORE_TOKEN` |

Runtime/model pins are code-driven from `PRODUCTION_MANIFEST_v1.0.1.json` (not overridden by Cloudflare vars).

---

## 3. Production DO separation

| Env | Worker | Storage |
|-----|--------|---------|
| Staging | `parallel-life-session-do-staging` | Staging DO namespace |
| Production | `parallel-life-session-do` | **Separate** production DO namespace |

- Production uses a **new** `SESSION_STORE_TOKEN` (not staging’s token).
- Production API `SESSION_STORE_URL` points only at the production DO Worker.
- Staging session storage was **not** reused.

---

## 4. Manifest verification

Source of truth: `kosuke-backend/app/parallel_life_deep_reading/PRODUCTION_MANIFEST_v1.0.1.json`

| Pin | Expected | Observed (staging Frozen-4 live metadata) |
|-----|----------|-------------------------------------------|
| Call 1 model | `gpt-4o-mini` | OK |
| Call 1 prompt | `parallel-life-call-1-v1.0.2` | OK |
| Call 2 model | `gpt-5.6-terra` | OK |
| Call 2 prompt | `parallel-life-call-2-v1.0.3` | OK |
| Call 3 model | `gpt-5.6-terra` | OK |
| Call 3 prompt | `parallel-life-call-3-v1.0.3` | OK |
| Runtime | `parallel-life-runtime-v1.0.5` | OK |

**MANIFEST_OK — deploy proceeded.**

No prompts / schemas / fixtures / model split / Deep Reading editorial logic were modified for this cutover.

---

## 5. Production deploy results

Deploy order executed:

1. **Session DO (production)** — deployed; healthz OK; authenticated PUT/GET session OK after env migrations.
2. **FastAPI Container / Worker** — deployed as `parallel-life-api`; secrets set; healthz OK after cold start.
3. **Pages** — project `parallel-life` created; production deploy OK at `https://parallel-life.pages.dev/`.

Infra-only Worker fixes during cutover (no editorial changes):
- Env-scoped container instance id
- Production DO / API migrations under `[env.production]`
- Kill-switch / capacity hardening: refresh container envVars; surface container errors as 503 JSON; raise production `max_instances` to 10 after capacity exhaustion

---

## 6. Pre-DNS smoke

Target: production Cloudflare URLs (before any custom DNS).

| Case | Result | Detail |
|------|--------|--------|
| A Standard happy | PASS | HTTP 200, manuscript keys present |
| B Deep Reading happy | PASS | ground→confirm→draft→edit → `complete` |
| C Case09 contradiction | PASS | status `needs_additional_input`; confirm blocked |
| D Case10 vague branch | PASS | status `structural_ambiguity` |
| E Kill switch probe | PASS | `/enabled` true at start; see §9 for toggle |
| F Session persistence | PASS | separate GET after ground; full pipeline OK |

Artifacts: `pre_dns_smoke/RESULTS.json`

---

## 7. Domain / DNS cutover

**Not performed.**

- No intended production custom domain is documented in the repository.
- Old deployments / staging URLs remain available (rollback target intact).
- Public production entrypoints for this cutover:
  - Pages: https://parallel-life.pages.dev/
  - API: https://parallel-life-api.shiroandco-office.workers.dev

Attach custom domain only after hostname is confirmed; prefer reversible route/DNS change; do not delete prior deployments.

---

## 8. Post-cutover smoke (public CF URLs)

After recovery to healthy production:

| Check | Result |
|-------|--------|
| Homepage | PASS (200) |
| SPA nested `/experience/parallel-life` | PASS (200) |
| Standard Parallel Life | PASS (200) |
| Deep Reading Call1 (ground) | PASS (`ready_for_user_confirmation`) |
| Pre-DNS full DR + Case09/10 | PASS (section 6) |
| Archive/export | Not re-run as load; export path unchanged from staging-validated API |
| Mobile-sized browser | Not run (optional); SPA HTML serves for nested routes |

---

## 9. Kill-switch verification

| Step | Result |
|------|--------|
| `DEEP_READING_ENABLED=false` redeploy | Worker var showed `"false"` |
| `/healthz` while OFF | `deep_reading_enabled: false` |
| Deep Reading `ground` while OFF | **503** maintenance message |
| Standard while OFF | **200** (preserved) |
| Restore `true` | Completed |

Operational note: flipping the kill switch by creating many new container instance ids exhausted `max_instances=3` and briefly returned Worker 1101 / “no container instance…”. Mitigated by raising production `max_instances` to **10** and pinning a stable container id (`production-api-r3`). Prefer kill-switch via var flip + single container recycle, not instance-id fan-out.

---

## 10. Session persistence

- Staging Frozen-4: persistence across Call1 → confirm → Call2 → Call3 for all four cases.
- Production pre-DNS: persistence across separate GET + confirm + draft + edit (`F_session_persistence` PASS).
- No stale-session or duplicate-draft failures observed in these runs.

---

## 11. Error rates (cutover window)

| Signal | Observation |
|--------|-------------|
| 5xx / 1101 | Transient spike during kill-switch capacity exhaustion; recovered |
| 503 container_unavailable | Seen briefly while new instances provisioned; then healthy |
| OpenAI failures | None in Frozen-4 / pre-DNS / recovery smokes |
| Schema failures | None |
| Title validation failures | None (Frozen-4) |
| DO read/write failures | None after production DO migration fix |
| Stale revision / duplicate draft | None |

No raw manuscript logging enabled.

---

## 12. Latency (observed sample)

| Path | Sample |
|------|--------|
| Staging Frozen-4 end-to-end | ~32–40s per case |
| Production Deep Reading happy (pre-DNS) | ~90s wall for full A–F script (includes Standard + DR + Case09/10) |
| Production Standard smoke (post-recovery) | seconds–tens of seconds (cold/warm dependent) |
| Container cold start | can exceed 30–60s; keep-warm `sleepAfter=30m` |

p95 not instrumented yet — track in first 2h / 48–72h monitoring.

---

## 13. Rollback readiness

Prefer first action:

```text
DEEP_READING_ENABLED=false
```

(redeploy API Worker vars; preserves Standard)

If infrastructure broken:
- Roll Cloudflare Worker/Pages to previous known-good version
- Keep staging stack as reference:  
  Pages `parallel-life-staging.pages.dev`, API `parallel-life-api-staging`, DO `parallel-life-session-do-staging`
- Do **not** delete old deployments during cutover

Rollback triggers (immediate):
- sessions disappear between calls
- confirmed sessions become stale
- duplicate drafts
- publication safety gate bypass
- substantial 5xx spike
- OpenAI secrets/config broken
- API route mismatch
- public SPA cannot reach backend

---

## 14. Remaining risks

1. **Custom domain not attached** — production traffic is on `*.pages.dev` / `*.workers.dev` until DNS is decided.
2. **Container capacity** — kill-switch / instance churn can exhaust instances; monitor live instance count (was elevated after cutover experiments).
3. **Cold start latency** — first request after idle/recycle can 503 briefly then recover.
4. **Title stochastic failure** — known historically; Frozen-4 clean this run; retry-once policy remains.
5. **v1.1 freeze** — no editorial optimization during first 72h; collect only.
6. **Cost** — terra Call2/Call3 on production; watch approximate spend at +12h/+24h/+48h/+72h.

---

## 15. Final status

Production Cloudflare stack for Deep Reading v1.0.1 is **live** on temporary/default Cloudflare URLs, with staging Frozen-4 green, manifest pins verified, DO separated, pre-DNS smoke green, kill-switch proven (Standard preserved), and rollback path documented.

Custom DNS/public hostname cutover is **pending** intentional domain attachment.

### Monitoring plan

**First 2 hours — watch:** 5xx, 503, OpenAI failures, schema failures, title validation failures, DO R/W failures, stale revision, duplicate request errors, avg/p95 latency, publication success rate, clarification/safe-stop behavior. No raw manuscript logging.

**+12h / +24h / +48h / +72h — track:** completion rate, clarification rate, safe-stop rate, validation failure rate, retry rate, title failure rate, latency, approximate cost, DO/storage errors.

**v1.1 freeze:** collect only; classify as `v1.0.2 operational bug` / `v1.1 editorial` / `UX` / `infrastructure`.

---

```
CLOUDFLARE PRODUCTION LIVE WITH MONITORING
```
