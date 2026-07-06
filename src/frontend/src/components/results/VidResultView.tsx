"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  FileText,
  HelpCircle,
  Layers,
  Lightbulb,
  ListChecks,
  ListVideo,
  Loader2,
  PlayCircle,
  RefreshCw,
} from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { assetUrl, type GenerateResponse, type VideoMode } from "@/lib/api";
import {
  asArray,
  asString,
  isObject,
  SourcesPanel,
  stripInternalMarkers,
  textList,
  type PlainObject,
} from "./resultHelpers";

const VIDEO_MODE_LABELS: Record<string, string> = {
  sixty_second: "Video 60 giây",
  three_minute: "Bài học 3 phút",
  ten_minute: "Bài giảng 10 phút",
  playlist_by_chapter: "Playlist theo chương",
};

export default function VidResultView({
  result,
  documentId,
  onRegenerate,
  isRegenerating,
  onGenerateMode,
  onRenderVideo,
}: {
  result: GenerateResponse;
  documentId?: string;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
  /** Called when the user picks a mode from the large-document recommendation. */
  onGenerateMode?: (mode: VideoMode, force?: boolean) => void;
  /** Called to render one planned playlist video as MP4. */
  onRenderVideo?: (videoIndex: number) => Promise<void> | void;
}) {
  const vid: PlainObject = isObject(result.vid) ? result.vid : {};
  const failed = vid.status === "failed";
  const isPlaylist = vid.video_mode === "playlist_by_chapter";
  const videoModeLabel = VIDEO_MODE_LABELS[asString(vid.video_mode)] || "";
  const rawVideos = asArray(vid.videos);
  const debugLog = asString(vid.debug_log);
  const [renderingIdx, setRenderingIdx] = useState<number | null>(null);

  const playlist =
    rawVideos.length > 0
      ? rawVideos
      : [
          {
            video_index: 1,
            full_title:
              asString(vid.course_title) ||
              asString(vid.filename, "Video bài giảng AI"),
            duration_minutes: asString(vid.duration_minutes, "3"),
            storyboard: asArray(vid.scenes),
            transcript: asString(vid.transcript),
            subtitles_srt: asString(vid.subtitles_srt),
            quick_quiz: asArray(vid.quick_quiz),
            url: vid.url,
          },
        ];

  const [selectedIdx, setSelectedIdx] = useState(0);
  const [activeTab, setActiveTab] = useState<
    "storyboard" | "transcript" | "quiz" | "sources" | "debug"
  >("storyboard");

  // Pagination for storyboard scenes to keep DOM lightweight
  const [activeSceneIdx, setActiveSceneIdx] = useState(0);

  const currentVideo = isObject(playlist[selectedIdx])
    ? (playlist[selectedIdx] as PlainObject)
    : {};
  const currentScenes = asArray(
    currentVideo.storyboard || currentVideo.scenes || vid.scenes
  );
  const currentUrl = assetUrl(asString(currentVideo.url || vid.url));
  const currentTranscript =
    asString(currentVideo.transcript) ||
    asString(vid.transcript) ||
    currentScenes
      .map((s) => (isObject(s) ? stripInternalMarkers(asString(s.voiceover)) : ""))
      .filter(Boolean)
      .join(" ");
  const currentSubtitles = asString(currentVideo.subtitles_srt) || asString(vid.subtitles_srt);
  const currentQuiz = asArray(currentVideo.quick_quiz || vid.quick_quiz);
  const sourceIds = Array.from(
    new Set(
      currentScenes.flatMap((scene) =>
        isObject(scene) ? asArray(scene.source_chunk_ids).map((item) => asString(item)).filter(Boolean) : [],
      ),
    ),
  );
  const rawError = asString(vid.error);
  const friendlyError = rawError
    ? rawError.length > 180 || /ffmpeg|traceback|error opening|invalid data/i.test(rawError)
      ? "Hệ thống gặp lỗi khi ghép video hoặc renderer. Vui lòng tạo lại video, hoặc thử topic cụ thể hơn."
      : rawError
    : "Video chưa được tạo. Vui lòng thử lại sau.";
  const tabs = [
    { key: "storyboard" as const, label: "Storyboard", icon: <ListChecks className="h-4 w-4" /> },
    { key: "transcript" as const, label: "Lời giảng", icon: <FileText className="h-4 w-4" /> },
    { key: "quiz" as const, label: "Quiz nhanh", icon: <HelpCircle className="h-4 w-4" /> },
    { key: "sources" as const, label: "Nguồn tham khảo", icon: <Layers className="h-4 w-4" /> },
  ];

  // Large/broad document: backend recommends a playlist instead of one compressed video.
  if (vid.status === "recommendation") {
    const options = asArray(vid.options).filter(isObject) as PlainObject[];
    return (
      <section className="space-y-4 rounded-xl border border-amber-200 bg-amber-50/50 p-5 dark:border-amber-900/50 dark:bg-amber-950/20">
        <div className="flex items-center gap-2 font-semibold text-amber-800 dark:text-amber-300">
          <ListVideo className="h-5 w-5 shrink-0" />
          <span>Nên tạo playlist cho tài liệu này</span>
        </div>
        <p className="text-sm text-amber-800/90 dark:text-amber-200/90">
          {asString(vid.message, "Tài liệu này có nhiều chương/chủ đề. Bạn nên tạo playlist theo chương hoặc chọn một chủ đề cụ thể.")}
        </p>
        {onGenerateMode && (
          <div className="flex flex-wrap gap-2">
            {options.map((opt, idx) => (
              <button
                key={idx}
                type="button"
                disabled={isRegenerating}
                onClick={() => onGenerateMode(asString(opt.video_mode, "playlist_by_chapter") as VideoMode, opt.force === true)}
                className={buttonVariants({ variant: idx === 0 ? "default" : "outline", size: "sm" })}
              >
                {asString(opt.label, "Tạo video")}
              </button>
            ))}
          </div>
        )}
      </section>
    );
  }

  if (failed && !currentUrl) {
    return (
      <section className="space-y-4 rounded-xl border border-rose-200 bg-rose-50/50 p-5 dark:border-rose-900/50 dark:bg-rose-950/20">
        <div className="flex items-center gap-2 font-semibold text-rose-800 dark:text-rose-300">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span>Quá trình tạo video chưa hoàn tất</span>
        </div>
        <p className="text-sm text-rose-700 dark:text-rose-400">{friendlyError}</p>
        {onRegenerate && (
          <button
            type="button"
            onClick={onRegenerate}
            disabled={isRegenerating}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            <RefreshCw className={cn("mr-2 h-4 w-4", isRegenerating && "animate-spin")} />
            Tạo lại Video
          </button>
        )}
      </section>
    );
  }

  const activeScene = isObject(currentScenes[activeSceneIdx]) ? currentScenes[activeSceneIdx] : {};
  const vTpl = asString(activeScene.visual_template || activeScene.scene_type, "concept_card");
  const screenText = asArray(activeScene.screen_text).map((line) => asString(line)).filter(Boolean);

  const handleRenderVideo = async (videoIndex: number) => {
    if (!onRenderVideo) return;
    setRenderingIdx(videoIndex);
    try {
      await onRenderVideo(videoIndex);
    } finally {
      setRenderingIdx(null);
    }
  };

  return (
    <section className="space-y-6">
      {(videoModeLabel || asString(vid.video_title)) && (
        <div className="flex flex-wrap items-center gap-2">
          {videoModeLabel && (
            <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
              {videoModeLabel}
            </span>
          )}
          {asString(vid.video_title) && (
            <span className="text-sm font-semibold text-foreground">{asString(vid.video_title)}</span>
          )}
        </div>
      )}

      {/* Playlist plan table: playlist mode plans videos first and renders MP4s on demand */}
      {isPlaylist && rawVideos.length > 0 && (
        <div className="overflow-hidden rounded-xl border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-3 py-2.5 font-semibold">#</th>
                <th className="px-3 py-2.5 font-semibold">Bài học</th>
                <th className="px-3 py-2.5 font-semibold">Thời lượng</th>
                <th className="px-3 py-2.5 font-semibold">Trạng thái</th>
                <th className="px-3 py-2.5 font-semibold text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {rawVideos.map((rawV, idx) => {
                const v = isObject(rawV) ? (rawV as PlainObject) : {};
                const videoIndex = Number(v.video_index ?? idx + 1);
                const isReady = v.status === "ready";
                const isRenderingThis = renderingIdx === videoIndex;
                return (
                  <tr
                    key={idx}
                    className={cn(
                      "cursor-pointer border-b last:border-0 transition-colors hover:bg-muted/30",
                      selectedIdx === idx && "bg-primary/5",
                    )}
                    onClick={() => setSelectedIdx(idx)}
                  >
                    <td className="px-3 py-2.5 text-muted-foreground">{videoIndex}</td>
                    <td className="px-3 py-2.5 font-medium text-foreground">
                      {asString(v.full_title || v.short_title, `Bài ${videoIndex}`)}
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground">
                      {asString(v.duration_minutes, "3")} phút
                    </td>
                    <td className="px-3 py-2.5">
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold",
                          isReady
                            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                            : "bg-muted text-muted-foreground",
                        )}
                      >
                        {isReady ? "Sẵn sàng" : "Đã lên kế hoạch"}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      {onRenderVideo && !isReady && (
                        <button
                          type="button"
                          disabled={renderingIdx !== null}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRenderVideo(videoIndex);
                          }}
                          className={buttonVariants({ variant: "outline", size: "sm" })}
                        >
                          {isRenderingThis ? (
                            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <PlayCircle className="mr-1.5 h-3.5 w-3.5" />
                          )}
                          {isRenderingThis ? "Đang xử lý" : "Tạo MP4"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Video Player */}
      {currentUrl && (
        <div className="overflow-hidden rounded-xl border bg-black shadow-lg">
          <video
            key={currentUrl}
            src={currentUrl}
            controls
            className="max-h-[480px] w-full"
          />
        </div>
      )}

      {/* Tabs */}
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2 border-b pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                "flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors",
                activeTab === tab.key
                  ? "border-primary text-primary font-semibold"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        <div className="rounded-xl border bg-card p-5 shadow-xs">
          {activeTab === "storyboard" && (
            <div className="space-y-4">
              {currentScenes.length > 0 ? (
                <div>
                  {/* Scene pagination bar to render only 1 scene at a time */}
                  <div className="mb-4 flex flex-wrap items-center gap-2 pb-3 border-b">
                    <span className="text-xs font-semibold text-muted-foreground mr-2">Chọn Cảnh (Scenes):</span>
                    {currentScenes.map((_, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setActiveSceneIdx(idx)}
                        className={cn(
                          "rounded-md px-3 py-1 text-xs font-medium transition-colors",
                          activeSceneIdx === idx
                            ? "bg-primary text-primary-foreground font-bold shadow-2xs"
                            : "bg-muted hover:bg-muted/80 text-muted-foreground"
                        )}
                      >
                        Cảnh {idx + 1}
                      </button>
                    ))}
                  </div>

                  {/* Active Scene Card */}
                  <div className="rounded-lg border bg-background/50 p-5 transition-all shadow-2xs">
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <span className="inline-flex items-center rounded bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
                        Cảnh {activeSceneIdx + 1} / {currentScenes.length}
                      </span>
                      <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                        {vTpl.replace(/_/g, " ")}
                      </span>
                    </div>
                    <h4 className="mb-2 text-lg font-semibold text-foreground">
                      {asString(activeScene.title, `Cảnh ${activeSceneIdx + 1}`)}
                    </h4>
                    {asString(activeScene.key_message) && (
                      <p className="mb-4 text-sm text-muted-foreground">{asString(activeScene.key_message)}</p>
                    )}
                    <div className="space-y-2">
                      {(screenText.length ? screenText : textList(activeScene.visual_text)).slice(0, 4).map((line, idx) => (
                        <div key={idx} className="rounded-md bg-muted/50 px-3 py-2 text-sm">
                          {line}
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2 pt-3 border-t">
                      <span>Loại hình: {asString(activeScene.scene_type, "concept").replace(/_/g, " ")}</span>
                      <span>Thời lượng: {asString(activeScene.duration_seconds, "20")} giây</span>
                    </div>
                    {asString(activeScene.animation_notes) && (
                      <p className="mt-3 flex items-start gap-1.5 rounded-md border bg-muted/30 p-2 text-xs text-muted-foreground">
                        <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                        {asString(activeScene.animation_notes)}
                      </p>
                    )}
                    <SourcesPanel documentId={documentId} sourceChunkIds={activeScene.source_chunk_ids} />
                  </div>
                </div>
              ) : (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  Chưa có dữ liệu storyboard cho video này.
                </p>
              )}
            </div>
          )}

          {activeTab === "transcript" && (
            <div className="space-y-4 leading-relaxed text-foreground">
              <h4 className="text-base font-semibold">Lời giảng và phụ đề</h4>
              {currentTranscript ? (
                <div className="space-y-3 rounded-lg border bg-muted/30 p-4 text-sm">
                  {currentTranscript.split("\n").map((para, pIdx) =>
                    para.trim() ? <p key={pIdx}>{para}</p> : null,
                  )}
                </div>
              ) : (
                <p className="italic text-muted-foreground">Chưa có dữ liệu transcript.</p>
              )}
              {currentSubtitles && (
                <details className="rounded-lg border bg-background p-4 text-xs">
                  <summary className="cursor-pointer font-semibold">Xem phụ đề SRT</summary>
                  <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-muted-foreground font-mono">
                    {currentSubtitles}
                  </pre>
                </details>
              )}
            </div>
          )}

          {activeTab === "quiz" && (
            <div className="space-y-4">
              <h4 className="mb-2 text-base font-semibold">Câu hỏi kiểm tra nhanh</h4>
              {currentQuiz.length > 0 ? (
                <div className="grid gap-3">
                  {currentQuiz.map((q, qIdx) => {
                    const qObj = isObject(q) ? q : { question: asString(q) };
                    return (
                      <div key={qIdx} className="rounded-lg border bg-background/50 p-4">
                        <p className="text-sm font-medium text-foreground">
                          Câu {qIdx + 1}: {asString(qObj.question || qObj.title, `Câu hỏi ${qIdx + 1}`)}
                        </p>
                        {asArray(qObj.options).length > 0 && (
                          <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                            {asArray(qObj.options).map((opt, oIdx) => (
                              <li key={oIdx}>{asString(opt)}</li>
                            ))}
                          </ul>
                        )}
                        {asString(qObj.explanation) && (
                          <p className="mt-3 flex items-start gap-1.5 rounded-md bg-muted/50 p-2 text-xs text-muted-foreground">
                            <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                            {asString(qObj.explanation)}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Video này chưa có quiz nhanh.</p>
              )}
            </div>
          )}

          {activeTab === "sources" && (
            <div className="space-y-4">
              <h4 className="text-base font-semibold">Nguồn RAG dùng để grounding ({sourceIds.length})</h4>
              {sourceIds.length > 0 ? (
                <SourcesPanel
                  documentId={documentId}
                  sourceChunkIds={sourceIds}
                  fallbackCount={sourceIds.length}
                />
              ) : (
                <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-300">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>Video này chưa có metadata nguồn đủ rõ để hiển thị trích đoạn.</span>
                </div>
              )}
            </div>
          )}

        </div>

        {debugLog && (
          <details className="rounded-lg border bg-background p-3 text-xs">
            <summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">
              Chi tiết kỹ thuật
            </summary>
            <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded bg-muted/50 p-3 font-mono text-muted-foreground">
              {debugLog}
            </pre>
          </details>
        )}
      </div>
    </section>
  );
}
