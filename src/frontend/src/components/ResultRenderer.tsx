"use client";

import {
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  FileText,
  HelpCircle,
  Layers,
  ListChecks,
  Map,
  Presentation,
  Quote,
  Sparkles,
  StickyNote,
  Target,
} from "lucide-react";
import type { ReactNode } from "react";
import type { FeatureType } from "@/components/FeatureSelector";
import type { Citation, GenerateResponse } from "@/lib/api";
import type {
  Citation as MindMapCitation,
  MindMapData,
  MindMapNode,
} from "@/lib/mindmap/types";
import MindMapViewer from "@/components/mindmap/MindMapViewer";
import { cn } from "@/lib/utils";

type PlainObject = Record<string, unknown>;

interface ResultRendererProps {
  feature: FeatureType;
  result: GenerateResponse;
  citations: Citation[];
}

const featureMeta: Record<
  FeatureType,
  { title: string; icon: ReactNode; tone: string }
> = {
  course: {
    title: "Khóa học",
    icon: <BookOpen className="h-5 w-5" />,
    tone: "bg-blue-50 text-blue-700 ring-blue-200",
  },
  summary: {
    title: "Tóm tắt",
    icon: <FileText className="h-5 w-5" />,
    tone: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  },
  flashcards: {
    title: "Flashcard",
    icon: <StickyNote className="h-5 w-5" />,
    tone: "bg-amber-50 text-amber-700 ring-amber-200",
  },
  quiz: {
    title: "Quiz",
    icon: <HelpCircle className="h-5 w-5" />,
    tone: "bg-rose-50 text-rose-700 ring-rose-200",
  },
  slides: {
    title: "Slide",
    icon: <Presentation className="h-5 w-5" />,
    tone: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  },
  mindmap: {
    title: "Mind Map",
    icon: <Map className="h-5 w-5" />,
    tone: "bg-cyan-50 text-cyan-700 ring-cyan-200",
  },
  custom: {
    title: "Prompt riêng",
    icon: <Sparkles className="h-5 w-5" />,
    tone: "bg-violet-50 text-violet-700 ring-violet-200",
  },
};

function isObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown, fallback = "") {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function stripInternalMarkers(value: string, compact = true) {
  const cleaned = value
    .replace(/===\s*BẮT ĐẦU.*?===/giu, " ")
    .replace(/===\s*KẾT THÚC.*?===/giu, " ")
    .replace(/\[MÃ ĐỊNH DANH TRANG:\s*\d+\]/giu, " ")
    .replace(/\bNỘI DUNG:\s*/giu, " ")
    .replace(/\bMã định danh trang\s+\d+\s+nội dung\b/giu, " ");

  if (compact) {
    return cleaned.replace(/\s+/g, " ").trim();
  }

  return cleaned
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function markdownLines(content: string) {
  return stripInternalMarkers(content, false).replace(/\r/g, "").split("\n");
}

function MarkdownBlock({ content }: { content: string }) {
  const lines = markdownLines(content);
  const blocks: React.ReactNode[] = [];
  let listItems: string[] = [];
  let orderedItems: string[] = [];

  const flushList = () => {
    if (listItems.length > 0) {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="space-y-1 pl-5 text-sm leading-6">
          {listItems.map((item, index) => (
            <li key={`${item}-${index}`} className="list-disc">
              {item}
            </li>
          ))}
        </ul>
      );
      listItems = [];
    }

    if (orderedItems.length > 0) {
      blocks.push(
        <ol key={`ol-${blocks.length}`} className="space-y-1 pl-5 text-sm leading-6">
          {orderedItems.map((item, index) => (
            <li key={`${item}-${index}`} className="list-decimal">
              {item}
            </li>
          ))}
        </ol>
      );
      orderedItems = [];
    }
  };

  lines.forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) {
      flushList();
      return;
    }

    const headingMatch = /^(#{1,3})\s+(.+)$/.exec(line);
    if (headingMatch) {
      flushList();
      const level = headingMatch[1].length;
      const text = headingMatch[2].replace(/[*_`]/g, "");
      blocks.push(
        level === 1 ? (
          <h3 key={`h-${blocks.length}`} className="text-xl font-semibold leading-tight">
            {text}
          </h3>
        ) : (
          <h4 key={`h-${blocks.length}`} className="text-base font-semibold leading-tight">
            {text}
          </h4>
        )
      );
      return;
    }

    const bulletMatch = /^[-*]\s+(.+)$/.exec(line);
    if (bulletMatch) {
      orderedItems = [];
      listItems.push(bulletMatch[1].replace(/[*_`]/g, ""));
      return;
    }

    const orderedMatch = /^\d+[.)]\s+(.+)$/.exec(line);
    if (orderedMatch) {
      listItems = [];
      orderedItems.push(orderedMatch[1].replace(/[*_`]/g, ""));
      return;
    }

    flushList();
    blocks.push(
      <p key={`p-${blocks.length}`} className="text-sm leading-7 text-foreground/90">
        {line.replace(/[*_`]/g, "")}
      </p>
    );
  });

  flushList();

  return <div className="space-y-3">{blocks}</div>;
}

