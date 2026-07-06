import { backendFetch, getAuthHeaders, proxyError, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function GET(request: Request, ctx: RouteContext<"/api/backend/download/[...path]">) {
  try {
    const { path } = await ctx.params;
    const backendPath = path.join("/");

    if (!backendPath.startsWith("api/course/")) {
      return proxyError("Đường dẫn tải file không hợp lệ.", 400);
    }

    const response = await backendFetch(
      `/${backendPath}`,
      { method: "GET", headers: getAuthHeaders(request) },
      { timeoutMs: 120000, retries: 2 },
    );
    const headers = new Headers();
    for (const header of ["content-type", "content-disposition", "content-length"]) {
      const value = response.headers.get(header);
      if (value) headers.set(header, value);
    }
    headers.set("Cache-Control", "no-store");

    return new Response(response.body, {
      status: response.status,
      headers,
    });
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tải file từ backend.", 502);
  }
}
