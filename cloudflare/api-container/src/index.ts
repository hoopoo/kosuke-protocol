/**
 * Cloudflare Container Worker — proxy HTTP to FastAPI (uvicorn :8000).
 * Deep Reading sessions persist via SESSION_STORE_* → Durable Object Worker.
 */

import { Container, getContainer } from "@cloudflare/containers";

export interface Env {
  BACKEND: DurableObjectNamespace;
  OPENAI_API_KEY: string;
  SESSION_STORE_URL: string;
  SESSION_STORE_TOKEN: string;
  SESSION_STORE_BACKEND: string;
  DEEP_READING_ENABLED: string;
  /** v1.1-exp Context Pack — staging only; must stay false/unset in production. */
  DEEP_READING_CONTEXT_PACK_ENABLED?: string;
  CORS_ALLOW_ORIGINS: string;
  ENV: string;
  ENVIRONMENT?: string;
  /** One-shot infra flag: stop running container before start so process env refreshes. */
  FORCE_CONTAINER_RESTART?: string;
}

function buildEnvVars(env: Env): Record<string, string> {
  return {
    OPENAI_API_KEY: env.OPENAI_API_KEY || "",
    SESSION_STORE_URL: env.SESSION_STORE_URL || "",
    SESSION_STORE_TOKEN: env.SESSION_STORE_TOKEN || "",
    SESSION_STORE_BACKEND: env.SESSION_STORE_BACKEND || "do",
    // Keep literal "false" — do not coerce with || "true".
    DEEP_READING_ENABLED: env.DEEP_READING_ENABLED ?? "true",
    // Default false: production must not enable Context Pack by accident.
    DEEP_READING_CONTEXT_PACK_ENABLED: env.DEEP_READING_CONTEXT_PACK_ENABLED ?? "false",
    CORS_ALLOW_ORIGINS: env.CORS_ALLOW_ORIGINS || "*",
    ENV: env.ENV || env.ENVIRONMENT || "staging",
    PYTHONUNBUFFERED: "1",
  };
}

export class ParallelLifeBackend extends Container<Env> {
  defaultPort = 8000;
  // Keep warm across multi-call Deep Reading pipelines (ground → confirm → draft → edit)
  sleepAfter = "30m";
  enableInternet = true;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    this.envVars = buildEnvVars(env);
  }

  override async fetch(request: Request): Promise<Response> {
    try {
      this.envVars = buildEnvVars(this.env);
      // Infra-only: refresh container process env (e.g. CORS) without changing getContainer name.
      if (String(this.env.FORCE_CONTAINER_RESTART || "").trim().toLowerCase() === "true") {
        try {
          await this.destroy();
        } catch (error) {
          console.error("FORCE_CONTAINER_RESTART destroy:", error);
        }
      }
      await this.startAndWaitForPorts({
        ports: 8000,
        startOptions: {
          envVars: this.envVars,
          enableInternet: true,
        },
        cancellationOptions: {
          instanceGetTimeoutMS: 90_000,
          portReadyTimeoutMS: 240_000,
          waitInterval: 1_000,
        },
      });
      return super.fetch(request);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error("ParallelLifeBackend fetch failed:", message);
      return new Response(JSON.stringify({ error: "container_unavailable", message }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      });
    }
  }

  override onError(error: unknown): void {
    console.error("ParallelLifeBackend container error:", error);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    try {
      const envName = (env.ENV || env.ENVIRONMENT || "default").trim() || "default";
      // Stable production id — do not fan out names during cutover.
      const container = getContainer(env.BACKEND, `${envName}-api-r3`);
      return await container.fetch(request);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error("Worker fetch failed:", message);
      return new Response(JSON.stringify({ error: "worker_fetch_failed", message }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      });
    }
  },
};
