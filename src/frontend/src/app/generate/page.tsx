"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  BookOpen,
  CheckCircle2,
  CircleAlert,
  ClipboardCheck,
  FileText,
  FileVideo,
  Layers,
  Loader2,
  Presentation,
} from "lucide-react";
import { toast } from "sonner";
import dynamic from "next/dynamic";
import FeatureSelector, { type FeatureType } from "@/components/FeatureSelector";
import PromptInput from "@/components/PromptInput";
import UploadBox from "@/components/UploadBox";

const ResultRenderer = dynamic(() => import("@/components/ResultRenderer"), {
  loading: () => (
    <div className="flex flex-col items-center justify-center rounded-lg border bg-card p-12 text-muted-foreground">
      <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
      <p className="text-sm">Đang tải khu vực hiển thị kết quả...</p>
    </div>
  ),
  ssr: false,
});
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  type CourseStatusResponse,
  type DocumentStatusResponse,
  type GenerateResponse,
  type UploadResponse,
  friendlyApiErrorMessage,
  generateContent,
  getDocumentStatus,
  getDemoCourse,
  retryDocumentAnalysis,
} from "@/lib/api";

type CourseStatus = CourseStatusResponse["status"] | "idle";
type CourseStage = NonNullable<CourseStatusResponse["stage"]>;
type OutputMap = Partial<Record<FeatureType, GenerateResponse>>;

const OUTPUT_ORDER: FeatureType[] = ["book", "slide", "quiz", "vid"];
const OUTPUT_LABELS: Record<FeatureType, { title: string; description: string; icon: ReactNode }> = {
  book: {
    title: "Sách",
    description: "Tạo sách tiếng Việt có cấu trúc từ tài liệu của bạn.",
    icon: <BookOpen className="h-4 w-4" />,
  },
  slide: {
    title: "Slides",
    description: "Tùy chọn PPTX",
    icon: <Presentation className="h-4 w-4" />,
  },
  quiz: {
    title: "Quiz",
    description: "Làm bài + key",
    icon: <ClipboardCheck className="h-4 w-4" />,
  },
  vid: {
    title: "Video",
    description: "Tùy chọn MP4",
    icon: <FileVideo className="h-4 w-4" />,
  },
};
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function statusCopy(status: CourseStatus) {
  switch (status) {
    case "ready":
      return "Tài liệu đã sẵn sàng";
    case "completed_limited":
      return "Tài liệu sẵn sàng với ngữ cảnh giới hạn";
    case "paused_due_to_quota":
      return "Tạm dừng vì giới hạn Gemini";
    case "failed":
      return "Lỗi phân tích tài liệu";
    case "processing":
    case "pending":
      return "Đang phân tích tài liệu";
    case "unknown":
      return "Chưa tìm thấy tài liệu";
    default:
      return "Chưa có tài liệu";
  }
}

function stageCopy(stage?: CourseStage) {
  switch (stage) {
    case "uploading":
      return "Đang tải tài liệu";
    case "extracting_text":
      return "Đang đọc nội dung";
    case "chunking":
      return "Đang chia nhỏ kiến thức";
    case "embedding":
      return "Đang tạo embedding";
    case "storing_vectors":
      return "Đang lưu vào Vector DB";
    case "completed":
      return "Hoàn tất";
    case "completed_limited":
      return "Hoàn tất một phần";
    case "failed":
      return "Thất bại";
    case "paused_due_to_quota":
      return "Tạm dừng do vượt giới hạn quota";
    case "analysis_failed":
      return "Phân tích thất bại";
    case "extraction_failed":
      return "Trích xuất nội dung thất bại";
    case "embedding_failed":
      return "Tạo embedding thất bại";
    case "vector_index_failed":
      return "Lưu Chroma thất bại";
    case "insufficient_context":
      return "Không đủ ngữ cảnh";
    default:
      return "";
  }
}

function recommendedActionCopy(action?: string | null) {
  switch (action) {
    case "wait_for_quota":
      return "Chờ khoảng 1 phút rồi thử lại, hoặc dùng file nhỏ hơn.";
    case "upload_clearer_pdf":
      return "Tải bản PDF có text rõ hơn, hoặc bật OCR nếu đây là file scan.";
    case "check_api_key":
      return "Kiểm tra Gemini API key ở backend rồi chạy lại.";
    case "check_chroma":
      return "Kiểm tra Chroma persist dir/collection hoặc khởi động lại backend.";
    case "check_network":
      return "Kiểm tra kết nối Internet/VPN/firewall của máy, rồi bấm thử lại — tài liệu của bạn không có vấn đề gì.";
    case "retry":
      return "Chạy lại phân tích từ file đã upload.";
    default:
      return action || "";
  }
}

