# Container Capacity Audit — Parallel Life Production

**Date:** 2026-08-08 (JST)  
**Scope:** Read-only investigation. No cleanup, capacity changes, DNS, code, prompts, runtime, models, or manifests modified.

**Release decision:**

```
CURRENT CAPACITY IS SAFE — CUTOVER CAN PROCEED
```

---

## Executive finding

`LIVE INSTANCES = 7` on the **production Container application** is **not** “7 API processes serving traffic.”

It matches the application health breakdown:

| health.instances | Count |
|------------------|------:|
| active | 1 |
| healthy | 6 |
| **sum (= LIVE / `instances`)** | **7** |
| failed | 0 |
| max_instances | 10 |

Only **one** Durable Object–backed container is actually `running` and receives production traffic: **`production-api-r3`**.

Staging is a **separate** Container application (`LIVE=2`, `max_instances=2`) and does **not** consume the production 7/10 budget.

---

## 1. Container inventory

### 1.1 Container applications (account)

| App ID | Name | Env role | State | LIVE | max_instances | App version | Updated (UTC) |
|--------|------|----------|-------|-----:|--------------:|------------:|---------------|
| `a038580f-683c-4a16-8a86-e42db39cb688` | `parallel-life-api-parallellifebackend-production` | Production | active | **7** | **10** | 2 | 2026-08-07T21:53:20Z |
| `a032c112-8987-4c52-99e8-8da2d76c2166` | `parallel-life-api-staging-parallellifebackend-staging` | Staging | ready | **2** | **2** | 2 | 2026-08-07T10:33:45Z |

Worker scripts (separate from Container app objects):

| Worker | URL | Container app |
|--------|-----|---------------|
| `parallel-life-api` (`--env production`) | https://parallel-life-api.shiroandco-office.workers.dev | production app above |
| `parallel-life-api-staging` | https://parallel-life-api-staging.shiroandco-office.workers.dev | staging app above |

Pages does **not** bind containers directly; it calls the API Worker URL baked into the FE build.

### 1.2 Named container instances (Durable Object names)

These names come from `getContainer(env.BACKEND, "<name>")` history during cutover experiments. They are **not** separate Container applications.

#### Production app instances

| Name | State | Location | Version | Created (UTC) | Classification |
|------|-------|----------|---------|---------------|----------------|
| **production-api-r3** | **running** | sin11 | 2 | 2026-08-07T21:52:06Z | **Current production** |
| production-api | inactive | — | — | 2026-08-07T21:59:37Z | Superseded / orphan DO name |
| staging-api | inactive | — | — | 2026-08-07T21:59:00Z | Orphan in **prod** DO namespace (legacy hardcoded name) |
| production-api-off | inactive | — | — | 2026-08-07T21:53:02Z | Kill-switch experiment orphan |
| production-api-r2 | inactive | — | — | 2026-08-07T21:53:03Z | Recovery attempt orphan |

`production-api-on` does **not** appear (failed to obtain a slot during the max_instances=3 incident).

#### Staging app instances

| Name | State | Location | Version | Created (UTC) | Classification |
|------|-------|----------|---------|---------------|----------------|
| staging-api | stopped | del06 | 2 | 2026-08-07T10:33:52Z | Current staging identity (sleeping) |

### 1.3 Current traffic assignment (confirmed by code + probes)

| Path | Target |
|------|--------|
| Pages `parallel-life.pages.dev` | `VITE_API_URL` → production API Worker |
| Production Worker `fetch` | `getContainer(..., "production-api-r3")` only (see `cloudflare/api-container/src/index.ts`) |
| Production `/healthz` | `env=production`, 200 |
| Staging `/healthz` | `env=staging`, 200 |

**Current production revision (container identity):** `production-api-r3` (running).  
**Current staging revision (container identity):** `staging-api` on the staging app (stopped/warm, not in prod pool).

Inactive names are **not** referenced by current Worker code paths.

---

## 2. Quota attribution

### What CLI fields mean (observed)