function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;

  return (
    <section className="mt-8 rounded-lg border bg-muted/30 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <Quote className="h-4 w-4" />
        Citations
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {citations.map((citation, index) => (
          <div
            key={`${citation.source}-${citation.chunk_id}-${index}`}
            className="rounded-md border bg-background p-3 text-xs"
          >
            <div className="font-semibold">Page {citation.page ?? "?"}</div>
            <div className="mt-1 truncate text-muted-foreground">
              {citation.source ?? "unknown"}
            </div>
            <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">
              chunk {citation.chunk_id ?? "?"}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function textList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => stripInternalMarkers(asString(item)))
      .filter(Boolean);
  }

  const text = stripInternalMarkers(asString(value), false);
  if (!text) return [];

  return text
    .split(/\n|;|•/)
    .map((item) => item.replace(/^[-*\d.)\s]+/, "").trim())
    .filter(Boolean);
}

function LessonList({
  title,
  icon,
  items,
}: {
  title: string;
  icon: ReactNode;
  items: string[];
}) {
  if (items.length === 0) return null;

  return (
    <div>
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
        {icon}
        {title}
      </div>
      <ul className="space-y-1 pl-5 text-sm leading-6 text-muted-foreground">
        {items.map((item, index) => (
          <li key={`${item}-${index}`} className="list-disc">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function renderCourse(result: GenerateResponse) {
  const course = isObject(result.course) ? result.course : result;
  const chapters = asArray(course.chapters ?? course.syllabus);
  const lessonCount = chapters.reduce<number>((total, chapter) => {
    const item = isObject(chapter) ? chapter : {};
    return total + asArray(item.lessons).length;
  }, 0);

  return (
    <section className="space-y-6">
      <div className="rounded-lg border bg-card p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h3 className="text-2xl font-semibold">
              {asString(course.title, "Khóa học từ tài liệu")}
            </h3>
            {Boolean(course.description) && (
              <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
                {asString(course.description)}
              </p>
            )}
          </div>
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-md bg-muted px-3 py-2">
              <div className="font-semibold">{chapters.length}</div>
              <div className="text-muted-foreground">Chương</div>
            </div>
            <div className="rounded-md bg-muted px-3 py-2">
              <div className="font-semibold">{lessonCount}</div>
              <div className="text-muted-foreground">Bài</div>
            </div>
            <div className="rounded-md bg-muted px-3 py-2">
              <div className="font-semibold">
                {asString(course.estimated_duration, "3-5 giờ")}
              </div>
              <div className="text-muted-foreground">Thời lượng</div>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {chapters.map((chapter, chapterIndex) => {
          const item = isObject(chapter) ? chapter : {};
          const lessons = asArray(item.lessons);
          return (
            <section key={chapterIndex} className="rounded-lg border bg-card">
              <div className="border-b p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground">
                    {chapterIndex + 1}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="font-semibold leading-snug">
                      {asString(item.title ?? item.chapter, `Chương ${chapterIndex + 1}`)}
                    </h4>
                    {Boolean(item.description) && (
                      <p className="mt-1 text-sm leading-6 text-muted-foreground">
                        {asString(item.description)}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="divide-y">
                {lessons.map((lesson, lessonIndex) => {
                  const lessonObj = isObject(lesson) ? lesson : {};
                  const title = asString(
                    lessonObj.title ?? lesson,
                    `Bài ${chapterIndex + 1}.${lessonIndex + 1}`
                  );
                  const objectives = textList(lessonObj.objectives);
                  const keyPoints = textList(lessonObj.key_points ?? lessonObj.keyPoints);
                  const assessment = textList(lessonObj.assessment);
                  const activity = asString(lessonObj.activity);
                  const duration = asString(lessonObj.duration);
                  const citation = isObject(lessonObj.citation) ? lessonObj.citation : null;

                  return (
                    <details
                      key={lessonIndex}
                      className="group"
                      open={chapterIndex === 0 && lessonIndex === 0}
                    >
                      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-4 hover:bg-muted/40">
                        <div className="min-w-0">
                          <div className="text-sm font-semibold leading-snug">{title}</div>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            {duration && (
                              <span className="inline-flex items-center gap-1">
                                <Clock className="h-3.5 w-3.5" />
                                {duration}
                              </span>
                            )}
                            {citation && (
                              <span>
                                Page {asString(citation.page, "?")} ·{" "}
                                {asString(citation.source, "source")}
                              </span>
                            )}
                          </div>
                        </div>
                        <span className="rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground group-open:hidden">
                          Mở
                        </span>
                        <span className="hidden rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground group-open:inline-flex">
                          Đóng
                        </span>
                      </summary>

                      <div className="space-y-5 px-4 pb-5">
                        <LessonList
                          title="Mục tiêu"
                          icon={<Target className="h-4 w-4" />}
                          items={objectives}
                        />

                        <div>
                          <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                            <BookOpen className="h-4 w-4" />
                            Nội dung bài giảng
                          </div>
                          <div className="rounded-lg bg-muted/40 p-4">
                            <MarkdownBlock
                              content={asString(
                                lessonObj.lecture ?? lessonObj.content,
                                "Chưa có nội dung bài giảng."
                              )}
                            />
                          </div>
                        </div>

                        <LessonList
                          title="Ý chính cần nhớ"
                          icon={<ListChecks className="h-4 w-4" />}
                          items={keyPoints}
                        />

                        {activity && (
                          <div>
                            <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                              <Sparkles className="h-4 w-4" />
                              Hoạt động học tập
                            </div>
                            <p className="rounded-lg border bg-background p-3 text-sm leading-6 text-muted-foreground">
                              {stripInternalMarkers(activity)}
                            </p>
                          </div>
                        )}

                        <LessonList
                          title="Kiểm tra nhanh"
                          icon={<ClipboardCheck className="h-4 w-4" />}
                          items={assessment}
                        />
                      </div>
                    </details>
                  );
                })}
                {lessons.length === 0 && (
                  <div className="p-4 text-sm text-muted-foreground">
                    Chương này chưa có bài học chi tiết.
                  </div>
                )}
                </div>
            </section>
          );
        })}
      </div>
    </section>
  );
}

function renderSummary(result: GenerateResponse) {
  return (
    <section className="rounded-lg border bg-card p-5">
      <MarkdownBlock content={asString(result.summary ?? result.result)} />
    </section>
  );
}

function renderFlashcards(result: GenerateResponse) {
  const flashcards = asArray(result.flashcards);

  return (
    <section className="grid gap-3 md:grid-cols-2">
      {flashcards.map((card, index) => {
        const item = isObject(card) ? card : {};
        const citation = isObject(item.citation) ? item.citation : {};
        return (
          <div key={index} className="rounded-lg border bg-card p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Card {index + 1}
              </span>
              {Boolean(citation.page) && (
                <span className="rounded-full bg-muted px-2 py-1 text-xs">
                  p.{asString(citation.page)}
                </span>
              )}
            </div>
            <h4 className="font-semibold leading-snug">
              {asString(item.question, "Câu hỏi")}
            </h4>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              {stripInternalMarkers(asString(item.answer, "Chưa có đáp án"))}
            </p>
          </div>
        );
      })}
    </section>
  );
}

function optionEntries(options: unknown) {
  if (Array.isArray(options)) {
    return options.map((option, index) => ({
      key: String(index),
      label: String.fromCharCode(65 + index),
      value: asString(option),
    }));
  }

  if (isObject(options)) {
    return Object.entries(options).map(([key, value]) => ({
      key,
      label: key,
      value: asString(value),
    }));
  }

  return [];
}

function isCorrectOption(optionKey: string, optionLabel: string, correct: unknown) {
  if (typeof correct === "number") return optionKey === String(correct);
  const text = asString(correct).trim();
  return text === optionKey || text.toUpperCase() === optionLabel.toUpperCase();
}

function renderQuiz(result: GenerateResponse) {
  const questions = asArray(result.questions);

  return (
    <section className="grid gap-4">
      {questions.map((question, index) => {
        const item = isObject(question) ? question : {};
        const options = optionEntries(item.options);
        return (
          <div key={index} className="rounded-lg border bg-card p-4">
            <div className="mb-3 flex items-start gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground">
                {index + 1}
              </div>
              <h4 className="font-semibold leading-snug">
                {asString(item.question, "Câu hỏi")}
              </h4>
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              {options.map((option) => {
                const isCorrect = isCorrectOption(
                  option.key,
                  option.label,
                  item.correct ?? item.correct_answer
                );
                return (
                  <div
                    key={option.key}
                    className={cn(
                      "flex items-start gap-2 rounded-md border p-3 text-sm",
                      isCorrect
                        ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                        : "bg-background"
                    )}
                  >
                    <span className="font-semibold">{option.label}.</span>
                    <span className="leading-5">{stripInternalMarkers(option.value)}</span>
                    {isCorrect && <CheckCircle2 className="ml-auto h-4 w-4 shrink-0" />}
                  </div>
                );
              })}
            </div>

            {Boolean(item.explanation) && (
              <p className="mt-3 rounded-md bg-muted/50 p-3 text-sm leading-6 text-muted-foreground">
                {stripInternalMarkers(asString(item.explanation))}
              </p>
            )}
          </div>
        );
      })}
    </section>
  );
}

function renderSlides(result: GenerateResponse) {
  const slides = asArray(result.slides);

  return (
    <section className="grid gap-4 md:grid-cols-2">
      {slides.map((slide, index) => {
        const item = isObject(slide) ? slide : {};
        return (
          <div key={index} className="rounded-lg border bg-card p-4">
            <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Layers className="h-4 w-4" />
              Slide {index + 1}
            </div>
            <h4 className="mb-3 text-lg font-semibold leading-tight">
              {asString(item.title, `Slide ${index + 1}`)}
            </h4>
            <MarkdownBlock content={asString(item.content, "")} />
            {Boolean(item.image_suggestion) && (
              <p className="mt-4 rounded-md bg-muted/50 p-3 text-xs leading-5 text-muted-foreground">
                {asString(item.image_suggestion)}
              </p>
            )}
          </div>
        );
      })}
    </section>
  );
}

function normalizeMindMapCitation(citation: Citation): MindMapCitation {
  const page =
    typeof citation.page === "number"
      ? citation.page
      : Number.parseInt(asString(citation.page, "0"), 10) || 0;
  return {
    page,
    source: asString(citation.source, "unknown"),
    chunk_id: asString(citation.chunk_id, ""),
  };
}

function convertMindMapNode(
  node: unknown,
  path: string,
  fallbackCitations: MindMapCitation[]
): MindMapNode {
  const item = isObject(node) ? node : {};
  const label = stripInternalMarkers(
    asString(item.label ?? item.title, `Ý chính ${path}`)
  );
  const nodeCitations = asArray(item.citations)
    .filter(isObject)
    .map((citation) => normalizeMindMapCitation(citation as Citation));

  return {
    id: asString(item.id, `node-${path}`),
    label,
    citations: nodeCitations.length > 0 ? nodeCitations : fallbackCitations.slice(0, 1),
    children: asArray(item.children).map((child, index) =>
      convertMindMapNode(child, `${path}-${index + 1}`, fallbackCitations)
    ),
  };
}

function adaptMindMap(result: GenerateResponse, citations: Citation[]): MindMapData {
  const raw = result.mindmap;
  const fallbackCitations = citations.map(normalizeMindMapCitation);

  if (isObject(raw) && isObject(raw.root)) {
    const branches = asArray(raw.branches).map((branch, index) =>
      convertMindMapNode(branch, `branch-${index + 1}`, fallbackCitations)
    );
    const root = convertMindMapNode(raw.root, "root", fallbackCitations);
    root.children = root.children?.length ? root.children : branches;
    return { root, branches };
  }

  if (isObject(raw)) {
    const branches = asArray(raw.branches ?? raw.children).map((branch, index) =>
      convertMindMapNode(branch, `branch-${index + 1}`, fallbackCitations)
    );
    const root: MindMapNode = {
      id: "root",
      label: stripInternalMarkers(
        asString(raw.central_topic ?? raw.title ?? raw.label, "Tài liệu học tập")
      ),
      citations: fallbackCitations,
      children: branches,
    };
    return { root, branches };
  }

  return {
    root: {
      id: "root",
      label: "Tài liệu học tập",
      citations: fallbackCitations,
      children: [],
    },
    branches: [],
  };
}

function renderMindmap(result: GenerateResponse, citations: Citation[]) {
  const data = adaptMindMap(result, citations);
  return <MindMapViewer data={data} />;
}

function renderCustom(result: GenerateResponse) {
  return (
    <section className="rounded-lg border bg-card p-5">
      {Boolean(result.prompt_type) && (
        <div className="mb-4 inline-flex rounded-full bg-muted px-3 py-1 text-xs font-semibold">
          {asString(result.prompt_type)}
        </div>
      )}
      <MarkdownBlock content={asString(result.result ?? result.answer ?? result.summary)} />
    </section>
  );
}

function renderFallback(result: GenerateResponse) {
  return (
    <pre className="max-h-[520px] overflow-auto rounded-lg bg-muted p-4 text-xs leading-relaxed">
      {JSON.stringify(result, null, 2)}
    </pre>
  );
}

export default function ResultRenderer({
  feature,
  result,
  citations,
}: ResultRendererProps) {
  const meta = featureMeta[feature];

  const content = (() => {
    switch (feature) {
      case "course":
        return renderCourse(result);
      case "summary":
        return renderSummary(result);
      case "flashcards":
        return renderFlashcards(result);
      case "quiz":
        return renderQuiz(result);
      case "slides":
        return renderSlides(result);
      case "mindmap":
        return renderMindmap(result, citations);
      case "custom":
        return renderCustom(result);
      default:
        return renderFallback(result);
    }
  })();

  return (
    <div className="w-full max-w-5xl space-y-5">
      <section className="space-y-4">
        <div className="flex items-center gap-3">
          <span className={cn("rounded-md p-2 ring-1", meta.tone)}>{meta.icon}</span>
          <h2 className="text-xl font-semibold">{meta.title}</h2>
        </div>
        {content}
      </section>

      <CitationList citations={citations} />
    </div>
  );
}
