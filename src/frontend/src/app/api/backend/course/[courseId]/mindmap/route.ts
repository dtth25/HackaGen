import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET(request: Request, ctx: RouteContext<"/api/backend/course/[courseId]/mindmap">) {
  try {
    const { courseId } = await ctx.params;
    return await proxyBackendJson(
      `/api/course/${courseId}/mindmap`,
      { method: "GET", headers: getAuthHeaders(request) },
      { timeoutMs: 60000, retries: 2 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tải sơ đồ tư duy từ backend.", 502);
  }
}