export default function GeneratePage() {
  const router = useRouter();
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState<FeatureType>("book");
  const [generatingFeature, setGeneratingFeature] = useState<FeatureType | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [courseId, setCourseId] = useState("");
  const [filenames, setFilenames] = useState<string[]>([]);
  const [courseStatus, setCourseStatus] = useState<CourseStatus>("idle");
  const [courseStage, setCourseStage] = useState<CourseStage | undefined>();
  const [outputs, setOutputs] = useState<OutputMap>({});
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [documentFailure, setDocumentFailure] = useState<DocumentStatusResponse | null>(null);
  const [retryingAnalysis, setRetryingAnalysis] = useState(false);
  const [learningMode, setLearningMode] = useState<"normal" | "high_yield">("normal");
  const [videoRenderer, setVideoRenderer] = useState<"simple_templates" | "manim">("simple_templates");
  const [lastPrompt, setLastPrompt] = useState("tổng quan");

  // Guards the poll loop below against continuing (and calling setState) after this
  // page has unmounted — e.g. the user navigates away mid-upload. Without this, an
  // in-flight poll keeps hitting the backend every 2s for up to 3 minutes per visit,
  // and repeated uploads-then-navigate-away cycles stack up concurrent pollers.
  const pollCancelledRef = useRef(false);
  useEffect(() => {
    pollCancelledRef.current = false;
    return () => {
      pollCancelledRef.current = true;
    };
  }, []);

  const pollDocumentStatus = async (documentId: string) => {
    setIsPolling(true);
    setCourseStatus("processing");
    setCourseStage("extracting_text");
    setProgress(0);
    setProgressMessage("Đang khởi tạo...");
    setDocumentFailure(null);

    try {
      for (let attempt = 0; attempt < 90; attempt += 1) {
        if (pollCancelledRef.current) return;
        const status = await getDocumentStatus(documentId);
        if (pollCancelledRef.current) return;
        const stage: CourseStage = status.stage ?? (status.status === "completed" ? "completed" : status.status);
        setCourseStage(stage);
        setProgress(status.progress);
        setProgressMessage(status.message);

        if (status.status === "completed" || status.status === "completed_limited") {
          setCourseStatus("ready");
          setProgress(100);
          setCourseStage(status.status === "completed_limited" ? "completed_limited" : "completed");
          setProgressMessage(status.message || "Tài liệu đã sẵn sàng");
          if (status.status === "completed_limited") {
            toast.warning(status.message || "Tài liệu đã sẵn sàng nhưng ngữ cảnh còn giới hạn.");
          } else {
            toast.success("Tài liệu đã xử lý xong! Đang mở không gian học tập...");
          }
          setTimeout(() => {
            if (!pollCancelledRef.current) router.push(`/dashboard/${documentId}`);
          }, 1200);
          return;
        }

        if (status.status === "paused_due_to_quota") {
          setCourseStatus("paused_due_to_quota");
          setDocumentFailure(status);
          toast.error(
            friendlyApiErrorMessage(status.user_message || status.error || status.message, "EMBEDDING_QUOTA_EXCEEDED"),
          );
          return;
        }

        if (status.status === "failed") {
          setCourseStatus("failed");
          setDocumentFailure(status);
          toast.error(status.user_message || status.error || status.message || "Không phân tích được tài liệu.");
          return;
        }

        setCourseStatus("processing");
        await wait(2000);
      }

      if (!pollCancelledRef.current) {
        throw new Error("Tài liệu xử lý quá lâu. Vui lòng thử lại sau.");
      }
    } catch (err) {
      if (pollCancelledRef.current) return;
      const message =
        err instanceof Error ? err.message : "Không kiểm tra được trạng thái tài liệu.";
      const friendlyMessage = friendlyApiErrorMessage(message);
      setCourseStatus("failed");
      setCourseStage(
        friendlyMessage === friendlyApiErrorMessage(undefined, "EMBEDDING_QUOTA_EXCEEDED")
          ? "paused_due_to_quota"
          : "failed",
      );
      setDocumentFailure({
        document_id: documentId,
        status: "failed",
        stage: "analysis_failed",
        failure_stage: "analysis_failed",
        progress,
        message: friendlyMessage,
        error: friendlyMessage,
        user_message: friendlyMessage,
        technical_error: message,
        can_retry: true,
        recommended_action: "retry",
      });
      toast.error(friendlyMessage);
    } finally {
      if (!pollCancelledRef.current) setIsPolling(false);
    }
  };

  const handleUploaded = (upload: UploadResponse) => {
    setCourseId(upload.course_id);
    setFilenames(upload.filenames?.length ? upload.filenames : [upload.filename]);
    setOutputs({});
    setDocumentFailure(null);
    void pollDocumentStatus(upload.document_id || upload.course_id);
  };

  const handleRetryAnalysis = async () => {
    if (!courseId) return;
    setRetryingAnalysis(true);
    setDocumentFailure(null);
    try {
      const retryStatus = await retryDocumentAnalysis(courseId);
      toast.success(retryStatus.message || "Đang chạy lại phân tích tài liệu...");
      void pollDocumentStatus(courseId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Không thể chạy lại phân tích tài liệu.";
      const friendlyMessage = friendlyApiErrorMessage(message);
      setDocumentFailure({
        document_id: courseId,
        status: "failed",
        stage: "analysis_failed",
        failure_stage: "analysis_failed",
        progress,
        message: friendlyMessage,
        error: friendlyMessage,
        user_message: friendlyMessage,
        technical_error: message,
        can_retry: true,
        recommended_action: "retry",
      });
      toast.error(friendlyMessage);
    } finally {
      setRetryingAnalysis(false);
    }
  };

  const handleLoadDemo = async () => {
    setLoadingDemo(true);
    try {
      const demo = await getDemoCourse();
      toast.success(demo.message || "Đã nạp tài liệu demo thành công!");
      handleUploaded(demo);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không thể nạp demo.");
    } finally {
      setLoadingDemo(false);
    }
  };

  const handlePromptSubmit = async (prompt: string) => {
    if (!courseId) {
      toast.error("Vui lòng tải tài liệu lên trước.");
      return;
    }

    if (courseStatus !== "ready") {
      toast.error("Tài liệu chưa sẵn sàng để tạo nội dung.");
      return;
    }

    setGeneratingFeature(selectedFeature);
    setLastPrompt(prompt || "tổng quan");

    try {
      const response = await generateContent(selectedFeature, courseId, prompt, learningMode, {
        videoRenderer,
        allowRendererFallback: true,
      });
      setOutputs((prev) => ({ ...prev, [selectedFeature]: response }));
      toast.success(`Đã tạo ${selectedFeature.toUpperCase()}.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Có lỗi xảy ra khi tạo nội dung.";
      toast.error(friendlyApiErrorMessage(message));
    } finally {
      setGeneratingFeature(null);
    }
  };

  const regenerateFeature = async (feature: FeatureType) => {
    if (!courseId || courseStatus !== "ready") return;
    setSelectedFeature(feature);
    setGeneratingFeature(feature);
    try {
      const response = await generateContent(feature, courseId, lastPrompt, learningMode, {
        videoRenderer,
        allowRendererFallback: true,
      });
      setOutputs((prev) => ({ ...prev, [feature]: response }));
      toast.success(`Đã tạo lại ${feature.toUpperCase()}.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Có lỗi xảy ra khi tạo lại nội dung.";
      toast.error(friendlyApiErrorMessage(message));
    } finally {
      setGeneratingFeature(null);
    }
  };

  const status = statusCopy(courseStatus);
  const stage = stageCopy(courseStage);
  const hasOutputs = OUTPUT_ORDER.some((feature) => outputs[feature]);
  const readyOutputCount = OUTPUT_ORDER.filter((feature) => outputs[feature]).length;
  const failureStage = stageCopy(documentFailure?.failure_stage ?? documentFailure?.stage);
  const failureAction = recommendedActionCopy(documentFailure?.recommended_action);

  return (
    <div className="flex w-full flex-col">
      <section className="mb-8 grid gap-6 lg:grid-cols-[1fr_360px] lg:items-end">
        <div className="space-y-3">
          <h1 className="max-w-3xl text-2xl font-extrabold tracking-tight sm:text-3xl text-foreground">
            Biến tài liệu thành Study Pack
          </h1>
          <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
            Tải lên PDF, DOCX hoặc TXT để nhận Sách, Mindmap, Quiz, Flashcards và bản tóm tắt trọng tâm.
          </p>
          <div className="pt-1">
            <Button
              variant="outline"
              onClick={handleLoadDemo}
              disabled={loadingDemo}
              className="font-medium gap-2"
            >
              {loadingDemo && <Loader2 className="h-4 w-4 animate-spin" />}
              Dùng tài liệu demo
            </Button>
          </div>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              {courseStatus === "ready" ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              ) : courseStatus === "failed" || courseStatus === "paused_due_to_quota" ? (
                <CircleAlert className="h-4 w-4 text-destructive" />
              ) : courseStatus === "idle" ? (
                <FileText className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              )}
              {courseStatus === "failed" && documentFailure?.user_message ? documentFailure.user_message : status}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            {courseId ? (
              <>
                <p>{filenames.length} tài liệu đã tải lên</p>
                {filenames.length > 0 && (
                  <div className="max-h-24 space-y-1 overflow-auto rounded-md bg-muted/50 p-2">
                    {filenames.map((name) => (
                      <div key={name} className="truncate">
                        {name}
                      </div>
                    ))}
                  </div>
                )}
                {isPolling && (
                  <div className="space-y-2">
                    <Progress value={Math.max(0, progress)} className="h-2" />
                    <div className="flex items-center justify-between text-xs">
                      <span>{progressMessage || "Đang xử lý..."}</span>
                      <span className="font-semibold">{Math.max(0, progress)}%</span>
                    </div>
                  </div>
                )}
                {!isPolling && courseStatus === "ready" && (
                  <div className="space-y-3 pt-2">
                    <p className="text-sm font-medium text-emerald-600">{progressMessage || "Tài liệu đã sẵn sàng."}</p>
                    <Link href={`/dashboard/${courseId}`} className="block">
                      <Button className="w-full font-medium shadow-sm gap-2">
                        Vào không gian học tập
                      </Button>
                    </Link>
                  </div>
                )}

                {!isPolling && documentFailure && (
                  <div className="space-y-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm">
                    <div className="flex items-start gap-2">
                      <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                      <div className="space-y-1">
                        <p className="font-semibold text-foreground">
                          {documentFailure.user_message || documentFailure.error || documentFailure.message}
                        </p>
                        {failureStage && (
                          <p className="text-xs text-muted-foreground">
                            Giai đoạn lỗi: <span className="font-medium text-foreground">{failureStage}</span>
                          </p>
                        )}
                        {failureAction && <p className="text-xs text-muted-foreground">Gợi ý: {failureAction}</p>}
                      </div>
                    </div>
                    {documentFailure.can_retry !== false && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="w-full gap-2"
                        disabled={retryingAnalysis}
                        onClick={handleRetryAnalysis}
                      >
                        {retryingAnalysis && <Loader2 className="h-4 w-4 animate-spin" />}
                        Thử phân tích lại
                      </Button>
                    )}
                    {documentFailure.technical_error && (
                      <details className="text-xs">
                        <summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">
                          Xem chi tiết kỹ thuật
                        </summary>
                        <pre className="mt-2 max-h-40 overflow-auto rounded-md bg-background/80 p-2 font-mono text-[11px] text-muted-foreground">
                          {documentFailure.technical_error}
                        </pre>
                      </details>
                    )}
                  </div>
                )}

                <details className="pt-1 text-xs">
                  <summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">
                    Chi tiết kỹ thuật
                  </summary>
                  <div className="mt-2 space-y-1 border-t border-border/60 pt-2 text-muted-foreground">
                    <div className="flex justify-between">
                      <span>Mã tài liệu</span>
                      <span className="font-mono text-foreground">{courseId}</span>
                    </div>
                    {stage && (
                      <div className="flex justify-between">
                        <span>Giai đoạn</span>
                        <span className="text-foreground">{stage}</span>
                      </div>
                    )}
                  </div>
                </details>
              </>
            ) : (
              <p>Tải tài liệu lên để bắt đầu tạo học liệu.</p>
            )}
          </CardContent>
        </Card>
      </section>

      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <aside className="space-y-6">
          <div className="flex items-center gap-2 px-1">
            <FileText className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-bold text-foreground">Nguồn</h2>
          </div>
          {!courseId && (
            <p className="px-1 text-xs text-muted-foreground">
              Chưa có tài liệu. Thêm PDF, DOCX hoặc TXT để bắt đầu.
            </p>
          )}
          <UploadBox onUploaded={handleUploaded} />
          <Card>
            <CardContent className="space-y-6 p-5">
              <FeatureSelector selected={selectedFeature} onSelect={setSelectedFeature} />
              <div className="rounded-xl border bg-muted/30 p-3">
                <div className="mb-2 text-sm font-semibold">Chế độ học trọng tâm</div>
                <button
                  type="button"
                  onClick={() => setLearningMode((mode) => (mode === "high_yield" ? "normal" : "high_yield"))}
                  className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                    learningMode === "high_yield"
                      ? "border-primary bg-primary/10 text-primary"
                      : "bg-background text-muted-foreground hover:bg-muted"
                  }`}
                >
                  Đọc ít hơn, nhớ nhiều hơn
                </button>
              </div>
              {selectedFeature === "vid" && (
                <div className="rounded-xl border bg-muted/30 p-3">
                  <div className="mb-2 text-sm font-semibold">Kiểu render video</div>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { value: "simple_templates", label: "Video thường", desc: "Template động nhẹ" },
                      { value: "manim", label: "Kiểu Manim", desc: "Tự fallback nếu thiếu" },
                    ].map((item) => (
                      <button
                        key={item.value}
                        type="button"
                        onClick={() => setVideoRenderer(item.value as "simple_templates" | "manim")}
                        className={`rounded-lg border px-3 py-2 text-left transition-colors ${
                          videoRenderer === item.value
                            ? "border-primary bg-primary/10 text-primary"
                            : "bg-background text-muted-foreground hover:bg-muted"
                        }`}
                      >
                        <span className="block text-sm font-medium">{item.label}</span>
                        <span className="text-xs">{item.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <PromptInput
                onSubmit={handlePromptSubmit}
                isLoading={generatingFeature === selectedFeature}
                disabled={!courseId || courseStatus !== "ready" || Boolean(generatingFeature)}
              />
            </CardContent>
          </Card>
        </aside>

        <section className="min-w-0 space-y-6">
          <div className="rounded-lg border bg-card p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-muted-foreground" />
                <h2 className="text-sm font-semibold">Bộ học liệu</h2>
              </div>
              <span className="text-xs text-muted-foreground">{readyOutputCount}/4 phần đã tạo</span>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              {OUTPUT_ORDER.map((feature) => {
                const meta = OUTPUT_LABELS[feature];
                const isSelected = selectedFeature === feature;
                const isReady = Boolean(outputs[feature]);
                const isGenerating = generatingFeature === feature;
                return (
                  <button
                    key={feature}
                    type="button"
                    onClick={() => setSelectedFeature(feature)}
                    className={`rounded-xl border p-3.5 text-left transition-all shadow-sm ${
                      isSelected
                        ? "border-primary bg-primary/10 ring-2 ring-primary/20 shadow"
                        : "bg-card hover:bg-secondary/60 hover:border-border"
                    }`}
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="flex items-center gap-2 text-sm font-semibold">
                        {meta.icon}
                        {meta.title}
                      </span>
                      {isGenerating ? (
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      ) : isReady ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      ) : (
                        <span className="h-2 w-2 rounded-full bg-muted-foreground/30" />
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">{meta.description}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {!hasOutputs && generatingFeature && (
            <div className="flex min-h-[360px] flex-col items-center justify-center rounded-lg border bg-card p-8 text-center">
              <Loader2 className="mb-4 h-10 w-10 animate-spin text-muted-foreground" />
              <h2 className="text-lg font-semibold">Đang xử lý</h2>
              <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                Kết quả sẽ xuất hiện ở đây khi xử lý xong.
              </p>
            </div>
          )}

          {!hasOutputs && !generatingFeature && (
            <div className="flex min-h-[420px] flex-col items-center justify-center rounded-lg border bg-card p-8 text-center">
              <BookOpen className="mb-4 h-10 w-10 text-muted-foreground" />
              <h2 className="text-lg font-semibold">
                {courseId ? "Bộ học liệu sẽ xuất hiện ở đây." : "Upload tài liệu để tạo Study Pack."}
              </h2>
              <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                {courseId
                  ? "Tạo Sách trước để mở Mindmap, Flashcards, Bản rút gọn và Quiz cùng nguồn."
                  : "Tải tài liệu lên ở khung Nguồn bên trái để bắt đầu."}
              </p>
            </div>
          )}

          {OUTPUT_ORDER.map((feature) => {
            const result = outputs[feature];
            if (!result) return null;
            return (
              <ResultRenderer
                key={feature}
                feature={feature}
                result={result}
                onRegenerate={feature === "vid" ? () => regenerateFeature(feature) : undefined}
                isRegenerating={generatingFeature === feature}
              />
            );
          })}
        </section>
      </div>
    </div>
  );
}