| Field | Source | Observed meaning |
|-------|--------|------------------|
| `LIVE INSTANCES` (list) | `wrangler containers list` | Same as app `instances` |
| `instances` | `wrangler containers info` | Provisioned/live slot count for **that app** |
| `max_instances` | info + wrangler.toml | Cap on simultaneous instances for **that app** |
| `health.instances.active` | info | Currently running containers |
| `health.instances.healthy` | info | Ready/warm (not failed) slots that still count toward LIVE |
| Named instance `state` | `containers instances` | Per–Durable Object container lifecycle (`running` / `inactive` / `stopped`) |

### Arithmetic for production

```
LIVE INSTANCES (7) = active (1) + healthy (6)
```

### What contributes to 7/10

| Bucket | Contributes to prod 7/10? | Evidence |
|--------|---------------------------|----------|
| Actively running (`production-api-r3`) | **Yes** (1 of active) | instances JSON `running` |
| Warm/idle provisioned slots | **Yes** (healthy=6) | info health; Cloudflare pre-positions free instances across locations (docs FAQ) |
| Staging app LIVE=2 | **No** | Separate app ID + separate DO namespace |
| Inactive named DOs (`production-api`, `*-off`, `*-r2`, orphan `staging-api`) | **Not proven 1:1** | 5 named rows ≠ 7 LIVE; 4 inactive have `location=null` / no version |
| Worker deployment version history | **No evidence** | Many Worker versions; LIVE tied to Container app health, not version list length |
| Pages deployments | **No** | No container binding |

### Explicit CLI/API limits

- Wrangler **does not** expose a per-slot map of which of the 6 `healthy` slots belong to which DO name or colo beyond the instances table.
- Wrangler **does not** expose a safe “delete this DO/container instance” command; `wrangler containers delete <ID>` deletes an **application**.
- Therefore: we can prove LIVE ≈ active+healthy for the app; we **cannot** prove that deleting inactive DO names would reduce LIVE from 7→1.

### Root cause of “stuck at 7”

1. Cutover experiments created multiple `getContainer` names and raised `max_instances` 3→10.
2. Cloudflare kept a provisioned pool for the production app at **7** slots (`active`+`healthy`).
3. `sleepAfter = "30m"` sleeps a **running** container on a DO; it does **not** necessarily shrink the app’s provisioned LIVE count back to 1.
4. Named orphans can remain as Durable Object identities while inactive; that is separate from the LIVE=7 pool metric.

### Why 1101 happened earlier

Error: `there is no container instance that can be provided to this durable object` with `max_instances=3`.

Mechanism: starting **additional named** Container DOs requires a free provisioned slot. Fan-out (`-off` / `-on` / `-r2`) under a small max exhausted the pool. Raising max to 10 and pinning traffic to a single name (`production-api-r3`) restored service.

---

## 3. Current production revision

| Item | Value |
|------|-------|
| Container app | `parallel-life-api-parallellifebackend-production` |
| Serving DO name | **`production-api-r3`** |
| Instance state | running @ sin11 |
| Worker routing | hardcoded `${ENV}-api-r3` → `production-api-r3` |
| Public API | https://parallel-life-api.shiroandco-office.workers.dev |
| Probe | `/healthz` → `env=production`, `deep_reading_enabled=true` |

Do **not** assume older names (`production-api`, `r2`) are current — code and instances table both show **r3** only.

---

## 4. Current staging revision

| Item | Value |
|------|-------|
| Container app | `parallel-life-api-staging-parallellifebackend-staging` |
| Serving DO name | **`staging-api`** |
| Instance state | stopped (del06) — expected idle |
| LIVE / max | 2 / 2 (separate quota) |
| Public API | https://parallel-life-api-staging.shiroandco-office.workers.dev |

---

## 5. Rollback dependency

| Asset | Keep? | Why |
|-------|-------|-----|
| Production app + `production-api-r3` | **Required** | Live traffic |
| Staging app + staging Worker/Pages | **Required** | Parallel validation / rollback reference |
| Prior Worker versions (wrangler deployments history) | **Keep** | Instant Worker rollback without deleting Container app |
| `parallel-life.pages.dev` | **Keep** | FE rollback / pre-DNS entry |
| Inactive DO names (`production-api`, `r2`, `off`, orphan `staging-api` in prod) | **Not required for traffic** | Not routed; optional cleanup only if CF later provides safe instance GC |
| Entire production Container app delete | **Unsafe** | Destroys current prod runtime |

