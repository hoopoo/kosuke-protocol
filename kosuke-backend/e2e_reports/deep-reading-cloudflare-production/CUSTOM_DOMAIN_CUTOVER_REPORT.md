# Custom Domain Cutover Report — Parallel Life Deep Reading v1.0.1

**Date:** 2026-08-08 (JST)  
**Final status:**

```
CUSTOM DOMAIN CUTOVER BLOCKED
```

**Blocker:** Pages custom domain is attached, but DNS CNAME for `parallel-life.shiroand.io` is **not set**. Wrangler OAuth token has `zone (read)` only — DNS write returns Authentication error (10000). No local `CLOUDFLARE_API_TOKEN` with Zone.DNS Edit was available.

---

## 1. Target hostname

| Role | Hostname | Used? |
|------|----------|-------|
| Public frontend | **https://parallel-life.shiroand.io** | Attached to Pages; **DNS pending** |
| Public API | `api.parallel-life.shiroand.io` | **Not used** (kept workers.dev; no FE rebuild) |
| Session DO | (none) | Remains infrastructure-only on workers.dev |

**Routing choice:** separate origins (Pages custom domain → API `*.workers.dev`) with explicit CORS. Same-origin gateway was **not** introduced (would require architecture changes).

---

## 2. Existing DNS collision check

| Name | Pre-cutover records | Result |
|------|---------------------|--------|
| `parallel-life.shiroand.io` | none observed via dig | **No collision** |
| `api.parallel-life.shiroand.io` | none | N/A (not created) |
| Zone `shiroand.io` | active on account `53154fa721b9ebb31574651fc9f10081` | OK |

Post-attach Pages verification error:

```text
CNAME record not set
```

---

## 3. CORS configuration

Production `CORS_ALLOW_ORIGINS` (no wildcard):

```text
https://parallel-life.pages.dev,
https://a8ac5a22.parallel-life.pages.dev,
https://parallel-life.shiroand.io
```

Verified after container env refresh (`FORCE_CONTAINER_RESTART` one-shot + `destroy()` on same DO name `production-api-r3`):

```text
Access-Control-Allow-Origin: https://parallel-life.shiroand.io
```

`FORCE_CONTAINER_RESTART` left **off** after refresh. Worker still supports optional one-shot restart flag for future env refreshes (infra only; same getContainer name).

---

## 4. API routing configuration

| Item | Value |
|------|-------|
| Public API | https://parallel-life-api.shiroandco-office.workers.dev |
| API custom domain | **Not attached** |
| Container DO name | `production-api-r3` (unchanged; no name fan-out) |
| Session store | production Session DO workers.dev (secret-bound) |
| Frontend `VITE_API_URL` | unchanged → workers.dev API |

---

## 5. Frontend build / version

| Item | Result |
|------|--------|
| Rebuild required? | **No** (`VITE_API_URL` unchanged) |
| Bundle API URL | `https://parallel-life-api.shiroandco-office.workers.dev` |
| Staging API in bundle? | Not present |

---

## 6. Pages custom-domain result

| Step | Result |
|------|--------|
| Attach `parallel-life.shiroand.io` to project `parallel-life` | **SUCCESS** (API) |
| Domain id | `d884caf3-4ddf-4182-803f-83ac39842ed5` |
| Status | **pending** |
| SSL validation | pending / initializing |
| `parallel-life.pages.dev` retained | **Yes** (200) |

---

## 7. API custom-domain result

**Not used.** Prefer workers.dev API + CORS for this cutover.

---

## 8. Post-cutover smoke results

| Check | Result |
|-------|--------|
| https://parallel-life.shiroand.io homepage | **BLOCKED** — host does not resolve |
| Nested SPA | **BLOCKED** — same |
| Standard / Deep Reading / Case09 / Case10 / export | **Not run** on custom host |
| Rollback Pages `parallel-life.pages.dev` | **200** |
| API healthz | **200** `deep_reading_enabled=true` `env=production` |
| CORS for new origin (direct API) | **PASS** |

---

## 9. Container capacity before / after

| Metric | Before cutover window | After domain attach attempt |
|--------|----------------------|----------------------------|
| LIVE / max | 7 / 10 | 7 / 10 |
| failed | 0 | 0 |
| health.errors | [] | [] |
| Serving DO | production-api-r3 | production-api-r3 (may be stopped/warm; starts on traffic) |
| New getContainer names | none | none |

---

## 10. 1101 / 5xx status

| Signal | During cutover ops |
|--------|-------------------|
| 1101 | Not observed on successful health probes |
| 5xx | Transient during forced container destroy/reconnect; recovered to 200 |
| Sustained 5xx | No |

---

## 11. Rollback readiness

Available immediately:

- https://parallel-life.pages.dev/
- https://parallel-life-api.shiroandco-office.workers.dev
- Staging stack unchanged
- Kill switch: `DEEP_READING_ENABLED=false`
- Pages domain can be removed if needed (domain currently pending only)

---

## 12. Final public URL

| URL | State |
|-----|-------|
| **https://parallel-life.shiroand.io** | **NOT LIVE** (DNS CNAME missing) |
| https://parallel-life.pages.dev | LIVE (rollback / current public FE) |
| https://parallel-life-api.shiroandco-office.workers.dev | LIVE |

---

## 13. Final status

```
CUSTOM DOMAIN CUTOVER BLOCKED
```

### Required manual DNS step (zone editor / token with Zone.DNS Edit)

In Cloudflare Dashboard → zone **shiroand.io** → DNS → Add record:

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| **CNAME** | `parallel-life` | `parallel-life.pages.dev` | **Proxied** (orange cloud) |

Do not delete existing unrelated records. Do not remove `parallel-life.pages.dev`.

After CNAME is set, expect Pages domain status → active, then run post-cutover smoke from https://parallel-life.shiroand.io.

### What is already done (safe to leave)

1. Pre-verify: health / DO / r3 / secrets / manifest v1.0.1 / runtime v1.0.5 — OK  
2. CORS includes `https://parallel-life.shiroand.io` — OK  
3. Pages project domain attachment — OK (pending DNS)  
4. No API hostname / no Session DO public hostname  
5. No app-logic / prompt / runtime / schema changes  

### Resume after DNS

1. Confirm `dig parallel-life.shiroand.io` resolves (proxied)  
2. Confirm Pages domain status `active`  
3. Run smoke: home, SPA nested, Standard, DR Call1→confirm→complete, Case09, Case10, export, refresh  
4. Re-check capacity / 1101 / 5xx  
5. Update this report to `CUSTOM DOMAIN LIVE — V1.0.1` or `… WITH MONITORING`
