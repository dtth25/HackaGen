import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET(request: Request, ctx: RouteContext<"/api/backend/course/[courseId]/study-pack">) {
  try {
    const { courseId } = await ctx.params;
    return proxyBackendJson(
      `/api/course/${courseId}/study-pack`,
      { method: "GET", headers: getAuthHeaders(request) },
      { timeoutMs: 60000, retries: 2 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tải Study Pack từ backend.", 502);
  }
}
