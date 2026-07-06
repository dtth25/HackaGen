import { proxyBackendJson, proxyError, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

type GenerateFeature = "book" | "slide" | "quiz" | "vid";

const SUPPORTED_FEATURES = new Set<GenerateFeature>(["book", "slide", "quiz", "vid"]);

function isGenerateFeature(value: string): value is GenerateFeature {
  return SUPPORTED_FEATURES.has(value as GenerateFeature);
}

function buildBackendRequest(feature: GenerateFeature, body: Record<string, unknown>) {
  const courseId = typeof body.course_id === "string" ? body.course_id : "";
  const prompt = typeof body.prompt === "string" ? body.prompt.trim() : "";
  const topic = (typeof body.topic === "string" && body.topic.trim()) || prompt || "tổng quan";
  const learningMode = body.learning_mode === "high_yield" ? "high_yield" : "normal";
  const videoRenderer = body.video_renderer === "manim" ? "manim" : "simple_templates";

  switch (feature) {
    case "book":
      return {
        path: "/api/generate-book",
        body: {
          course_id: courseId,
          user_prompt: prompt,
          target_audience: typeof body.target_audience === "string" ? body.target_audience : "sinh viên",
          learning_mode: learningMode,
        },
      };
    case "slide":
      return {
        path: "/api/generate-slide",
        body: {
          course_id: courseId,
          topic,
          num_slides: Number(body.num_slides ?? 8),
          learning_mode: learningMode,
        },
      };
    case "quiz":
      return {
        path: "/api/generate-quiz",
        body: {
          course_id: courseId,
          topic,
          quantity: Number(body.quantity ?? 10),
          difficulty: typeof body.difficulty === "string" ? body.difficulty : "medium",
          learning_mode: learningMode,
        },
      };
    case "vid": {
      const validModes = new Set(["sixty_second", "three_minute", "ten_minute", "playlist_by_chapter"]);
      const videoMode = typeof body.video_mode === "string" && validModes.has(body.video_mode)
        ? body.video_mode
        : "three_minute";
      return {
        path: "/api/generate-vid",
        body: {
          course_id: courseId,
          topic,
          video_mode: videoMode,
          topic_id: typeof body.topic_id === "string" ? body.topic_id : undefined,
          chapter_id: typeof body.chapter_id === "string" ? body.chapter_id : undefined,
          user_mode: typeof body.user_mode === "string" ? body.user_mode : "student",
          render_mp4: body.render_mp4 !== false,
          force: body.force === true,
          duration_minutes: Number(body.duration_minutes ?? 3),
          learning_mode: learningMode,
          video_renderer: videoRenderer,
          allow_renderer_fallback: body.allow_renderer_fallback !== false,
        },
      };
    }
  }
}

export async function POST(request: Request, ctx: RouteContext<"/api/backend/generate/[feature]">) {
  const { feature } = await ctx.params;
  if (!isGenerateFeature(feature)) {
    return proxyError("Output không hợp lệ.", 400);
  }

  try {
    const body = (await request.json()) as Record<string, unknown>;
    if (typeof body.course_id !== "string" || !body.course_id.trim()) {
      return proxyError("Thiếu mã tài liệu.", 400);
    }

    const authHeader = request.headers.get("Authorization");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (authHeader) headers["Authorization"] = authHeader;

    const config = buildBackendRequest(feature, body);
    return proxyBackendJson(
      config.path,
      {
        method: "POST",
        headers,
        body: JSON.stringify(config.body),
      },
      { timeoutMs: feature === "vid" ? 300000 : 180000, retries: 2 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tạo output từ backend.", 502);
  }
}
