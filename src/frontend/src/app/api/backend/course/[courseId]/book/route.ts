import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET(request: Request, ctx: RouteContext<"/api/backend/course/[courseId]/book">) {
  try {
    const { courseId } = await ctx.params;
    return proxyBackendJson(
      `/api/course/${courseId}/book`,
      { method: "GET", headers: getAuthHeaders(request) },
      { timeoutMs: 60000, retries: 2 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tải Book từ backend.", 502);
  }
}
