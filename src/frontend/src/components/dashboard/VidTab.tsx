"use client";

import { useEffect, useRef, useState } from "react";
import { usePollingArtifact } from "@/hooks/usePollingArtifact";
import {
  Video,
  RefreshCw,
  Download,
  FileText,
  Maximize2,
  X,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { VidOptionsPanel } from "@/components/dashboard/VidOptionsPanel";
import { RegenerateButton } from "@/components/dashboard/RegenerateButton";
import { VersionSwitcher } from "@/components/dashboard/VersionSwitcher";
import { ReplaceVersionDialog } from "@/components/dashboard/ReplaceVersionDialog";
import {
  ApiRequestError,
  apiGetVid,
  apiGenerateVid,
  getDownloadVidMp4Url,
  getDownloadVidUrl,
  getDownloadVidSrtUrl,
} from "@/lib/api";
import type { VidOutput } from "@/lib/types";

interface VidTabProps {
  courseId: string;
  /** True while the course's document is still being extracted/indexed — generating now
   * would hit the backend's "still processing" guard, so the button is disabled instead. */
  documentProcessing?: boolean;
}

function formatDuration(totalSeconds?: number | null): string {
  const s = Math.max(0, Math.round(totalSeconds || 0));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export function VidTab({ courseId, documentProcessing = false }: VidTabProps) {
  // Generation config
  const [format, setFormat] = useState("standard");
  const [voice, setVoice] = useState("female");
  const [userPrompt, setUserPrompt] = useState("");
  const [regenError, setRegenError] = useState<string | null>(null);
  const [regenDialogOpen, setRegenDialogOpen] = useState(false);
  const [replaceDialogOpen, setReplaceDialogOpen] = useState(false);

  const [downloadMenuOpen, setDownloadMenuOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const stageRef = useRef<HTMLDivElement>(null);
  const downloadMenuRef = useRef<HTMLDivElement>(null);

  const {
    data: video,
    hasFetched,
    error,
    setError,
    generating,
    setGenerating,
    progress,
    setProgress,
    regenUsed,
    setRegenUsed,
    regenMax,
    setRegenMax,
    startPolling,
    versions,
    activeVersion,
    viewedVersion,
    switchVersion,
  } = usePollingArtifact<VidOutput>({
    courseId,
    fetchFn: apiGetVid,
    isReady: (data) => (data.scenes?.length ?? 0) > 0,
    timeoutMs: 8 * 60 * 1000,
    timeoutMessage: "Quá trình tạo video mất nhiều thời gian hơn dự kiến. Vui lòng thử lại sau.",
    defaultErrorMessage: "Tạo video thất bại.",
  });

  const loading = !hasFetched && !error;

  // Close download menu on outside click
  useEffect(() => {
    if (!downloadMenuOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (downloadMenuRef.current && !downloadMenuRef.current.contains(e.target as Node)) {
        setDownloadMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [downloadMenuOpen]);

  // Keep isFullscreen in sync with the browser (Escape / back-gesture exits without our button).
  useEffect(() => {
    const onFsChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    setProgress(5);
    try {
      await apiGenerateVid(courseId, { format, voice, user_prompt: userPrompt });
      startPolling(Date.now());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bắt đầu tạo video thất bại.");
      setGenerating(false);
    }
  };

  // The backend persists a hard "error" status from the last generation attempt, so a plain
  // refetch would just surface the same error forever — retry opens the picker before a new job.
  const handleRetryAfterError = () => {
    setRegenDialogOpen(true);
  };

  // Regenerating from the ready view keeps the current video visible (stale-while-revalidate)
  // instead of bouncing to the full-page ErrorState/EmptyState — a 429 (regen limit reached)
  // surfaces as a small inline banner instead of blowing away otherwise-valid content.
  const handleRegenerate = async (replaceVersionId?: string) => {
    setRegenError(null);
    setGenerating(true);
    setProgress(5);
    try {
      const res = await apiGenerateVid(courseId, { format, voice, user_prompt: userPrompt, replace_version_id: replaceVersionId });
      if (typeof res.regen_used === "number") setRegenUsed(res.regen_used);
      if (typeof res.regen_max === "number") setRegenMax(res.regen_max);
      startPolling(Date.now());
    } catch (err) {
      if (err instanceof ApiRequestError && err.status === 409 && (err.detail as { code?: string })?.code === "version_cap_reached") setReplaceDialogOpen(true);
      setRegenError(err instanceof Error ? err.message : "Tạo lại thất bại.");
      setGenerating(false);
    }
  };

  const optionValue = { format, voice, userPrompt };
  const updateOptions = (value: typeof optionValue) => {
    setFormat(value.format);
    setVoice(value.voice);
    setUserPrompt(value.userPrompt);
  };
  const regenMaxDisplay = regenMax ?? 3;
  const regenRemainingDisplay = Math.max(0, regenMaxDisplay - (regenUsed ?? 0));
  const submitRegenerateFromDialog = () => {
    setRegenDialogOpen(false);
    if (error) {
      handleGenerate();
    } else {
      handleRegenerate();
    }
  };
  const regenerateDialog = (
    <Dialog open={regenDialogOpen} onOpenChange={setRegenDialogOpen}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Tạo lại video</DialogTitle>
          <DialogDescription>
            Chọn cấu hình mới rồi xác nhận để bắt đầu tạo. Nội dung hiện tại vẫn được giữ cho đến khi bản mới sẵn sàng.
          </DialogDescription>
        </DialogHeader>
        <VidOptionsPanel
          value={optionValue}
          onChange={updateOptions}
          onSubmit={submitRegenerateFromDialog}
          busy={generating}
          progress={progress}
          submitLabel="Tạo lại video"
          documentProcessing={documentProcessing}
        />
        <DialogFooter className="items-center sm:justify-between">
          <span className="text-xs font-medium text-muted-foreground">
            Còn {regenRemainingDisplay}/{regenMaxDisplay} lượt tạo
          </span>
          <Button variant="ghost" onClick={() => setRegenDialogOpen(false)}>
            Hủy
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );

  const toggleFullScreen = () => {
    if (!document.fullscreenElement) {
      stageRef.current?.requestFullscreen().catch((err) => {
        console.error("Error attempting to enable full-screen mode:", err);
      });
    } else {
      document.exitFullscreen();
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 py-6 animate-pulse">
        <div className="flex justify-between items-center">
          <Skeleton className="h-8 w-64 rounded-xl" />
          <div className="flex gap-2">
            <Skeleton className="h-10 w-32 rounded-xl" />
            <Skeleton className="h-10 w-36 rounded-xl" />
          </div>
        </div>
        <Skeleton className="aspect-video w-full rounded-2xl" />
      </div>
    );
  }

  if (error) {
    return (
      <>
        <ErrorState
          title="Lỗi tạo video"
          description={error}
          onRetry={handleRetryAfterError}
          retryLabel="Thử tạo lại"
        />
        {regenerateDialog}
      </>
    );
  }

  if (!video || !video.scenes || video.scenes.length === 0) {
    return (
      <EmptyState
        icon={Video}
        title="Chưa có video bài giảng"
        description="Hệ thống sẽ dựng một video ngắn có giọng đọc Tiếng Việt, tóm tắt và trình bày nội dung tài liệu của bạn theo từng phần."
        badge=""
      >
        <VidOptionsPanel
          value={optionValue}
          onChange={updateOptions}
          onSubmit={handleGenerate}
          busy={generating}
          progress={progress}
          submitLabel="Tạo video bài giảng"
          documentProcessing={documentProcessing}
        />
      </EmptyState>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in-50">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-card/40 p-5 rounded-2xl border shadow-[var(--shadow-xs)]">
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2 rounded-xl bg-primary/10 text-primary shrink-0">
            <Video className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h2 className="text-xl font-semibold text-foreground tracking-tight truncate">
              {video.title || "Video bài giảng"}
            </h2>
            <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="secondary" className="font-medium">
                {video.scenes.length} cảnh
              </Badge>
              <span>{formatDuration(video.total_duration_seconds)}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="relative" ref={downloadMenuRef}>
            <Button
              onClick={() => setDownloadMenuOpen((v) => !v)}
              variant="default"
              className="gap-1.5"
            >
              <Download className="h-4 w-4" />
              Tải xuống
              <ChevronDown className="h-3.5 w-3.5" />
            </Button>
            {downloadMenuOpen && (
              <div className="absolute right-0 top-full mt-1.5 w-48 rounded-xl border bg-card p-1 shadow-[var(--shadow-md)] z-10 animate-in fade-in-50">
                <a
                  href={getDownloadVidMp4Url(courseId, viewedVersion)}
                  target="_blank"
                  rel="noopener noreferrer"
                  download
                  onClick={() => setDownloadMenuOpen(false)}
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
                >
                  <Download className="h-3.5 w-3.5" /> Video (MP4)
                </a>
                <a
                  href={getDownloadVidUrl(courseId, viewedVersion)}
                  target="_blank"
                  rel="noopener noreferrer"
                  download
                  onClick={() => setDownloadMenuOpen(false)}
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
                >
                  <FileText className="h-3.5 w-3.5" /> Lời thoại (.txt)
                </a>
                <a
                  href={getDownloadVidSrtUrl(courseId, viewedVersion)}
                  target="_blank"
                  rel="noopener noreferrer"
                  download
                  onClick={() => setDownloadMenuOpen(false)}
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
                >
                  <FileText className="h-3.5 w-3.5" /> Phụ đề (.srt)
                </a>
              </div>
            )}
          </div>

          <Button onClick={toggleFullScreen} variant="outline" className="gap-1.5">
            <Maximize2 className="h-4 w-4" />
            <span className="hidden sm:inline">Toàn màn hình</span>
          </Button>

          {generating ? (
            <Button disabled variant="outline" className="gap-1.5">
              <RefreshCw className="h-4 w-4 animate-spin" /> Đang tạo lại ({progress}%)…
            </Button>
          ) : (
            <RegenerateButton
              label="video"
              regenUsed={regenUsed}
              regenMax={regenMax}
              onOpen={() => {
                setRegenError(null);
                setRegenDialogOpen(true);
              }}
            />
          )}
        </div>
      </div>

      <VersionSwitcher versions={versions} activeVersion={activeVersion} viewedVersion={viewedVersion} onSwitch={switchVersion} />

      {regenError && (
        <div className="flex items-center justify-between gap-3 rounded-xl border border-error/40 bg-error/5 px-4 py-3 text-sm text-error">
          <span>{regenError}</span>
          <button onClick={() => setRegenError(null)} className="shrink-0 font-semibold hover:underline">
            Đóng
          </button>
        </div>
      )}

      {regenerateDialog}
      <ReplaceVersionDialog open={replaceDialogOpen} versions={versions} onOpenChange={setReplaceDialogOpen} onConfirm={(versionId) => { setReplaceDialogOpen(false); handleRegenerate(versionId); }} />

      {/* Player stage */}
      <div
        ref={stageRef}
        className="w-full bg-stage border border-stage-border rounded-2xl shadow-2xl relative overflow-hidden text-stage-foreground flex items-center justify-center p-2 sm:p-4"
      >
        {isFullscreen && (
          <button
            onClick={toggleFullScreen}
            className="absolute top-4 right-4 z-10 p-2 rounded-lg bg-stage-muted hover:bg-stage-border text-stage-foreground transition-colors"
            title="Thoát toàn màn hình"
          >
            <X className="h-5 w-5" />
          </button>
        )}
        <video
          key={courseId}
          controls
          className={cn(
            "max-w-full rounded-lg",
            isFullscreen ? "max-h-screen" : "max-h-[70vh]"
          )}
          src={getDownloadVidMp4Url(courseId, viewedVersion)}
        />
      </div>
    </div>
  );
}