Known-good rollback path without touching orphans:

1. `DEEP_READING_ENABLED=false` (prefer first for DR issues)
2. Roll Worker version via Cloudflare deployments
3. Keep Pages on `*.pages.dev`

---

## 6. Stale / orphan candidates

| Name | App | Safe to remove? | Notes |
|------|-----|-----------------|-------|
| production-api | prod | Candidate **if** CF provides instance GC; **not** via `containers delete` app | Superseded |
| production-api-off | prod | Same | Kill-switch lane leftover |
| production-api-r2 | prod | Same | Recovery leftover |
| staging-api (in **prod** app) | prod | Same | Legacy hardcoded name; **not** staging app |
| production-api-r3 | prod | **Do not remove** | Current |
| staging-api (staging app) | staging | **Do not remove** | Current staging identity |

---

## 7. Cleanup candidates (plan only — not executed)

### Smallest safe plan (if cleanup is later approved)

1. **Do nothing to Container applications** (no `wrangler containers delete` on prod/staging apps).
2. **Do not** create new `getContainer` names for kill-switch or recovery (avoid pool exhaustion).
3. Kill-switch only via `DEEP_READING_ENABLED` var + redeploy (same DO name).
4. Optional later: ask Cloudflare / use any future API to GC inactive DO container bindings — only after confirming LIVE decreases.
5. Optional later: lower staging `max_instances` only if account-level memory/vCPU quotas bite (does **not** free prod 7/10).

### Not recommended before cutover

- Deleting the production or staging Container application
- Aggressive Worker version pruning (low benefit for LIVE count)
- Reintroducing per-flag container name suffixes

---

## 8. max_instances recommendation

| Option | Risk | Ops impact | Solves 1101? | Needed before custom-domain cutover? |
|--------|------|------------|--------------|--------------------------------------|
| **A. Increase max_instances further** | Cost; larger warm pool | Redeploy config | Only if again fan-out names | **No** (single name + max=10 enough) |
| **B. Reduce staging footprint** | Staging cold starts | Staging toml change | No effect on prod 7/10 | **No** |
| **C. Remove superseded revisions** | High if app-deleted; unknown if DO GC exists | Needs safe GC tool | Unproven LIVE reduction | **No** (not required for cutover) |
| **D. Separate staging/prod differently** | Migration risk | Already separated by app/DO namespace | N/A | **No** — already done |
| **E. Accept 7/10; only 1 running** | Residual if someone fans out names again | None | 1101 risk low while single-name routing holds | **Yes — preferred** |

**Recommendation:** keep `max_instances=10`; accept LIVE≈7 as warm pool; enforce single production DO name.

---

## 9. Remaining 1101 risk

| Scenario | Risk level |
|----------|------------|
| Normal traffic to `production-api-r3` only | **Low** |
| Custom domain attach (Pages/API route only) | **Low** — no new container DO names |
| Kill-switch via new `getContainer` suffixes | **High** — can re-exhaust pool |
| Kill-switch via env var on same DO name | **Low–medium** (cold start possible, not pool fan-out) |
| Concurrent start of many new named DOs | **High** |

---

## 10. Cutover recommendation

```
CURRENT CAPACITY IS SAFE — CUTOVER CAN PROCEED
```

### Why not HOLD / cleanup-first

- LIVE=7 is explained as **active+healthy provisioned pool**, not 7 serving replicas.
- Staging does not share the production 10-slot budget.
- Traffic is pinned to one running instance; orphans are inactive and unrouted.
- Prior 1101 was max=3 + name fan-out; that condition is not present for domain cutover.
- CLI cannot safely delete per-instance orphans; blocking cutover on unproven cleanup is not justified.

### Still required before DNS (non-capacity)

- Confirm intended `PAGES_HOST` / optional `API_HOST`
- Follow `CUSTOM_DOMAIN_CUTOVER_PROCEDURE.md` (CORS append, reversible domain add)
- Do **not** auto-cutover without hostname approval

### Optional post-cutover hygiene (non-blocking)

- Document “never fan out container DO names for kill-switch”
- Revisit orphan DO GC if Cloudflare exposes it and LIVE remains elevated against cost targets
