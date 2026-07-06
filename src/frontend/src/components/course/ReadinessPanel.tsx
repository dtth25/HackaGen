"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  CircleSlash,
  Loader2,
  Sparkles,
  Target,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { generateFallbackOutput, getCourseReadiness, type GenerationReadinessReport } from "@/lib/api";

type OutputKey = "book" | "course" | "slides" | "video" | "quiz" | "flashcards" | "mindmap";

const OUTPUT_LABELS: Record<OutputKey, string> = {
  book: "Sách",
  course: "Lộ trình khóa học",
  slides: "Slides",
  video: "Video",
  quiz: "Quiz",
  flashcards: "Flashcards",
  mindmap: "Mindmap",
};

const OUTPUT_ORDER: OutputKey[] = ["book", "course", "slides", "video", "quiz", "flashcards", "mindmap"];

const STATUS_META: Record<string, { label: string; className: string; icon: React.ReactNode }> = {
  ready: {
    label: "Có thể tạo đầy đủ",
    className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    icon: <CheckCircle2 className="h-4 w-4" />,
  },
  limited: {
    label: "Chỉ đủ để tạo bản rút gọn",
    className: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400",
    icon: <AlertTriangle className="h-4 w-4" />,
  },
  not_enough_context: {
    label: "Chưa đủ dữ liệu",
    className: "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400",
    icon: <CircleSlash className="h-4 w-4" />,
  },
};

const FALLBACK_ACTIONS: Record<string, { type: string; label: string }> = {
  short_summary: { type: "summary", label: "Tạo bản tóm tắt thay thế" },
  short_60_second_script: { type: "summary", label: "Tạo video script 60 giây" },
  "3_basic_questions": { type: "summary", label: "Tạo vài câu hỏi ôn tập cơ bản" },
  summary_slides: { type: "summary", label: "Tạo slide tóm tắt" },
  high_yield_study_guide: { type: "high_yield", label: "Tạo bản học trọng tâm" },
  high_yield_course: { type: "high_yield", label: "Tạo lộ trình học trọng tâm" },
  short_outline: { type: "outline", label: "Tạo outline tài liệu" },
  storyboard_only: { type: "outline", label: "Tạo storyboard ngắn" },
  short_6_slide_overview: { type: "outline", label: "Tạo outline 6 slide" },
  shallow_concept_map: { type: "outline", label: "Tạo sơ đồ khái niệm đơn giản" },
  key_terms_only: { type: "key_terms", label: "Tạo flashcards thuật ngữ chính" },
};

const GENERIC_FALLBACKS: { type: string; label: string }[] = [
  { type: "summary", label: "Tạo bản tóm tắt ngắn" },
  { type: "high_yield", label: "Tạo bản học trọng tâm" },
  { type: "outline", label: "Tạo outline tài liệu" },
  { type: "key_terms", label: "Tạo flashcards thuật ngữ chính" },
];

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function FallbackResultView({ type, result }: { type: string; result: Record<string, unknown> }) {
  const list = (value: unknown) => (Array.isArray(value) ? value.filter((v) => typeof v === "string") : []);

  if (type === "summary") {
    const mainPoints = list(result.main_points);
    const keyTerms = list(result.key_terms);
    return (
      <div className="space-y-2 text-sm">
        {typeof result.summary === "string" && <p className="text-muted-foreground">{result.summary}</p>}
        {mainPoints.length > 0 && (
          <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
            {mainPoints.map((p, i) => <li key={i}>{p}</li>)}
          </ul>
        )}
        {keyTerms.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {keyTerms.map((t, i) => (
              <span key={i} className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">{t}</span>
            ))}
          </div>
        )}
        {typeof result.limitations === "string" && result.limitations && (
          <p className="pt-1 text-xs italic text-muted-foreground">{result.limitations}</p>
        )}
      </div>
    );
  }

  if (type === "high_yield") {
    const coreIdeas = list(result.core_ideas);
    const mustKnow = list(result.must_know_points);
    const questions = list(result.quick_review_questions);
    return (
      <div className="space-y-2 text-sm">
        {coreIdeas.length > 0 && (
          <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
            {coreIdeas.map((p, i) => <li key={i}>{p}</li>)}
          </ul>
        )}
        {mustKnow.length > 0 && (
          <div>
            <div className="text-xs font-semibold text-foreground">Phải nhớ:</div>
            <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
              {mustKnow.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </div>
        )}
        {questions.length > 0 && (
          <div>
            <div className="text-xs font-semibold text-foreground">Câu hỏi tự kiểm tra:</div>
            <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
              {questions.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </div>
        )}
      </div>
    );
  }

  if (type === "outline") {
    const topics = list(result.detected_topics);
    const sections = Array.isArray(result.possible_sections) ? result.possible_sections : [];
    return (
      <div className="space-y-2 text-sm">
        {topics.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {topics.map((t, i) => (
              <span key={i} className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">{t}</span>
            ))}
          </div>
        )}
        {sections.length > 0 && (
          <ol className="list-decimal space-y-1.5 pl-5 text-muted-foreground">
            {sections.map((s, i) => {
              const section = isObject(s) ? s : {};
              return (
                <li key={i}>
                  <span className="font-medium text-foreground">{typeof section.heading === "string" ? section.heading : `Phần ${i + 1}`}</span>
                  {typeof section.summary === "string" && <p className="text-xs">{section.summary}</p>}
                </li>
              );
            })}
          </ol>
        )}
        {typeof result.missing_context_warning === "string" && result.missing_context_warning && (
          <p className="pt-1 text-xs italic text-muted-foreground">{result.missing_context_warning}</p>
        )}
      </div>
    );
  }

  // key_terms
  const terms = Array.isArray(result.terms) ? result.terms : [];
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {terms.map((t, i) => {
        const term = isObject(t) ? t : {};
        return (
          <div key={i} className="rounded-lg border bg-background p-2.5 text-sm">
            <div className="font-semibold text-primary">{typeof term.term === "string" ? term.term : `Thuật ngữ ${i + 1}`}</div>
            {typeof term.definition === "string" && <p className="mt-0.5 text-xs text-muted-foreground">{term.definition}</p>}
          </div>
        );
      })}
    </div>
  );
}

