import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function DELETE(request: Request, ctx: RouteContext<"/api/backend/documents/[documentId]">) {
  try {
    const { documentId } = await ctx.params;
    return proxyBackendJson(
      `/api/documents/${documentId}`,
      { method: "DELETE", headers: getAuthHeaders(request) },
      { timeoutMs: 30000, retries: 1 }
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể xóa tài liệu từ backend.", 500);
  }
}
