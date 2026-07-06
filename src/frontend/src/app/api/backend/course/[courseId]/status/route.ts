import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET(request: Request, ctx: RouteContext<"/api/backend/course/[courseId]/status">) {
  try {
    const { courseId } = await ctx.params;
    return proxyBackendJson(
      `/api/course/${courseId}/status`,
      { method: "GET", headers: getAuthHeaders(request) },
      { timeoutMs: 30000, retries: 2 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể kiểm tra trạng thái tài liệu.", 502);
  }
}
