import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET(request: Request, ctx: RouteContext<"/api/backend/course/[courseId]/flashcards">) {
  try {
    const { courseId } = await ctx.params;
    return await proxyBackendJson(
      `/api/course/${courseId}/flashcards`,
      { method: "GET", headers: getAuthHeaders(request) },
      { timeoutMs: 60000, retries: 2 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tải bộ thẻ ghi nhớ từ backend.", 502);
  }
}