export function ReadinessPanel({ courseId }: { courseId: string }) {
  const [readiness, setReadiness] = useState<GenerationReadinessReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fallbackBusy, setFallbackBusy] = useState<string | null>(null);
  const [fallbackResults, setFallbackResults] = useState<Record<string, Record<string, unknown>>>({});
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!courseId) return;
      setLoading(true);
      setError(null);
      try {
        const data = await getCourseReadiness(courseId);
        if (!cancelled) setReadiness(data);
      } catch {
        if (!cancelled) setError("Chưa thể đánh giá độ sẵn sàng cho tài liệu này lúc này.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  const handleFallback = async (type: string, label: string) => {
    setFallbackBusy(type);
    try {
      const res = await generateFallbackOutput(courseId, type, label);
      const result = isObject(res?.result) ? res.result : isObject(res) ? res : {};
      setFallbackResults((prev) => ({ ...prev, [type]: result }));
      setExpanded(type);
      toast.success("Đã tạo bản dự phòng từ ngữ cảnh sạch hiện có.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không thể tạo bản dự phòng.");
    } finally {
      setFallbackBusy(null);
    }
  };

  if (!courseId) return null;

  if (loading) {
    return (
      <Card className="shadow-sm">
        <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Đang đánh giá độ sẵn sàng của tài liệu...
        </CardContent>
      </Card>
    );
  }

  if (error || !readiness) {
    return null;
  }

  return (
    <div className="space-y-4">
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Target className="h-4.5 w-4.5 text-emerald-600" />
            Output readiness — Phần nào có thể tạo ngay?
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {readiness.warnings.length > 0 && (
            <div className="space-y-1.5 rounded-lg border border-amber-500/25 bg-amber-500/5 p-3">
              {readiness.warnings.map((w, i) => (
                <p key={i} className="flex items-start gap-2 text-xs leading-5 text-amber-800 dark:text-amber-300">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  {w}
                </p>
              ))}
            </div>
          )}

          <div className="grid gap-2.5 sm:grid-cols-2">
            {OUTPUT_ORDER.map((key) => {
              const item = readiness.generation_readiness[key];
              if (!item) return null;
              const meta = STATUS_META[item.status] ?? STATUS_META.not_enough_context;
              const action = FALLBACK_ACTIONS[item.recommended_fallback];
              const isBusy = action && fallbackBusy === action.type;
              const isExpanded = action && expanded === action.type;
              const result = action ? fallbackResults[action.type] : undefined;

              return (
                <div key={key} className="rounded-xl border bg-background p-3.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold">{OUTPUT_LABELS[key]}</span>
                    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold", meta.className)}>
                      {meta.icon}
                      {meta.label}
                    </span>
                  </div>
                  <p className="mt-1.5 text-xs leading-5 text-muted-foreground">{item.reason}</p>
                  {action && item.status !== "ready" && (
                    <div className="mt-2.5">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={isBusy}
                        onClick={() => {
                          if (result) {
                            setExpanded(isExpanded ? null : action.type);
                          } else {
                            void handleFallback(action.type, action.label);
                          }
                        }}
                        className="h-7 gap-1.5 text-xs"
                      >
                        {isBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                        {result ? (isExpanded ? "Ẩn kết quả" : "Xem bản dự phòng") : action.label}
                        {result && <ChevronDown className={cn("h-3 w-3 transition-transform", isExpanded && "rotate-180")} />}
                      </Button>
                      {isExpanded && result && (
                        <div className="mt-2.5 rounded-lg border bg-muted/20 p-3">
                          <FallbackResultView type={action.type} result={result} />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {readiness.recommended_actions.length > 0 && (
            <ul className="space-y-1 border-t pt-3 text-xs leading-5 text-muted-foreground">
              {readiness.recommended_actions.map((a, i) => (
                <li key={i}>• {a}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardContent className="flex flex-wrap items-center gap-2 p-4">
          <span className="mr-1 text-xs font-semibold text-muted-foreground">Hoặc tạo nhanh học liệu dự phòng:</span>
          {GENERIC_FALLBACKS.map((item) => {
            const isBusy = fallbackBusy === item.type;
            return (
              <Button
                key={item.type}
                size="sm"
                variant="secondary"
                disabled={isBusy}
                onClick={() => {
                  setExpanded(item.type);
                  void handleFallback(item.type, item.label);
                }}
                className="h-7 gap-1.5 text-xs"
              >
                {isBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                {item.label}
              </Button>
            );
          })}
          <Link href="/generate">
            <Button size="sm" variant="ghost" className="h-7 text-xs">
              Chọn chủ đề cụ thể để tạo
            </Button>
          </Link>
          {(["summary", "high_yield", "outline", "key_terms"] as const).map((type) =>
            expanded === type && fallbackResults[type] ? (
              <div key={type} className="mt-2 w-full rounded-lg border bg-muted/20 p-3">
                <FallbackResultView type={type} result={fallbackResults[type]} />
              </div>
            ) : null,
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default ReadinessPanel;
