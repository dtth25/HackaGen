const DEFAULT_BACKEND_API_BASE_URL = "http://127.0.0.1:8000";
const BACKEND_STARTING_MESSAGE = "Backend đang khởi động, vui lòng chờ vài giây.";
const BACKEND_DOWN_MESSAGE = "Backend chưa chạy hoặc sai cổng.";
const BACKEND_TIMEOUT_MESSAGE =
  "Backend xử lý quá lâu, vui lòng chờ preprocess hoàn tất.";
const DEFAULT_BACKOFF_MS = [1000, 2000, 4000];

export const BACKEND_API_BASE_URL = (
  process.env.BACKEND_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  DEFAULT_BACKEND_API_BASE_URL
)
  .replace("://localhost:", "://127.0.0.1:")
  .replace(/\/$/, "");

export class BackendProxyError extends Error {
  status: number;
  payload?: unknown;

  constructor(message: string, status = 502, payload?: unknown) {
    super(message);
    this.name = "BackendProxyError";
    this.status = status;
    this.payload = payload;
  }
}

interface BackendHealthPayload {
  status?: "ok" | "starting" | "error";
  ready?: boolean;
  details?: Record<string, boolean>;
  error?: string | null;
}

interface BackendFetchOptions {
  retries?: number;
  timeoutMs?: number;
  ensureReady?: boolean;
}

export function backendUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${BACKEND_API_BASE_URL}${normalizedPath}`;
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new BackendProxyError(BACKEND_TIMEOUT_MESSAGE, 504);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function readResponsePayload(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json().catch(() => ({ detail: "Backend returned invalid JSON." }));
  }
  return { detail: await response.text().catch(() => response.statusText) };
}

function backendMessageFromPayload(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    const message = record.detail ?? record.message ?? record.error;
    if (typeof message === "string" && message.trim()) return message;
  }
  return fallback;
}

export async function ensureBackendReady(retries = 3) {
  let lastError: unknown = null;

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await fetchWithTimeout(
        backendUrl("/health"),
        { cache: "no-store" },
        5000,
      );
      const payload = (await readResponsePayload(response)) as BackendHealthPayload;

      if (response.ok && payload.ready) return payload;

      const message =
        payload.status === "starting" || response.status === 503
          ? BACKEND_STARTING_MESSAGE
          : backendMessageFromPayload(payload, "Backend chưa sẵn sàng.");

      if (attempt === retries) {
        throw new BackendProxyError(message, response.status || 503, payload);
      }
    } catch (error) {
      lastError = error;
      if (error instanceof BackendProxyError && error.status === 504) {
        throw error;
      }
      if (attempt === retries) {
        if (error instanceof BackendProxyError) throw error;
        throw new BackendProxyError(BACKEND_DOWN_MESSAGE, 502);
      }
    }

    await wait(DEFAULT_BACKOFF_MS[Math.min(attempt, DEFAULT_BACKOFF_MS.length - 1)]);
  }

  if (lastError instanceof BackendProxyError) throw lastError;
  throw new BackendProxyError(BACKEND_DOWN_MESSAGE, 502);
}

export async function backendFetch(
  path: string,
  init: RequestInit = {},
  options: BackendFetchOptions = {},
) {
  const retries = options.retries ?? 2;
  const timeoutMs = options.timeoutMs ?? 60000;
  const shouldEnsureReady = options.ensureReady ?? true;

  if (shouldEnsureReady) {
    await ensureBackendReady(2);
  }

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await fetchWithTimeout(
        backendUrl(path),
        { ...init, cache: init.cache ?? "no-store" },
        timeoutMs,
      );

      if (![502, 503, 504].includes(response.status) || attempt === retries) {
        return response;
      }
    } catch (error) {
      if (error instanceof BackendProxyError && error.status === 504) {
        if (attempt === retries) throw error;
      } else if (attempt === retries) {
        if (error instanceof BackendProxyError) throw error;
        throw new BackendProxyError(BACKEND_DOWN_MESSAGE, 502);
      }
    }

    await wait(DEFAULT_BACKOFF_MS[Math.min(attempt, DEFAULT_BACKOFF_MS.length - 1)]);
  }

  throw new BackendProxyError(BACKEND_DOWN_MESSAGE, 502);
}

export async function proxyJsonResponse(response: Response) {
  const payload = await readResponsePayload(response);
  const headers = new Headers({ "Cache-Control": "no-store" });
  const setCookie = response.headers.get("set-cookie");
  if (setCookie) {
    headers.set("Set-Cookie", setCookie);
  }

  return Response.json(payload, {
    status: response.status,
    headers,
  });
}

export async function proxyBackendJson(
  path: string,
  init: RequestInit = {},
  options: BackendFetchOptions = {},
) {
  try {
    const response = await backendFetch(path, init, options);
    return proxyJsonResponse(response);
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể kết nối backend.");
  }
}

export function proxyError(message: string, status = 500) {
  return Response.json({ detail: message }, { status });
}

export function proxyErrorFromUnknown(error: unknown, fallback: string, status = 502) {
  if (error instanceof BackendProxyError) {
    return proxyError(error.message, error.status);
  }
  if (error instanceof Error && error.message) {
    return proxyError(error.message, status);
  }
  return proxyError(fallback, status);
}

export function getAuthHeaders(request: Request): Record<string, string> {
  const authHeader = request.headers.get("Authorization");
  const cookieHeader = request.headers.get("Cookie");
  return {
    ...(authHeader ? { Authorization: authHeader } : {}),
    ...(cookieHeader ? { Cookie: cookieHeader } : {}),
  };
}
