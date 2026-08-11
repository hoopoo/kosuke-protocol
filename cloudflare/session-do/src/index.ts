/**
 * Deep Reading session Durable Object Worker.
 * Stores full session JSON keyed by session_id. No manuscript logging.
 */

export interface Env {
  SESSION: DurableObjectNamespace;
  SESSION_STORE_TOKEN?: string;
  ENVIRONMENT?: string;
}

type SessionBlob = {
  session_id: string;
  session_revision?: number;
  expires_at?: string;
  status?: string;
  [key: string]: unknown;
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function unauthorized(): Response {
  return json({ error: "unauthorized" }, 401);
}

function authorize(request: Request, env: Env): boolean {
  const expected = (env.SESSION_STORE_TOKEN || "").trim();
  if (!expected) {
    // Staging convenience: allow if secret unset (local wrangler dev).
    return true;
  }
  const header = request.headers.get("Authorization") || "";
  const token = header.startsWith("Bearer ") ? header.slice(7).trim() : "";
  return token === expected;
}

function parseExpiresMs(expiresAt: string | undefined): number | null {
  if (!expiresAt) return null;
  const t = Date.parse(expiresAt);
  return Number.isFinite(t) ? t : null;
}

export class DeepReadingSessionDO implements DurableObject {
  private state: DurableObjectState;

  constructor(state: DurableObjectState, _env: Env) {
    this.state = state;
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const method = request.method.toUpperCase();

    if (method === "GET") {
      const session = await this.state.storage.get<SessionBlob>("session");
      if (!session) return json({ error: "not_found" }, 404);
      const exp = parseExpiresMs(session.expires_at);
      if (exp !== null && Date.now() >= exp) {
        await this.state.storage.deleteAll();
        return json({ error: "expired" }, 404);
      }
      return json(session);
    }

    if (method === "PUT") {
      const body = (await request.json()) as SessionBlob;
      if (!body || typeof body.session_id !== "string") {
        return json({ error: "invalid_body" }, 400);
      }
      const session: SessionBlob = {
        ...body,
        session_revision: typeof body.session_revision === "number" ? body.session_revision : 0,
      };
      await this.state.storage.put("session", session);
      await this.scheduleAlarm(session.expires_at);
      return json(session);
    }

    if (method === "PATCH") {
      const payload = (await request.json()) as {
        session?: SessionBlob;
        expected_revision?: number | null;
        extend_ttl_hours?: number | null;
      };
      const current = await this.state.storage.get<SessionBlob>("session");
      if (!current) return json({ error: "not_found" }, 404);

      const exp = parseExpiresMs(current.expires_at);
      if (exp !== null && Date.now() >= exp) {
        await this.state.storage.deleteAll();
        return json({ error: "expired" }, 410);
      }

      if (
        payload.expected_revision !== undefined &&
        payload.expected_revision !== null &&
        (current.session_revision ?? 0) !== payload.expected_revision
      ) {
        return json(
          {
            error: "stale_revision",
            expected: payload.expected_revision,
            actual: current.session_revision ?? 0,
          },
          409
        );
      }

      const incoming = payload.session || {};
      let expiresAt = typeof incoming.expires_at === "string" ? incoming.expires_at : current.expires_at;
      if (typeof payload.extend_ttl_hours === "number" && payload.extend_ttl_hours > 0) {
        expiresAt = new Date(Date.now() + payload.extend_ttl_hours * 3600_000).toISOString();
      }

      const next: SessionBlob = {
        ...current,
        ...incoming,
        session_id: current.session_id,
        session_revision: (current.session_revision ?? 0) + 1,
        updated_at: new Date().toISOString(),
        expires_at: expiresAt,
      };
      await this.state.storage.put("session", next);
      await this.scheduleAlarm(next.expires_at);
      return json(next);
    }

    if (method === "DELETE") {
      await this.state.storage.deleteAll();
      await this.state.storage.deleteAlarm();
      return new Response(null, { status: 204 });
    }

    return json({ error: "method_not_allowed" }, 405);
  }

  async alarm(): Promise<void> {
    const session = await this.state.storage.get<SessionBlob>("session");
    if (!session) return;
    const exp = parseExpiresMs(session.expires_at);
    if (exp === null || Date.now() >= exp) {
      // Incomplete / expired cleanup — never log manuscript fields.
      await this.state.storage.deleteAll();
    }
  }

  private async scheduleAlarm(expiresAt: string | undefined): Promise<void> {
    const exp = parseExpiresMs(expiresAt);
    if (exp === null) return;
    await this.state.storage.setAlarm(exp);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/healthz") {
      return json({ status: "ok", service: "parallel-life-session-do" });
    }

    if (!authorize(request, env)) return unauthorized();

    const match = url.pathname.match(/^\/sessions\/([^/]+)\/?$/);
    if (!match) {
      return json({ error: "not_found" }, 404);
    }

    const sessionId = decodeURIComponent(match[1]);
    if (!sessionId) return json({ error: "invalid_session_id" }, 400);

    const id = env.SESSION.idFromName(sessionId);
    const stub = env.SESSION.get(id);
    return stub.fetch(request);
  },
};
