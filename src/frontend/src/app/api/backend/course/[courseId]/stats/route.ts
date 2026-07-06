import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET(request: Request, ctx: RouteContext<"/api/backend/course/[courseId]/stats">) {
  try {
    const { courseId } = await ctx.params;
    return await proxyBackendJson(
      `/api/course/${courseId}/stats`,
      { method: "GET", headers: getAuthHeaders(request) },
      { timeoutMs: 15000, retries: 2 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tải thống kê tài liệu từ backend.", 502);
  }
}
