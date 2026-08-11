/**
 * Optional same-origin gateway: proxy /experience/* and /healthz to Container API.
 * Avoids browser CORS when Pages and API share a hostname via routes.
 */

export interface Env {
  UPSTREAM_API_URL: string;
  ENVIRONMENT?: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const upstreamBase = (env.UPSTREAM_API_URL || "").replace(/\/$/, "");
    if (!upstreamBase) {
      return new Response(JSON.stringify({ error: "UPSTREAM_API_URL unset" }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      });
    }

    const url = new URL(request.url);
    const path = url.pathname;
    if (
      !(
        path === "/healthz" ||
        path.startsWith("/experience/") ||
        path.startsWith("/stats") ||
        path.startsWith("/fragments") ||
        path.startsWith("/network")
      )
    ) {
      return new Response("Not found", { status: 404 });
    }

    const target = `${upstreamBase}${path}${url.search}`;
    const headers = new Headers(request.headers);
    headers.delete("host");

    const init: RequestInit = {
      method: request.method,
      headers,
      redirect: "manual",
    };
    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = request.body;
      // @ts-expect-error duplex required for streaming body in Workers
      init.duplex = "half";
    }

    return fetch(target, init);
  },
};
