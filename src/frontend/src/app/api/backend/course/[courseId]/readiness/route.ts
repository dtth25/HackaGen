import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET(request: Request, ctx: RouteContext<"/api/backend/course/[courseId]/readiness">) {
  try {
    const { courseId } = await ctx.params;
    return await proxyBackendJson(
      `/api/course/${courseId}/readiness`,
      { method: "GET", headers: getAuthHeaders(request) },
      { timeoutMs: 15000, retries: 2 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tải báo cáo readiness từ backend.", 502);
  }
}
