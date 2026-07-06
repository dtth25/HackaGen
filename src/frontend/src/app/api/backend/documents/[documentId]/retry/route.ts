import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function POST(request: Request, ctx: RouteContext<"/api/backend/documents/[documentId]/retry">) {
  try {
    const { documentId } = await ctx.params;
    return proxyBackendJson(
      `/documents/${documentId}/retry`,
      { method: "POST", headers: getAuthHeaders(request) },
      { timeoutMs: 30000, retries: 1 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể chạy lại phân tích tài liệu.", 502);
  }
}
