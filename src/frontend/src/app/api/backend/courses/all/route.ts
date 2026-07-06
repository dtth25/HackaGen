import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET(request: Request) {
  try {
    return proxyBackendJson(
      "/api/courses/all",
      { method: "GET", headers: getAuthHeaders(request) },
      { timeoutMs: 30000, retries: 2 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tải danh sách tài liệu.", 502);
  }
}
