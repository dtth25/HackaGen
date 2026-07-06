import { proxyBackendJson, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function POST(request: Request, ctx: RouteContext<"/api/backend/course/[courseId]/generate-fallback">) {
  try {
    const { courseId } = await ctx.params;
    const body = (await request.json()) as Record<string, unknown>;

    const authHeader = request.headers.get("Authorization");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (authHeader) headers["Authorization"] = authHeader;

    return await proxyBackendJson(
      `/api/course/${courseId}/generate-fallback`,
      {
        method: "POST",
        headers,
        body: JSON.stringify({
          fallback_type: typeof body.fallback_type === "string" ? body.fallback_type : "",
          title: typeof body.title === "string" ? body.title : undefined,
        }),
      },
      { timeoutMs: 60000, retries: 1 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tạo bản dự phòng từ backend.", 502);
  }
}
