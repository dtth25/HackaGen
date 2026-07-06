import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET(request: Request, ctx: RouteContext<"/api/backend/documents/[documentId]/sources">) {
  try {
    const { documentId } = await ctx.params;
    const url = new URL(request.url);
    const query = url.search ? url.search : "";
    return proxyBackendJson(
      `/api/documents/${documentId}/sources${query}`,
      { method: "GET", headers: getAuthHeaders(request) },
      { timeoutMs: 30000, retries: 1 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tải nguồn được dùng từ backend.", 500);
  }
}
