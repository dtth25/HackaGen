import { proxyBackendJson, proxyError, proxyErrorFromUnknown } from "@/lib/server/backend";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const incoming = await request.formData();
    const files = incoming.getAll("files").filter((entry): entry is File => entry instanceof File);

    if (files.length === 0) {
      return proxyError("Vui lòng chọn ít nhất một file PDF, DOCX hoặc TXT.", 400);
    }

    const outgoing = new FormData();
    for (const file of files) {
      outgoing.append("files", file, file.name);
    }

    const authHeader = request.headers.get("Authorization");
    const headers: Record<string, string> = {};
    if (authHeader) headers["Authorization"] = authHeader;

    return proxyBackendJson(
      "/api/upload",
      {
        method: "POST",
        headers,
        body: outgoing,
      },
      { timeoutMs: 30000, retries: 2 },
    );
  } catch (error) {
    return proxyErrorFromUnknown(error, "Không thể tải tài liệu lên backend.", 502);
  }
}
