import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function POST(request: Request, ctx: RouteContext<"/api/backend/course/[courseId]/flashcards/regenerate">) {
  try {
    const { courseId } = await ctx.params;
    return await proxyBackendJson(
      `/api/course/${courseId}/flashcards/regenerate`,
      { method: "POST", headers: getAuthHeaders(request) },
      { timeoutMs: 180000, retries: 1 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tạo lại bộ thẻ ghi nhớ từ backend.", 502);
  }
}
