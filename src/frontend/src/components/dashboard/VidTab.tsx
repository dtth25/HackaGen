"use client";

import { useEffect, useRef, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Video,
  Sparkles,
  RefreshCw,
  Download,
  FileText,
  Maximize2,
  X,
  ChevronDown,
  Smartphone,
  Film,
  MonitorPlay,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { cn } from "@/lib/utils";
import {
  apiGetVid,
  apiGenerateVid,
  getDownloadVidMp4Url,
  getDownloadVidUrl,
  getDownloadVidSrtUrl,
} from "@/lib/api";
import type { VidOutput } from "@/lib/types";

interface VidTabProps {
  courseId: string;
}

const FORMAT_OPTIONS: { value: string; label: string; hint: string; icon: LucideIcon }[] = [
  { value: "shorts", label: "Shorts", hint: "9:16 · 30-60s", icon: Smartphone },
  { value: "overview", label: "Tổng quan", hint: "16:9 · 2-3 phút", icon: Film },
  { value: "standard", label: "Tiêu chuẩn", hint: "16:9 · 5-7 phút", icon: MonitorPlay },
];

const VOICE_OPTIONS: { value: string; label: string }[] = [
  { value: "female", label: "Giọng nữ" },
  { value: "male", label: "Giọng nam" },
];

function formatDuration(totalSeconds?: number | null): string {
  const s = Math.max(0, Math.round(totalSeconds || 0));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export function VidTab({ courseId }: VidTabProps) {
  const [video, setVideo] = useState<VidOutput | null>(null);
  const [hasFetched, setHasFetched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);

  // Generation config
  const [format, setFormat] = useState("standard");
  const [voice, setVoice] = useState("female");
  const [userPrompt, setUserPrompt] = useState("");

  const [downloadMenuOpen, setDownloadMenuOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const stageRef = useRef<HTMLDivElement>(null);
  const downloadMenuRef = useRef<HTMLDivElement>(null);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loading = !hasFetched && !error;

  const startPolling = (startedAt: number) => {
    const TIMEOUT_MS = 8 * 60 * 1000;
    const POLL_MS = 3000;

    const poll = async () => {
      try {
        const res = await apiGetVid(courseId);
        if (res.status === "ready" && res.data && res.data.scenes?.length > 0) {
          setVideo(res.data);
          setHasFetched(true);
          setGenerating(false);
          setProgress(100);
          return;
        }
        if (res.status === "error") {
          setError(res.error || "Tạo video thất bại.");
          setGenerating(false);
          return;
        }
        if (typeof res.progress === "number") setProgress(res.progress);
      } catch {
        // Ignore transient errors while the background job is still running.
      }
      if (Date.now() - startedAt > TIMEOUT_MS) {
        setError("Quá trình tạo video mất nhiều thời gian hơn dự kiến. Vui lòng thử lại sau.");
        setGenerating(false);
        return;
      }
      pollTimer.current = setTimeout(poll, POLL_MS);
    };

    pollTimer.current = setTimeout(poll, POLL_MS);
  };

  useEffect(() => {
    if (hasFetched) return;
    apiGetVid(courseId)
      .then((res) => {
        if (res.status === "ready" && res.data) {
          setVideo(res.data);
        } else if (res.status === "processing") {
          setGenerating(true);
          setProgress(res.progress ?? 5);
          startPolling(Date.now());
        } else if (res.status === "error") {
          setError(res.error || "Tạo video thất bại.");
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Không thể tải video bài giảng."))
      .finally(() => setHasFetched(true));

    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId, hasFetched]);

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
  // refetch would just surface the same error forever — retrying must kick off a new job.
  const handleRetryAfterError = () => {
    setError(null);
    handleGenerate();
  };

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
      <ErrorState
        title="Lỗi tạo video"
        description={error}
        onRetry={handleRetryAfterError}
        retryLabel="Thử tạo lại"
      />
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
        <div className="w-full max-w-md space-y-5 rounded-2xl border bg-card/40 p-5 text-left shadow-[var(--shadow-xs)]">
          <div className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Định dạng
            </span>
            <div className="grid grid-cols-3 gap-2">
              {FORMAT_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                return (
                  <button
                    key={opt.value}
                    onClick={() => setFormat(opt.value)}
                    disabled={generating}
                    className={cn(
                      "flex flex-col items-center gap-1 rounded-lg border py-3 text-xs font-semibold transition-colors",
                      format === opt.value
                        ? "border-primary bg-primary/10 text-primary shadow-[var(--shadow-xs)]"
                        : "border-border/60 text-muted-foreground hover:border-primary/40 hover:text-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {opt.label}
                    <span className="text-[10px] font-normal opacity-80">{opt.hint}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Giọng đọc
            </span>
            <div className="grid grid-cols-2 gap-2">
              {VOICE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setVoice(opt.value)}
                  disabled={generating}
                  className={cn(
                    "rounded-lg border py-2 text-sm font-semibold transition-colors",
                    voice === opt.value
                      ? "border-primary bg-primary/10 text-primary shadow-[var(--shadow-xs)]"
                      : "border-border/60 text-muted-foreground hover:border-primary/40 hover:text-foreground"
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Yêu cầu bổ sung (tuỳ chọn)
            </span>
            <textarea
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              disabled={generating}
              placeholder="Ví dụ: tập trung vào phần ứng dụng thực tế…"
              rows={2}
              className="w-full resize-none rounded-lg border border-border/60 bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none"
            />
          </div>

          {generating ? (
            <div className="space-y-2">
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <Button disabled size="lg" className="w-full gap-2 font-semibold">
                <RefreshCw className="h-5 w-5 animate-spin" /> Đang dựng video ({progress}%)…
              </Button>
            </div>
          ) : (
            <Button onClick={handleGenerate} size="lg" className="w-full gap-2 font-semibold">
              <Sparkles className="h-5 w-5" /> Tạo video bài giảng
            </Button>
          )}
        </div>
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
                  href={getDownloadVidMp4Url(courseId)}
                  target="_blank"
                  rel="noopener noreferrer"
                  download
                  onClick={() => setDownloadMenuOpen(false)}
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
                >
                  <Download className="h-3.5 w-3.5" /> Video (MP4)
                </a>
                <a
                  href={getDownloadVidUrl(courseId)}
                  target="_blank"
                  rel="noopener noreferrer"
                  download
                  onClick={() => setDownloadMenuOpen(false)}
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
                >
                  <FileText className="h-3.5 w-3.5" /> Lời thoại (.txt)
                </a>
                <a
                  href={getDownloadVidSrtUrl(courseId)}
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
        </div>
      </div>

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
          src={getDownloadVidMp4Url(courseId)}
        />
      </div>
    </div>
  );
}
