import { proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET() {
  try {
    return await proxyBackendJson(
      "/api/demo-course",
      { method: "GET" },
      { timeoutMs: 15000, retries: 2 }
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tải tài liệu demo từ backend.", 502);
  }
}
