import { backendFetch, proxyErrorFromUnknown, proxyJsonResponse } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET() {
  try {
    const response = await backendFetch(
      "/health",
      { method: "GET" },
      { ensureReady: false, timeoutMs: 5000, retries: 2 },
    );
    return proxyJsonResponse(response);
  } catch (error) {
    return proxyErrorFromUnknown(error, "Backend chưa chạy hoặc sai cổng.", 502);
  }
}
