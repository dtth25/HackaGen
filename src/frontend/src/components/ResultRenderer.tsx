"use client";

import React, { type ReactNode } from "react";
import dynamic from "next/dynamic";
import {
  AlertTriangle,
  BookOpen,
  ClipboardCheck,
  FileVideo,
  Presentation,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import type { FeatureType } from "@/components/FeatureSelector";
import { QualityScoreBadge } from "@/components/ui";
import { type GenerateResponse } from "@/lib/api";
import { cn } from "@/lib/utils";
import { EmptyResult } from "./results/resultHelpers";

interface ResultRendererProps {
  feature: FeatureType;
  result: GenerateResponse;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
}

const LoadingSkeleton = () => (
  <div className="flex flex-col items-center justify-center rounded-lg border bg-card p-12 text-muted-foreground">
    <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
    <p className="text-sm">Đang nạp dữ liệu hiển thị...</p>
  </div>
);

// Dynamic lazy imports to prevent loading heavy AST/DOM trees when unopened
const BookResultView = dynamic(() => import("./results/BookResultView"), {
  loading: () => <LoadingSkeleton />,
  ssr: false,
});

const SlideResultView = dynamic(() => import("./results/SlideResultView"), {
  loading: () => <LoadingSkeleton />,
  ssr: false,
});

const QuizResultView = dynamic(() => import("./results/QuizResultView"), {
  loading: () => <LoadingSkeleton />,
  ssr: false,
});

const VidResultView = dynamic(() => import("./results/VidResultView"), {
  loading: () => <LoadingSkeleton />,
  ssr: false,
});

const featureMeta: Record<
  FeatureType,
  { title: string; icon: ReactNode; tone: string }
> = {
  book: {
    title: "Sách",
    icon: <BookOpen className="h-5 w-5" />,
    tone: "bg-sky-50 text-sky-700 ring-sky-200 dark:bg-sky-950/40 dark:text-sky-300 dark:ring-sky-800",
  },
  slide: {
    title: "Slide",
    icon: <Presentation className="h-5 w-5" />,
    tone: "bg-violet-50 text-violet-700 ring-violet-200 dark:bg-violet-950/40 dark:text-violet-300 dark:ring-violet-800",
  },
  quiz: {
    title: "Quiz",
    icon: <ClipboardCheck className="h-5 w-5" />,
    tone: "bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:ring-rose-800",
  },
  vid: {
    title: "Vid",
    icon: <FileVideo className="h-5 w-5" />,
    tone: "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:ring-amber-800",
  },
};

function collectSourceIds(value: unknown, output = new Set<string>()): string[] {
  if (Array.isArray(value)) {
    value.forEach((item) => collectSourceIds(item, output));
    return Array.from(output);
  }
  if (!value || typeof value !== "object") return Array.from(output);

  Object.entries(value as Record<string, unknown>).forEach(([key, entry]) => {
    if (key === "source_chunk_ids" && Array.isArray(entry)) {
      entry.forEach((id) => {
        if (typeof id === "string" && id.trim()) output.add(id.trim());
      });
      return;
    }
    if (typeof entry === "object") collectSourceIds(entry, output);
  });
  return Array.from(output);
}

export default function ResultRenderer({
  feature,
  result,
  onRegenerate,
  isRegenerating,
}: ResultRendererProps) {
  const meta = featureMeta[feature];
  const qualityReport = result.quality_report || (feature === "vid" ? result.vid?.quality_report : undefined);
  const documentId = result.course_id;
  const sourceCount =
    collectSourceIds(result).length ||
    qualityReport?.usable_chunks_count ||
    qualityReport?.used_chunks ||
    qualityReport?.retrieved_chunks_count ||
    0;

  const content = (() => {
    switch (feature) {
      case "book":
        return <BookResultView result={result} documentId={documentId} />;
      case "slide":
        return <SlideResultView result={result} documentId={documentId} />;
      case "quiz":
        return <QuizResultView result={result} documentId={documentId} />;
      case "vid":
        return (
          <VidResultView
            result={result}
            documentId={documentId}
            onRegenerate={onRegenerate}
            isRegenerating={isRegenerating}
          />
        );
      default:
        return <EmptyResult message="Output này chưa được hỗ trợ." />;
    }
  })();

  return (
    <div className="w-full space-y-5 transition-all">
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/60">
          <div className="flex items-center gap-3.5">
            <span className={cn("rounded-xl p-2.5 ring-1 shadow-sm", meta.tone)}>{meta.icon}</span>
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-foreground">{meta.title}</h2>
              <p className="text-xs text-muted-foreground">Kết quả được tạo tự động từ tài liệu của bạn</p>
            </div>
          </div>
          {qualityReport && (
            <div className="flex items-center gap-2">
              <QualityScoreBadge score={qualityReport.score} isUniversityReady={qualityReport.is_university_ready} />
            </div>
          )}
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="flex items-start gap-2.5 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-xs leading-5 text-emerald-800 dark:text-emerald-300">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            <span>
              Được tạo từ {sourceCount || "các"} đoạn nguồn trong tài liệu. Bạn có thể mở phần nguồn để kiểm tra excerpt gốc.
            </span>
          </div>
          <div className="flex items-start gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs leading-5 text-amber-800 dark:text-amber-300">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
            <span>Nội dung do AI tạo có thể có sai sót. Hãy kiểm tra lại thông tin quan trọng với tài liệu gốc.</span>
          </div>
        </div>

        {qualityReport && (qualityReport.can_generate === false || (qualityReport.warnings && qualityReport.warnings.length > 0)) && (
          <div className={cn(
            "rounded-xl border p-4 text-sm flex flex-col gap-2 shadow-sm",
            qualityReport.can_generate === false
              ? "bg-rose-500/10 border-rose-500/30 text-rose-800 dark:text-rose-300"
              : "bg-amber-500/10 border-amber-500/30 text-amber-800 dark:text-amber-300"
          )}>
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              <span>{qualityReport.can_generate === false ? "Cảnh báo chất lượng tài liệu:" : "Lưu ý kiểm tra nội dung:"}</span>
            </div>
            <ul className="list-disc pl-5 space-y-1 text-xs sm:text-sm">
              {qualityReport.warnings?.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
              {qualityReport.can_generate === false && (!qualityReport.warnings || qualityReport.warnings.length === 0) && (
                <li>Không đủ ngữ cảnh sạch để tạo học liệu chất lượng. Vui lòng dùng PDF rõ hơn hoặc bật OCR.</li>
              )}
            </ul>
          </div>
        )}

        {content}
      </section>
    </div>
  );
}
