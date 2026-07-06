import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

async function handleProxy(request: Request, ctx: { params: Promise<{ path: string[] }> }) {
  try {
    const { path } = await ctx.params;
    const backendPath = `/auth/${path.join("/")}`;
    const headers: Record<string, string> = getAuthHeaders(request);

    let body: string | undefined = undefined;
    if (request.method !== "GET" && request.method !== "HEAD") {
      const jsonBody = await request.json().catch(() => null);
      if (jsonBody) {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify(jsonBody);
      }
    }

    return proxyBackendJson(
      backendPath,
      {
        method: request.method,
        headers,
        body,
      },
      { ensureReady: false, timeoutMs: 15000, retries: 0 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Lỗi kết nối xác thực đến backend.", 502);
  }
}

export async function GET(request: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(request, ctx);
}

export async function POST(request: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(request, ctx);
}

export async function PUT(request: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(request, ctx);
}
