import { getAuthHeaders, proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function POST(request: Request, ctx: RouteContext<"/api/backend/course/[courseId]/vid/render">) {
  try {
    const { courseId } = await ctx.params;
    const body = (await request.json()) as Record<string, unknown>;
    const videoIndex = Number(body.video_index ?? 1);
    return await proxyBackendJson(
      `/api/course/${courseId}/vid/render`,
      {
        method: "POST",
        headers: { ...getAuthHeaders(request), "Content-Type": "application/json" },
        body: JSON.stringify({ video_index: videoIndex }),
      },
      { timeoutMs: 300000, retries: 1 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tạo video từ playlist.", 502);
  }
}
