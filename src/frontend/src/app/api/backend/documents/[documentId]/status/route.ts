import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET(request: Request, ctx: RouteContext<"/api/backend/documents/[documentId]/status">) {
  try {
    const { documentId } = await ctx.params;
    return proxyBackendJson(
      `/documents/${documentId}/status`,
      { method: "GET", headers: getAuthHeaders(request) },
      { timeoutMs: 30000, retries: 2 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể kiểm tra trạng thái tài liệu.", 502);
  }
}
