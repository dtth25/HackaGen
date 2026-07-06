"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  Award,
  Calculator,
  ChevronLeft,
  ChevronRight,
  Clock,
  Code,
  Download,
  FileText,
  GitBranch,
  Layers,
  MessageCircleQuestion,
  Mic,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { GenerateResponse } from "@/lib/api";
import {
  asArray,
  asString,
  DownloadLink,
  EmptyResult,
  isObject,
  MarkdownBlock,
  SourcesPanel,
  stripInternalMarkers,
  type PlainObject,
} from "./resultHelpers";

export default function SlideResultView({ result, documentId }: { result: GenerateResponse; documentId?: string }) {
  const slides = asArray(result.slides);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showNotes, setShowNotes] = useState(false);
  const current = isObject(slides[currentIndex]) ? slides[currentIndex] : {};
  const progress = slides.length ? ((currentIndex + 1) / slides.length) * 100 : 0;
  const visualType = asString(current.visual_type, "concept");
  const keyIdea = stripInternalMarkers(asString(current.key_idea), true);
  const note = stripInternalMarkers(asString(current.note ?? current.example), true);
  const speakerNotes = stripInternalMarkers(asString(current.speaker_notes), false);
  const studentPrompt = stripInternalMarkers(asString(current.student_prompt), true);
  const commonMistake = isObject(current.common_mistake) ? (current.common_mistake as PlainObject) : {};
  const generationStatus = isObject(result.generation_status) ? (result.generation_status as PlainObject) : {};
  const isLimited = generationStatus.status === "limited";

  // Rich screen_content extraction
  const screenContent = isObject(current.screen_content) ? (current.screen_content as PlainObject) : {};
  const bullets = asArray(screenContent.bullets ?? current.bullets);
  const formula = stripInternalMarkers(asString(screenContent.formula), true);
  const code = stripInternalMarkers(asString(screenContent.code), false);
  const table = asArray(screenContent.table);
  const diagramDesc = stripInternalMarkers(asString(screenContent.diagram_description), true);

  // Speaker notes word count & speaking time estimation
  const notesWordCount = speakerNotes ? speakerNotes.trim().split(/\s+/).length : 0;
  const estimatedSpeakMinutes = Math.max(1, Math.round(notesWordCount / 130));

  // Quality report metadata
  const qualityReport = isObject(result.quality_report) ? (result.quality_report as PlainObject) : {};
  const qualityScore = typeof qualityReport.quality_score === "number" ? qualityReport.quality_score : null;
  const isUniReady = qualityReport.is_university_ready === true;

  if (slides.length === 0) {
    return <EmptyResult message="Chưa có slide để hiển thị." />;
  }

  const hasRichContent = bullets.length > 0 || formula || code || table.length > 0 || diagramDesc;

  return (
    <section className="space-y-4">
      {isLimited && (
        <div className="flex items-start gap-2.5 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800/60 dark:bg-amber-950/20">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700 dark:text-amber-400" />
          <div>
            <div className="font-semibold text-amber-900 dark:text-amber-200">Bộ slide tổng quan ngắn (ngữ cảnh giới hạn)</div>
            <p className="mt-1 text-amber-800/90 dark:text-amber-300/90">
              {asString(
                generationStatus.reason,
                "Tài liệu chưa đủ ngữ cảnh sạch để tạo bộ slide bài giảng đầy đủ.",
              )}
            </p>
          </div>
        </div>
      )}

      <div className="rounded-lg border bg-card p-5 shadow-xs">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="mb-1.5 flex items-center gap-2 text-sm text-muted-foreground">
              <Layers className="h-4 w-4 text-primary" />
              <span>Slide {currentIndex + 1} / {slides.length}</span>
              {qualityScore !== null && (
                <span className={cn(
                  "ml-2 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium border",
                  qualityScore >= 85
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800"
                    : "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/30 dark:text-amber-300 dark:border-amber-800"
                )}>
                  <Award className="h-3 w-3" />
                  Điểm: {qualityScore}/100
                </span>
              )}
              {qualityReport.is_university_ready !== undefined && (
                <span className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium border",
                  isUniReady
                    ? "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/30 dark:text-blue-300 dark:border-blue-800"
                    : "bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700"
                )}>
                  <ShieldCheck className="h-3 w-3" />
                  {isUniReady ? "Chuẩn đại học" : "Đang tối ưu"}
                </span>
              )}
            </div>
            <h3 className="text-2xl font-semibold leading-tight text-foreground">
              {asString(current.title, `Slide ${currentIndex + 1}`)}
            </h3>
          </div>
          <div className="flex flex-wrap gap-2">
            <DownloadLink
              href={result.pptx_url}
              label="Tải PPTX"
              icon={<Download className="h-4 w-4" />}
              variant="default"
            />
          </div>
        </div>

        <Progress value={progress} className="mb-5 h-2" />
        <div className="grid min-h-[320px] gap-5 rounded-lg border bg-background p-5 md:grid-cols-[1fr_280px]">
          <div className="space-y-4">
            {keyIdea && (
              <div className="rounded-md border border-cyan-200 bg-cyan-50 px-3 py-2 text-sm font-medium leading-6 text-cyan-950 dark:border-cyan-800 dark:bg-cyan-950/30 dark:text-cyan-200">
                {keyIdea}
              </div>
            )}

            {/* Rich screen_content rendering */}
            {bullets.length > 0 && (
              <ul className="space-y-2 pl-1">
                {bullets.map((bullet, idx) => (
                  <li key={idx} className="flex items-start gap-2.5 text-sm md:text-base leading-relaxed text-foreground">
                    <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-primary" />
                    <span>{stripInternalMarkers(asString(bullet))}</span>
                  </li>
                ))}
              </ul>
            )}

            {!hasRichContent && (
              <MarkdownBlock content={asString(current.content, "")} />
            )}

            {formula && (
              <div className="rounded-lg border border-indigo-200 bg-indigo-50/60 p-4 dark:border-indigo-800/60 dark:bg-indigo-950/20">
                <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-800 dark:text-indigo-300">
                  <Calculator className="h-3.5 w-3.5" />
                  Công thức trọng tâm
                </div>
                <div className="font-mono text-base md:text-lg font-semibold text-indigo-950 dark:text-indigo-100 overflow-x-auto py-1">
                  {formula}
                </div>
              </div>
            )}

            {code && (
              <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-slate-100 shadow-inner overflow-x-auto">
                <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <Code className="h-3.5 w-3.5" />
                  Đoạn mã mẫu (Code)
                </div>
                <pre className="font-mono text-xs md:text-sm leading-relaxed overflow-x-auto">
                  <code>{code}</code>
                </pre>
              </div>
            )}

            {table.length > 0 && (
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-left text-sm">
                  {table.length > 0 && Array.isArray(table[0]) && (
                    <thead className="bg-muted/80 font-semibold text-foreground border-b border-border">
                      <tr>
                        {(table[0] as unknown[]).map((cell, cIdx) => (
                          <th key={cIdx} className="px-4 py-2.5">
                            {stripInternalMarkers(asString(cell))}
                          </th>
                        ))}
                      </tr>
                    </thead>
                  )}
                  <tbody className="divide-y divide-border">
                    {table.slice(Array.isArray(table[0]) ? 1 : 0).map((row, rIdx) => (
                      <tr key={rIdx} className={rIdx % 2 === 1 ? "bg-muted/20" : "bg-background"}>
                        {Array.isArray(row) ? (
                          (row as unknown[]).map((cell, cIdx) => (
                            <td key={cIdx} className="px-4 py-2.5 text-foreground/90">
                              {stripInternalMarkers(asString(cell))}
                            </td>
                          ))
                        ) : (
                          <td className="px-4 py-2.5 text-foreground/90">
                            {stripInternalMarkers(asString(row))}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {diagramDesc && (
              <div className="rounded-lg border border-teal-200 bg-teal-50/60 p-4 dark:border-teal-800/60 dark:bg-teal-950/20">
                <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-teal-800 dark:text-teal-300">
                  <GitBranch className="h-3.5 w-3.5" />
                  Sơ đồ / Trực quan hóa
                </div>
                <p className="text-sm leading-relaxed text-teal-950 dark:text-teal-100">
                  {diagramDesc}
                </p>
              </div>
            )}

            {note && (
              <p className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
                {note}
              </p>
            )}

            {Boolean(commonMistake.mistake) && (
              <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm leading-6 dark:border-rose-800 dark:bg-rose-950/30">
                <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-rose-800 dark:text-rose-300">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Sai lầm thường gặp
                </div>
                <p className="text-rose-950 dark:text-rose-200">
                  <span className="font-semibold">Sai: </span>
                  {stripInternalMarkers(asString(commonMistake.mistake))}
                </p>
                <p className="mt-1 text-rose-950 dark:text-rose-200">
                  <span className="font-semibold">Đúng: </span>
                  {stripInternalMarkers(asString(commonMistake.correction))}
                </p>
              </div>
            )}

            {studentPrompt && (
              <p className="flex items-start gap-2 rounded-md border border-violet-200 bg-violet-50 p-3 text-sm leading-6 text-violet-950 dark:border-violet-800 dark:bg-violet-950/30 dark:text-violet-200">
                <MessageCircleQuestion className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  <span className="font-semibold">Hỏi lớp: </span>
                  {studentPrompt}
                </span>
              </p>
            )}

            {speakerNotes && (
              <div className="pt-2 border-t border-border/60">
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setShowNotes((prev) => !prev)}
                    className="flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
                  >
                    <Mic className="h-3.5 w-3.5" />
                    {showNotes ? "Ẩn ghi chú giảng viên" : "Xem ghi chú giảng viên"}
                  </button>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground font-medium">
                    <span className="inline-flex items-center gap-1">
                      <FileText className="h-3 w-3" />
                      {notesWordCount} từ
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      ~{estimatedSpeakMinutes} phút nói
                    </span>
                  </div>
                </div>
                {showNotes && (
                  <p className="mt-2.5 rounded-md border bg-muted/40 p-3.5 text-sm leading-relaxed text-foreground/90 whitespace-pre-line shadow-inner">
                    {speakerNotes}
                  </p>
                )}
              </div>
            )}
          </div>
          <aside className="flex min-h-56 flex-col justify-between rounded-lg border bg-muted/30 p-4">
            <div>
              <div className="mb-3 inline-flex items-center gap-2 rounded-md bg-background px-2.5 py-1 text-xs font-semibold text-muted-foreground ring-1 ring-border">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                {visualType}
              </div>
              <p className="text-sm font-medium leading-6 text-foreground/80">
                {stripInternalMarkers(asString(current.image_suggestion, "Minh họa bám theo trọng tâm của slide."))}
              </p>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-[11px] text-muted-foreground">
              <span className="rounded-md bg-background px-2 py-1 ring-1 ring-border">Trọng tâm</span>
              <span className="rounded-md bg-background px-2 py-1 ring-1 ring-border">Ví dụ</span>
              <span className="rounded-md bg-background px-2 py-1 ring-1 ring-border">Visual</span>
            </div>
          </aside>
        </div>
        <SourcesPanel documentId={documentId} sourceChunkIds={current.source_chunk_ids} />

        <div className="mt-5 flex items-center justify-between gap-3">
          <button
            type="button"
            className={buttonVariants({ variant: "outline", size: "lg" })}
            onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
            disabled={currentIndex === 0}
          >
            <ChevronLeft className="h-4 w-4" />
            Trước
          </button>
          <button
            type="button"
            className={buttonVariants({ variant: "outline", size: "lg" })}
            onClick={() =>
              setCurrentIndex((prev) => Math.min(slides.length - 1, prev + 1))
            }
            disabled={currentIndex === slides.length - 1}
          >
            Tiếp
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {slides.map((slide, index) => {
          const item = isObject(slide) ? slide : {};
          return (
            <button
              key={index}
              type="button"
              onClick={() => setCurrentIndex(index)}
              className={cn(
                "min-w-40 rounded-md border p-3 text-left text-xs transition-colors shrink-0",
                currentIndex === index
                  ? "border-primary bg-primary/10"
                  : "bg-card hover:bg-muted/60"
              )}
            >
              <div className="mb-1 font-semibold">Slide {index + 1}</div>
              <div className="line-clamp-2 text-muted-foreground">
                {asString(item.title, "Nội dung")}
              </div>
            </button>
          );
        })}
      </div>
      <SourcesPanel
        documentId={documentId}
        sourceChunkIds={result.quality_report?.source_chunk_ids}
        fallbackCount={result.quality_report?.usable_chunks_count || result.quality_report?.used_chunks}
      />
    </section>
  );
}
