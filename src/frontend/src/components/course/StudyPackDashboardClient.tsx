"use client";

import React, { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  BookOpen,
  ChevronLeft,
  Download,
  FileText,
  BrainCircuit,
  Layers,
  Sparkles,
  CheckCircle2,
  HelpCircle,
  RotateCw,
  ArrowLeft,
  ArrowRight,
  ShieldCheck,
  Zap,
  Trash2,
  Loader2,
  XCircle,
  Filter,
  Presentation,
  FileVideo,
  Plus,
  FolderOpen,
  Eye,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui";
import { QualityScoreBadge } from "@/components/ui/QualityScoreBadge";
import { useSetDocumentTitle } from "@/components/layout/DocumentTitleContext";
import { SourcesPanel } from "@/components/results/resultHelpers";
import { cn } from "@/lib/utils";
import {
  assetUrl,
  deleteDocument,
  generateContent,
  getBook,
  getSlide,
  getStudyPack,
  getVid,
  getCourseStats,
  regenerateFlashcardDeck,
  regenerateMindmap,
  renderPlaylistVideo,
  type CourseStatsResponse,
  type VideoMode,
  type BookChapter,
  type BookLesson,
  type GenerateFeature,
  type GenerateResponse,
  type QuizQuestion,
  type StudyPackFlashcard,
  type StudyPackMindmapNode,
  type StudyPackResponse,
  type StudyPackSummaryItem,
} from "@/lib/api";

const SlideResultView = dynamic(() => import("../results/SlideResultView"), {
  loading: () => (
    <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
      <Loader2 className="mb-2 h-6 w-6 animate-spin text-primary" />
      <p className="text-sm">Đang tải Slide...</p>
    </div>
  ),
  ssr: false,
});

const VidResultView = dynamic(() => import("../results/VidResultView"), {
  loading: () => (
    <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
      <Loader2 className="mb-2 h-6 w-6 animate-spin text-primary" />
      <p className="text-sm">Đang tải Video...</p>
    </div>
  ),
  ssr: false,
});

interface StudyPackDashboardClientProps {
  courseId: string;
}

type FallbackChapter = {
  title?: string;
  lessons?: BookLesson[];
  sections?: BookLesson[];
};

type ActiveTab = "guide" | "mindmap" | "flashcards" | "summary" | "quiz" | "slides" | "video" | "grounding";
type StudyPackGenerateFeature = GenerateFeature | "mindmap" | "flashcards";
type FlashcardFilter = "all" | "known" | "unknown";

function collectSourceIdsFromValue(value: unknown, output = new Set<string>()): string[] {
  if (Array.isArray(value)) {
    value.forEach((item) => collectSourceIdsFromValue(item, output));
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
    if (typeof entry === "object") collectSourceIdsFromValue(entry, output);
  });
  return Array.from(output);
}

export function StudyPackDashboardClient({
  courseId,
}: StudyPackDashboardClientProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<ActiveTab>("guide");
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [slideData, setSlideData] = useState<GenerateResponse | null>(null);
  const [loadingSlide, setLoadingSlide] = useState(false);
  const [vidData, setVidData] = useState<GenerateResponse | null>(null);
  const [loadingVid, setLoadingVid] = useState(false);
  const [learningMode, setLearningMode] = useState<"normal" | "high_yield">("high_yield");
  const [generatingFeature, setGeneratingFeature] = useState<string | null>(null);
  const [videoMode, setVideoMode] = useState<VideoMode>("three_minute");
  const [videoChapter, setVideoChapter] = useState<string>("");

  const [studyPackPayload, setStudyPackPayload] = useState<StudyPackResponse | null>(null);
  const [loadStatus, setLoadStatus] = useState<"loading" | "ready" | "not_found" | "error">("loading");
  const [courseStats, setCourseStats] = useState<CourseStatsResponse | null>(null);

  const loadStudyPack = React.useCallback(async (): Promise<void> => {
    setLoadStatus((prev) => (prev === "ready" ? prev : "loading"));

    // Metadata-first: check cheap on-disk stats before paying for the heavy
    // combined study-pack fetch. A freshly uploaded document with nothing
    // generated yet would otherwise cost two guaranteed-404 round trips
    // (study-pack, then the book fallback) just to render an empty dashboard.
    let stats: CourseStatsResponse | null = null;
    try {
      stats = await getCourseStats(courseId);
      setCourseStats(stats);
    } catch {
      // Non-fatal — the full fetch below will surface a real error if needed.
    }
    const hasAnyGeneratedOutput = Boolean(
      stats && (stats.has_book || stats.has_quiz || stats.has_mindmap || stats.has_flashcards),
    );
    if (stats && !hasAnyGeneratedOutput) {
      setStudyPackPayload(null);
      setLoadStatus("ready");
      return;
    }

    try {
      const data = await getStudyPack(courseId);
      setStudyPackPayload(data);
      setLoadStatus("ready");
      return;
    } catch (err) {
      try {
        const bookData = await getBook(courseId);
        const { book } = bookData;
        const chapters = (book?.chapters || []) as FallbackChapter[];
        const summaryItems: StudyPackSummaryItem[] = [];
        const mindmapNodes: StudyPackMindmapNode[] = [];

        chapters.forEach((ch, cIdx) => {
          const cNode: StudyPackMindmapNode = { id: `c_${cIdx}`, label: ch.title, children: [] };
          (ch.lessons || ch.sections || []).forEach((sec, sIdx) => {
            cNode.children?.push({ id: `s_${cIdx}_${sIdx}`, label: sec.title });
            if (sec.lecture) {
              summaryItems.push({
                topic: sec.title,
                chapter: ch.title,
                content: sec.lecture.slice(0, 250).replace(/[.\s]+$/, "") + "…",
              });
            }
          });
          mindmapNodes.push(cNode);
        });

        setStudyPackPayload({
          course_id: courseId,
          study_pack: {
            title: book.title,
            book: book,
            summary: summaryItems,
            mindmap: { title: book.title, nodes: mindmapNodes },
            flashcards: [],
            quiz: [],
            quality_scores: { study_guide_pdf: 90 },
          },
        });
        setLoadStatus("ready");
      } catch (innerErr) {
        const is404 =
          (innerErr instanceof Error && innerErr.message.includes("404")) ||
          (err instanceof Error && err.message.includes("404"));
        setLoadStatus(is404 ? "not_found" : "error");
      }
    }
  }, [courseId]);

  useEffect(() => {
    void Promise.resolve().then(loadStudyPack);
  }, [loadStudyPack]);

  const pdfUrl = studyPackPayload?.study_pack?.book ? assetUrl(`/api/course/${courseId}/book.pdf`) : undefined;

  // In-flight guards live in refs, and the loading flags are NOT effect deps:
  // putting them in deps makes setLoading(true) re-run the effect, whose cleanup
  // then cancels the very fetch it just started (tab would hang on "Đang nạp...").
  const slideFetchRef = React.useRef(false);
  const vidFetchRef = React.useRef(false);
  useEffect(() => {
    let cancelled = false;
    if (activeTab === "slides" && !slideData && !slideFetchRef.current) {
      slideFetchRef.current = true;
      void Promise.resolve().then(async () => {
        setLoadingSlide(true);
        try {
          const res = await getSlide(courseId);
          if (!cancelled) setSlideData(res);
        } catch {
          // Ignore missing optional generated output.
        } finally {
          slideFetchRef.current = false;
          setLoadingSlide(false);
        }
      });
    }
    if (activeTab === "video" && !vidData && !vidFetchRef.current) {
      vidFetchRef.current = true;
      void Promise.resolve().then(async () => {
        setLoadingVid(true);
        try {
          const res = await getVid(courseId);
          if (!cancelled) setVidData(res);
        } catch {
          // Ignore missing optional generated output.
        } finally {
          vidFetchRef.current = false;
          setLoadingVid(false);
        }
      });
    }
    return () => { cancelled = true; };
  }, [activeTab, courseId, slideData, vidData]);

  // book/quiz go through the generic /generate/{feature} endpoint; mindmap/flashcards have
  // their own dedicated regenerate endpoints (no generic "generate" route exists for them).
  // Both refresh the shared study-pack payload afterwards so the new content shows up
  // through the same rendering path as data loaded on first visit.
  const handleGenerateAction = async (
    feature: StudyPackGenerateFeature,
    vidOptions?: { videoMode?: VideoMode; chapterId?: string; force?: boolean },
  ) => {
    setGeneratingFeature(feature);
    try {
      if (feature === "slide" || feature === "vid") {
        const prompt = feature === "slide" ? "slide bài giảng" : "video bài giảng";
        const res = await generateContent(feature, courseId, prompt, learningMode, feature === "vid" ? {
          videoMode: vidOptions?.videoMode ?? videoMode,
          chapterId: vidOptions?.chapterId ?? (videoChapter || undefined),
          force: vidOptions?.force,
        } : undefined);
        if (feature === "slide") {
          setSlideData(res);
          setActiveTab("slides");
        } else {
          setVidData(res);
          setActiveTab("video");
          if (res.vid?.status === "recommendation") {
            // Backend suggests a playlist for large documents — don't toast success yet.
            setGeneratingFeature(null);
            return;
          }
        }
      } else if (feature === "mindmap") {
        await regenerateMindmap(courseId);
        await loadStudyPack();
        setActiveTab("mindmap");
      } else if (feature === "flashcards") {
        await regenerateFlashcardDeck(courseId);
        await loadStudyPack();
        setActiveTab("flashcards");
      } else if (feature === "book" || feature === "quiz") {
        await generateContent(feature, courseId, "tổng quan", learningMode);
        await loadStudyPack();
        setActiveTab(feature === "book" ? "guide" : "quiz");
      }
      toast.success("Đã tạo xong.");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Tạo học liệu thất bại.");
    } finally {
      setGeneratingFeature(null);
    }
  };

  const handleDeleteDocument = async () => {
    setIsDeleting(true);
    try {
      await deleteDocument(courseId);
      toast.success("Đã xóa tài liệu và toàn bộ học liệu liên quan.");
      router.push("/course");
    } catch {
      toast.error("Không thể xóa tài liệu. Vui lòng thử lại sau.");
      setIsDeleting(false);
    }
  };

  const studyPack = studyPackPayload?.study_pack;

  const flashcards: StudyPackFlashcard[] = useMemo(() => studyPack?.flashcards || [], [studyPack?.flashcards]);
  const [currentCardIdx, setCurrentCardIdx] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  const flashcardStatusStorageKey = `studypack_flashcard_status_${courseId}`;
  const [cardStatus, setCardStatus] = useState<Record<string, "known" | "unknown">>({});
  const [cardFilter, setCardFilter] = useState<FlashcardFilter>("all");

  useEffect(() => {
    if (typeof window === "undefined") return;
    void Promise.resolve().then(() => {
      try {
        const raw = window.localStorage.getItem(flashcardStatusStorageKey);
        if (raw) setCardStatus(JSON.parse(raw));
      } catch {
        // Ignore
      }
    });
  }, [flashcardStatusStorageKey]);

  const cardKey = (card: StudyPackFlashcard, idx: number) => card.id || card.front || `card_${idx}`;

  const markCardStatus = (card: StudyPackFlashcard, idx: number, status: "known" | "unknown") => {
    setCardStatus((prev) => {
      const next = { ...prev, [cardKey(card, idx)]: status };
      if (typeof window !== "undefined") {
        try {
          window.localStorage.setItem(flashcardStatusStorageKey, JSON.stringify(next));
        } catch {
          // Ignore
        }
      }
      return next;
    });
  };

  const knownCount = flashcards.filter((c, i) => cardStatus[cardKey(c, i)] === "known").length;
  const unknownCount = flashcards.filter((c, i) => cardStatus[cardKey(c, i)] === "unknown").length;

  const filteredFlashcards = useMemo(
    () =>
      flashcards
        .map((card, idx) => ({ card, idx }))
        .filter(({ card, idx }) => {
          if (cardFilter === "all") return true;
          return cardStatus[cardKey(card, idx)] === cardFilter;
        }),
    [flashcards, cardFilter, cardStatus]
  );

  const quizQuestions: QuizQuestion[] = studyPack?.quiz || [];
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [submittedQuiz, setSubmittedQuiz] = useState<Record<number, boolean>>({});

  const book = studyPack?.book;
  // Book-first card state: "limited" means the generator honestly downgraded
  // (high-yield notes or summary) instead of producing a full study guide.
  const bookIsLimited = Boolean(
    book?.chapters?.length &&
      ((book?.generation_mode && book.generation_mode !== "full_book") ||
        book?.generation_status?.status === "limited"),
  );
  const bookQualityScore =
    typeof book?.quality_report?.score === "number" ? book.quality_report.score : undefined;
  const summaryItems: StudyPackSummaryItem[] = studyPack?.summary || [];
  const mindmap = studyPack?.mindmap || { nodes: [] };
  const mindmapNodes: StudyPackMindmapNode[] = mindmap.nodes || [];
  const mindmapNodeById = new Map<string, StudyPackMindmapNode>(
    mindmapNodes.filter((n) => n?.id).map((n) => [n.id as string, n])
  );
  const MAX_MINDMAP_PREVIEW = 4;
  const resolveMindmapChild = (
    child: StudyPackMindmapNode | string | undefined
  ): StudyPackMindmapNode | undefined => {
    if (!child) return undefined;
    return typeof child === "string" ? mindmapNodeById.get(child) : child;
  };
  const mindmapChapterNodes: StudyPackMindmapNode[] = mindmap.root?.children?.length
    ? mindmap.root.children
        .map(resolveMindmapChild)
        .filter((n): n is StudyPackMindmapNode => Boolean(n))
    : mindmapNodes.filter((n) => n.type === "chapter" || !n.parent_id || n.parent_id === "root");
  const mindmapPreviewChapters = mindmapChapterNodes.slice(0, MAX_MINDMAP_PREVIEW);
  const qualityScores = studyPack?.quality_scores || {};
  const grounding = studyPack?.grounding || {};
  const studyPackSourceIds = collectSourceIdsFromValue(studyPack);
  const groundingCount = grounding.num_chunks || studyPackSourceIds.length || courseStats?.num_chunks || 0;
  const currentEntry = filteredFlashcards[currentCardIdx];
  const currentFlashcard = currentEntry?.card;
  const currentFlashcardOriginalIdx = currentEntry?.idx ?? 0;

  useEffect(() => {
    if (currentCardIdx >= filteredFlashcards.length) {
      void Promise.resolve().then(() => setCurrentCardIdx(0));
    }
  }, [filteredFlashcards.length, currentCardIdx]);

  useSetDocumentTitle(studyPack?.title || book?.title || null);

  const totalChapters = book?.chapters?.length || mindmapChapterNodes.length || 0;
  const totalLessons = book?.chapters?.reduce(
    (sum: number, ch: BookChapter) => sum + (ch.sections?.length || ch.lessons?.length || 0),
    0
  ) || 0;
  const hasAnyStudyPack = Boolean(
    book?.chapters?.length || mindmapNodes.length || quizQuestions.length || flashcards.length || summaryItems.length
  );

  const handleNextCard = () => {
    setIsFlipped(false);
    setCurrentCardIdx((prev) => (filteredFlashcards.length ? (prev + 1) % filteredFlashcards.length : 0));
  };

  const handlePrevCard = () => {
    setIsFlipped(false);
    setCurrentCardIdx((prev) =>
      filteredFlashcards.length ? (prev - 1 + filteredFlashcards.length) % filteredFlashcards.length : 0
    );
  };

  const handleMarkCurrentCard = (status: "known" | "unknown") => {
    if (!currentFlashcard) return;
    markCardStatus(currentFlashcard, currentFlashcardOriginalIdx, status);
  };

  const handleSelectOption = (qIdx: number, oIdx: number) => {
    if (submittedQuiz[qIdx]) return;
    setSelectedAnswers((prev) => ({ ...prev, [qIdx]: oIdx }));
  };

  const handleCheckAnswer = (qIdx: number) => {
    setSubmittedQuiz((prev) => ({ ...prev, [qIdx]: true }));
  };

  if (loadStatus === "loading") {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Đang tải Study Pack...</p>
      </div>
    );
  }

  if (loadStatus === "not_found") {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
        <p className="text-sm text-muted-foreground">Không tìm thấy tài liệu này.</p>
        <Link href="/course" className="text-sm font-medium text-primary hover:underline">
          Quay lại danh sách tài liệu
        </Link>
      </div>
    );
  }

  if (loadStatus === "error") {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
        <p className="text-sm text-muted-foreground">Không thể tải Study Pack. Vui lòng thử lại sau.</p>
        <Link href="/course" className="text-sm font-medium text-primary hover:underline">
          Quay lại danh sách tài liệu
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12 w-full animate-in fade-in-50 duration-300">
      {/* Top navigation back link */}
      <div className="flex items-center justify-between border-b border-border/60 pb-3">
        <Link
          href="/course"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          Quay lại danh sách tài liệu
        </Link>
        <span className="text-xs font-semibold text-muted-foreground">
          Mã tài liệu: <span className="font-mono text-foreground">{courseId.slice(0, 8)}...</span>
        </span>
      </div>

      {/* 3-Panel Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_420px] xl:grid-cols-[300px_1fr_480px] gap-6 items-start w-full">
        {/* PANEL 1: LEFT - NGUỒN (SOURCES / DOCUMENTS) */}
        <div className="w-full space-y-5 rounded-2xl border border-border/80 bg-card/60 p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-border/60 pb-3">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
              <FolderOpen className="h-4 w-4 text-primary" />
              Nguồn
            </h2>
            <Link href="/generate">
              <Button size="sm" variant="outline" className="h-7 gap-1 px-2.5 text-xs font-semibold shadow-2xs">
                <Plus className="h-3.5 w-3.5" />
                Thêm tài liệu
              </Button>
            </Link>
          </div>

          <div className="space-y-3">
            <div className="rounded-xl border border-border/60 bg-muted/30 p-3.5 space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="h-4 w-4 shrink-0 text-primary" />
                  <span className="text-xs font-bold text-foreground truncate">
                    {studyPack?.title || book?.title || `Tài liệu ${courseId.slice(0, 8)}`}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1 border-t border-border/40 text-xs">
                <span className="text-muted-foreground font-medium">Trạng thái</span>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="h-3 w-3" /> Sẵn sàng
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">Điểm chất lượng</span>
                <QualityScoreBadge score={qualityScores.study_guide_pdf || courseStats?.quality_score || 92} />
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              className="w-full justify-center text-xs font-semibold h-9 shadow-2xs"
              onClick={() => setActiveTab("grounding")}
            >
              <Eye className="mr-1.5 h-3.5 w-3.5 text-primary" />
              Xem nguồn
            </Button>

            {/* Privacy & Trust notice */}
            <div className="rounded-xl border border-border/60 bg-muted/20 p-3 space-y-1.5 text-[11px] leading-relaxed text-muted-foreground">
              <div className="flex items-start gap-1.5">
                <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                <span>Tài liệu của bạn được giữ riêng tư.</span>
              </div>
              <div className="flex items-start gap-1.5">
                <Trash2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
                <span>Bạn có thể xóa tài liệu bất cứ lúc nào.</span>
              </div>
            </div>

            {/* Hidden Technical / Debug Info by Default */}
            <details className="group rounded-xl border border-border/60 bg-muted/20 p-3 text-xs transition-all">
              <summary className="cursor-pointer font-bold text-muted-foreground group-hover:text-foreground list-none flex items-center justify-between">
                <span>Chi tiết kỹ thuật</span>
                <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded font-normal text-muted-foreground">Ẩn mặc định</span>
              </summary>
              <div className="mt-3 space-y-2 text-muted-foreground border-t border-border/40 pt-2.5 text-[11px]">
                <div className="flex justify-between"><span>ID tài liệu:</span> <span className="font-mono text-foreground truncate max-w-[120px]">{courseId}</span></div>
                <div className="flex justify-between"><span>Số đoạn nguồn:</span> <span className="font-semibold text-foreground">{groundingCount || 0} chunk</span></div>
              </div>
            </details>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsDeleteDialogOpen(true)}
              className="w-full justify-center text-xs font-semibold text-destructive hover:bg-destructive/10 hover:text-destructive h-9"
            >
              <Trash2 className="mr-1.5 h-3.5 w-3.5" />
              Xóa tài liệu
            </Button>
          </div>
        </div>

        {/* PANEL 2: CENTER - KHÔNG GIAN HỌC TẬP (LEARNING WORKSPACE) */}
        <div className="w-full space-y-5">
          <div className="rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-primary/5 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">
                <Sparkles className="h-3.5 w-3.5" />
                Không gian học tập
              </span>
            </div>

            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
              {studyPack?.title || book?.title || courseId}
            </h1>

            {book?.description && (
              <p className="text-sm leading-relaxed text-muted-foreground">
                {book.description}
              </p>
            )}

            <div className="flex flex-wrap items-center gap-4 pt-2 text-xs font-semibold text-muted-foreground border-t border-border/60">
              <span className="inline-flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5 text-primary" />
                {totalChapters} chương
              </span>
              <span className="inline-flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-emerald-500" />
                {totalLessons} bài
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-amber-500" />
                {flashcards.length} flashcards
              </span>
            </div>
          </div>

          {/* Friendly Message & Suggested Actions */}
          <div className="rounded-2xl border border-primary/20 bg-primary/5 p-5 space-y-4 shadow-2xs">
            <div className="flex items-start gap-3.5">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary font-bold">
                <Zap className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-foreground">Tài liệu đã sẵn sàng để học tập</h3>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Bắt đầu với Sách, rồi tạo Mindmap, Quiz và Flashcards — tất cả dựa trên cùng nội dung đã phân tích từ tài liệu của bạn.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-primary/10 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-bold text-foreground">Chế độ học:</span>
                <button
                  onClick={() => setLearningMode(learningMode === "normal" ? "high_yield" : "normal")}
                  className={cn(
                    "rounded-lg px-2.5 py-1 font-bold transition-all border",
                    learningMode === "high_yield"
                      ? "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30"
                      : "bg-secondary text-muted-foreground border-border/80"
                  )}
                >
                  {learningMode === "high_yield" ? "Bản rút gọn" : "Bình thường"}
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveTab("mindmap")}
                  className="rounded-lg bg-background/90 px-3 py-1 font-semibold text-primary border border-primary/30 hover:bg-primary/10 transition-colors shadow-2xs"
                >
                  Khám phá Mindmap
                </button>
                <button
                  onClick={() => setActiveTab("quiz")}
                  className="rounded-lg bg-background/90 px-3 py-1 font-semibold text-foreground border border-border/80 hover:bg-secondary transition-colors shadow-2xs"
                >
                  Luyện Trắc nghiệm
                </button>
              </div>
            </div>
          </div>

          {/* PRIMARY: Study Guide Book — the core product output */}
          <div className="rounded-2xl border-2 border-primary/40 bg-card p-5 shadow-sm space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
                  {generatingFeature === "book" ? <Loader2 className="h-5 w-5 animate-spin" /> : <BookOpen className="h-5 w-5" />}
                </div>
                <div>
                  <h3 className="text-base font-bold text-foreground">Sách</h3>
                  <p className="text-xs text-muted-foreground">
                    Tài liệu học tiếng Việt có cấu trúc từ file của bạn — output chính của sản phẩm.
                  </p>
                </div>
              </div>
              <span
                className={cn(
                  "shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold",
                  generatingFeature === "book"
                    ? "bg-primary/10 text-primary"
                    : book?.chapters?.length
                      ? bookIsLimited
                        ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                        : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      : "bg-muted text-muted-foreground",
                )}
              >
                {generatingFeature === "book"
                  ? "Đang tạo"
                  : book?.chapters?.length
                    ? bookIsLimited
                      ? "Bản rút gọn"
                      : "Sẵn sàng"
                    : "Chưa tạo"}
              </span>
            </div>

            {book?.chapters?.length ? (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                {typeof bookQualityScore === "number" && (
                  <span className="inline-flex items-center gap-1.5">
                    Chất lượng sách: <QualityScoreBadge score={bookQualityScore} />
                  </span>
                )}
                {bookIsLimited && (
                  <span className="text-amber-600 dark:text-amber-400">
                    {book?.generation_mode === "high_yield_study_guide" ? "Sách học rút gọn" : "Bản tóm tắt từ trích đoạn gốc"}
                  </span>
                )}
              </div>
            ) : null}

            {bookIsLimited && (
              <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs leading-relaxed text-amber-700 dark:text-amber-300">
                Tài liệu chưa đủ ngữ cảnh để tạo sách đầy đủ. Đây là bản rút gọn — bạn có thể bấm
                &quot;Tạo lại&quot; sau khi bổ sung tài liệu rõ hơn hoặc khi hạn mức AI được làm mới.
              </p>
            )}

            {book?.chapters?.length ? (
              <div className="flex flex-wrap gap-2 pt-1">
                <Button size="sm" className="h-9 font-bold" onClick={() => setActiveTab("guide")}>
                  Xem sách
                </Button>
                {pdfUrl && (
                  <a href={pdfUrl} target="_blank" rel="noreferrer">
                    <Button size="sm" variant="outline" className="h-9 font-semibold">
                      <Download className="mr-1.5 h-4 w-4" />
                      Tải PDF
                    </Button>
                  </a>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  className="h-9 font-semibold"
                  disabled={generatingFeature === "book"}
                  onClick={() => handleGenerateAction("book")}
                >
                  <RotateCw className="mr-1.5 h-4 w-4" />
                  {generatingFeature === "book" ? "Đang tạo lại..." : "Tạo lại sách"}
                </Button>
              </div>
            ) : (
              <Button
                size="lg"
                className="w-full h-11 text-sm font-bold"
                disabled={generatingFeature === "book"}
                onClick={() => handleGenerateAction("book")}
              >
                {generatingFeature === "book" ? "Đang tạo sách..." : "Tạo sách"}
              </Button>
            )}
          </div>

          {/* SECONDARY: other study-pack outputs */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-foreground">Học liệu bổ sung</h3>
              <span className="text-xs text-muted-foreground">Bấm để xem hoặc tạo mới</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {([
                { id: "mindmap", label: "Tạo Mindmap", icon: BrainCircuit, desc: "Sơ đồ 3 cấp độ", feature: "mindmap", hasContent: mindmapNodes.length > 0 },
                { id: "quiz", label: "Tạo Quiz", icon: HelpCircle, desc: "Trắc nghiệm ôn luyện", feature: "quiz", hasContent: quizQuestions.length > 0 },
                { id: "flashcards", label: "Tạo Flashcards", icon: Layers, desc: "Thẻ lật ghi nhớ", feature: "flashcards", hasContent: flashcards.length > 0 },
                { id: "slides", label: "Tạo slide bài giảng", icon: Presentation, desc: "Bản trình chiếu PPTX", feature: "slide", hasContent: Boolean(slideData) },
                { id: "video", label: "Tạo Video", icon: FileVideo, desc: "Video giảng dạy MP4", feature: "vid", hasContent: Boolean(vidData) },
              ] as const).map((action) => {
                const Icon = action.icon;
                const isActive = activeTab === action.id;
                const isBusy = generatingFeature === action.feature;
                return (
                  <button
                    key={action.id}
                    disabled={isBusy}
                    onClick={() => {
                      if (action.hasContent) {
                        setActiveTab(action.id as ActiveTab);
                      } else {
                        handleGenerateAction(action.feature);
                      }
                    }}
                    className={cn(
                      "flex flex-col items-start rounded-2xl border p-4 text-left transition-all relative overflow-hidden",
                      isActive
                        ? "border-primary bg-primary/10 ring-2 ring-primary/20 shadow-sm"
                        : "border-border/80 bg-card/80 hover:border-primary/50 hover:bg-secondary/40"
                    )}
                  >
                    <div className="flex items-center justify-between w-full mb-2">
                      <div className={cn("rounded-xl p-2", isActive ? "bg-primary text-primary-foreground shadow-2xs" : "bg-secondary text-foreground")}>
                        {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
                      </div>
                      {isActive && <span className="h-2 w-2 rounded-full bg-primary" />}
                    </div>
                    <span className="text-sm font-bold text-foreground">{action.label}</span>
                    <span className="text-[11px] text-muted-foreground mt-0.5">{action.desc}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* PANEL 3: RIGHT - BỘ HỌC LIỆU (STUDY PACK / STUDIO) */}
        <div className="w-full space-y-4 rounded-2xl border border-border/80 bg-card/60 p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-border/60 pb-3.5">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-primary" />
              <h2 className="text-base font-bold text-foreground">Bộ học liệu</h2>
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-bold text-primary">
                7 phần
              </span>
            </div>
            {activeTab === "guide" && pdfUrl && (
              <a href={pdfUrl} target="_blank" rel="noreferrer">
                <Button size="sm" className="h-7 text-xs font-semibold shadow-2xs">
                  <Download className="mr-1.5 h-3.5 w-3.5" />
                  Tải PDF
                </Button>
              </a>
            )}
          </div>

          {hasAnyStudyPack ? (
            <>
          {/* Sub-navigation Tabs inside Right Panel */}
          <div className="flex flex-wrap gap-1.5 pb-2 border-b border-border/40">
            {[
              { id: "guide", label: "Sách" },
              { id: "mindmap", label: "Mindmap" },
              { id: "quiz", label: "Quiz" },
              { id: "flashcards", label: "Flashcards" },
              { id: "summary", label: "Bản rút gọn" },
              { id: "slides", label: "Slides" },
              { id: "video", label: "Video" },
              { id: "grounding", label: "Xem nguồn" },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id as ActiveTab)}
                className={cn(
                  "rounded-lg px-2.5 py-1 text-xs font-bold transition-all",
                  activeTab === t.id
                    ? "bg-primary text-primary-foreground shadow-2xs"
                    : "bg-secondary/60 text-muted-foreground hover:bg-secondary hover:text-foreground"
                )}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* RIGHT PANEL CONTENT BOX */}
          <div className="min-h-[460px] pt-1">
            {/* 1. STUDY GUIDE PDF VIEW */}
            {activeTab === "guide" && (
              <div className="space-y-4 animate-in fade-in-50 duration-300">
                {book?.chapters?.length ? (
                  <Accordion type="multiple" defaultValue={["chapter-0"]} className="w-full space-y-3">
                    {book.chapters.map((chapter: BookChapter, chIdx: number) => {
                      const sections = chapter.sections || chapter.lessons || [];
                      return (
                        <AccordionItem
                          key={chIdx}
                          value={`chapter-${chIdx}`}
                          className="rounded-xl border border-border/80 bg-card px-4 py-1 shadow-2xs"
                        >
                          <AccordionTrigger className="text-sm font-bold hover:no-underline py-3">
                            <div className="flex items-center gap-2.5 text-left">
                              <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary/10 text-xs font-bold text-primary">
                                {chIdx + 1}
                              </span>
                              <div>
                                <span>{chapter.title}</span>
                                <span className="ml-2 text-[11px] font-normal text-muted-foreground">
                                  ({sections.length} phần)
                                </span>
                              </div>
                            </div>
                          </AccordionTrigger>
                          <AccordionContent className="pt-1 pb-4">
                            <div className="space-y-3">
                              {chapter.description && (
                                <p className="text-xs leading-relaxed text-muted-foreground pl-8">
                                  {chapter.description}
                                </p>
                              )}
                              <div className="space-y-2.5 pl-2 md:pl-8">
                                {sections.map((sec: BookLesson, sIdx: number) => (
                                  <div
                                    key={sIdx}
                                    className="rounded-lg border border-border/60 bg-muted/30 p-3 text-xs space-y-1.5"
                                  >
                                    <h4 className="font-bold text-foreground">
                                      {sec.title || sec.short_name || `Phần ${sIdx + 1}`}
                                    </h4>
                                    {sec.content && (
                                      <p className="text-muted-foreground whitespace-pre-line leading-relaxed">
                                        {sec.content}
                                      </p>
                                    )}
                                    {sec.lecture && (
                                      <p className="text-muted-foreground whitespace-pre-line leading-relaxed">
                                        {sec.lecture}
                                      </p>
                                    )}
                                    <div className="pt-2">
                                      <SourcesPanel
                                        documentId={courseId}
                                        sourceChunkIds={sec.source_chunk_ids}
                                      />
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      );
                    })}
                  </Accordion>
                ) : (
                  <div className="rounded-xl border border-dashed p-8 text-center text-xs text-muted-foreground space-y-3">
                    <BookOpen className="mx-auto h-7 w-7 text-muted-foreground/60" />
                    <p className="font-bold text-foreground">Chưa có Sách cho tài liệu này</p>
                    <p>Tạo giáo trình học tập theo chương/bài từ tài liệu gốc.</p>
                    <Button
                      size="sm"
                      className="h-8 text-xs font-bold"
                      disabled={generatingFeature === "book"}
                      onClick={() => handleGenerateAction("book")}
                    >
                      {generatingFeature === "book" ? "Đang xử lý..." : "Tạo Sách ngay"}
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* 2. MINDMAP */}
            {activeTab === "mindmap" && (
              <div className="space-y-4 animate-in fade-in-50 duration-300">
                <div className="rounded-xl border border-border/80 bg-card p-4 space-y-3 shadow-2xs">
                  <div className="flex items-center justify-between border-b border-border/60 pb-3">
                    <div>
                      <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                        <BrainCircuit className="h-4 w-4 text-primary" />
                        Sơ Đồ Tư Duy Kiến Thức
                      </h3>
                      <p className="text-[11px] text-muted-foreground">
                        Cây cấu trúc 3 cấp độ (Root - Chapter - Lesson)
                      </p>
                    </div>
                    <Link
                      href={`/mindmap/${courseId}`}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground shadow-2xs hover:bg-primary/90 transition-all shrink-0"
                    >
                      <BrainCircuit className="h-3.5 w-3.5" />
                      Mở toàn màn hình
                    </Link>
                  </div>

                  <div className="space-y-2.5">
                    {mindmapPreviewChapters.length > 0 ? (
                      mindmapPreviewChapters.map((node, nIdx) => (
                        <div key={node.id || nIdx} className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs space-y-1">
                          <div className="flex items-center gap-2 font-bold text-foreground">
                            <span className="flex h-5 w-5 items-center justify-center rounded bg-primary/15 text-primary text-[10px]">
                              {nIdx + 1}
                            </span>
                            <span>{node.title || node.label || `Chương ${nIdx + 1}`}</span>
                          </div>
                          {(node.summary || node.core_idea) && (
                            <p className="text-muted-foreground line-clamp-2 pl-7 text-[11px]">
                              {node.summary || node.core_idea}
                            </p>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="p-6 text-center text-xs text-muted-foreground space-y-3">
                        <BrainCircuit className="mx-auto h-7 w-7 text-muted-foreground/60" />
                        <p className="font-bold text-foreground">Chưa có Mindmap cho tài liệu này</p>
                        <p>Cần có Sách trước để tạo sơ đồ tư duy 3 cấp độ.</p>
                        {book?.chapters?.length ? (
                          <Button
                            size="sm"
                            className="h-8 text-xs font-bold"
                            disabled={generatingFeature === "mindmap"}
                            onClick={() => handleGenerateAction("mindmap")}
                          >
                            {generatingFeature === "mindmap" ? "Đang xử lý..." : "Tạo Mindmap ngay"}
                          </Button>
                        ) : (
                          <Button size="sm" className="h-8 text-xs font-bold" onClick={() => setActiveTab("guide")}>
                            Tạo Sách trước
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 3. QUIZ PRACTICE */}
            {activeTab === "quiz" && (
              <div className="space-y-4 animate-in fade-in-50 duration-300">
                {quizQuestions.length > 0 ? (
                  <div className="space-y-4">
                    {quizQuestions.map((q, qIdx) => {
                      const selected = selectedAnswers[qIdx];
                      const isSubmitted = submittedQuiz[qIdx];
                      const correctIdx = q.correct !== undefined ? q.correct : 0;
                      const isCorrect = selected === correctIdx;

                      return (
                        <div key={qIdx} className="rounded-xl border border-border/80 bg-card p-4 text-xs space-y-3 shadow-2xs">
                          <div className="flex items-start gap-2.5 font-bold text-foreground">
                            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-primary text-[11px] text-primary-foreground">
                              {qIdx + 1}
                            </span>
                            <span>{q.question}</span>
                          </div>

                          <div className="space-y-1.5 pl-7">
                            {(q.options || []).map((opt: string, oIdx: number) => {
                              let optStyle = "border-border/80 bg-muted/20 hover:bg-muted/40";
                              if (isSubmitted) {
                                if (oIdx === correctIdx) {
                                  optStyle = "border-emerald-500 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-bold";
                                } else if (selected === oIdx) {
                                  optStyle = "border-rose-500 bg-rose-500/15 text-rose-700 dark:text-rose-300";
                                }
                              } else if (selected === oIdx) {
                                optStyle = "border-primary bg-primary/10 ring-1 ring-primary font-bold";
                              }

                              return (
                                <button
                                  key={oIdx}
                                  onClick={() => handleSelectOption(qIdx, oIdx)}
                                  className={cn("flex items-center gap-2.5 rounded-lg border p-2.5 text-left w-full transition-all", optStyle)}
                                >
                                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded border text-[10px] font-bold">
                                    {String.fromCharCode(65 + oIdx)}
                                  </span>
                                  <span>{opt}</span>
                                </button>
                              );
                            })}
                          </div>

                          <div className="flex items-center justify-between pl-7 pt-1">
                            {!isSubmitted ? (
                              <Button
                                size="sm"
                                disabled={selected === undefined}
                                onClick={() => handleCheckAnswer(qIdx)}
                                className="h-7 text-xs font-bold"
                              >
                                Kiểm tra đáp án
                              </Button>
                            ) : (
                              <div className="w-full rounded-lg bg-muted/40 border p-3 space-y-1">
                                <div className="font-bold text-xs">
                                  {isCorrect ? (
                                    <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                                      <CheckCircle2 className="h-3.5 w-3.5" /> Chính xác!
                                    </span>
                                  ) : (
                                    <span className="text-rose-600 dark:text-rose-400">
                                      Đáp án đúng là: {String.fromCharCode(65 + correctIdx)}
                                    </span>
                                  )}
                                </div>
                                {q.explanation && (
                                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                                    {q.explanation}
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed p-8 text-center text-xs text-muted-foreground space-y-3">
                    <HelpCircle className="mx-auto h-7 w-7 text-muted-foreground/60" />
                    <p className="font-bold text-foreground">Chưa có Quiz cho tài liệu này</p>
                    <p>Tạo câu hỏi trắc nghiệm ôn luyện từ tài liệu gốc.</p>
                    <Button
                      size="sm"
                      className="h-8 text-xs font-bold"
                      disabled={generatingFeature === "quiz"}
                      onClick={() => handleGenerateAction("quiz")}
                    >
                      {generatingFeature === "quiz" ? "Đang xử lý..." : "Tạo Quiz ngay"}
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* 4. FLASHCARDS */}
            {activeTab === "flashcards" && (
              <div className="space-y-4 animate-in fade-in-50 duration-300">
                {flashcards.length > 0 ? (
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-center gap-1.5 text-xs">
                      <Filter className="h-3.5 w-3.5 text-muted-foreground" />
                      {([
                        { id: "all", label: `Tất cả (${flashcards.length})` },
                        { id: "unknown", label: `Chưa thuộc (${unknownCount})` },
                        { id: "known", label: `Đã thuộc (${knownCount})` },
                      ] as const).map((f) => (
                        <button
                          key={f.id}
                          onClick={() => {
                            setCardFilter(f.id);
                            setCurrentCardIdx(0);
                            setIsFlipped(false);
                          }}
                          className={cn(
                            "rounded-full px-2.5 py-1 text-[11px] font-bold transition-colors",
                            cardFilter === f.id
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted text-muted-foreground hover:bg-muted/70"
                          )}
                        >
                          {f.label}
                        </button>
                      ))}
                    </div>

                    {filteredFlashcards.length === 0 ? (
                      <div className="rounded-xl border border-dashed p-8 text-center text-xs text-muted-foreground">
                        Không có thẻ nào khớp bộ lọc.
                      </div>
                    ) : (
                      <>
                        <div
                          onClick={() => setIsFlipped(!isFlipped)}
                          className="group perspective cursor-pointer"
                        >
                          <div
                            className={cn(
                              "relative flex min-h-[220px] flex-col items-center justify-center rounded-2xl border border-border/80 bg-gradient-to-b from-card to-card/90 p-6 text-center shadow-md transition-all select-none",
                              isFlipped ? "ring-2 ring-primary bg-primary/5" : ""
                            )}
                          >
                            <span className="absolute top-3 right-4 inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-[10px] font-bold text-muted-foreground">
                              <RotateCw className="h-2.5 w-2.5" />
                              {isFlipped ? "Mặt sau" : "Mặt trước"}
                            </span>
                            <h3 className="text-base md:text-lg font-bold text-foreground mt-3 max-w-sm">
                              {isFlipped ? currentFlashcard?.back : currentFlashcard?.front}
                            </h3>
                            <p className="absolute bottom-3 text-[10px] font-medium text-muted-foreground">
                              Nhấp để lật thẻ ({currentCardIdx + 1}/{filteredFlashcards.length})
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center justify-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleMarkCurrentCard("unknown")}
                            className="h-8 text-xs font-bold text-amber-600 border-amber-300"
                          >
                            <XCircle className="mr-1.5 h-3.5 w-3.5" /> Chưa thuộc
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleMarkCurrentCard("known")}
                            className="h-8 text-xs font-bold text-emerald-600 border-emerald-300"
                          >
                            <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" /> Đã thuộc
                          </Button>
                        </div>

                        <div className="flex items-center justify-between gap-2">
                          <Button variant="outline" size="sm" onClick={handlePrevCard} className="flex-1 h-8 text-xs font-bold">
                            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" /> Trước
                          </Button>
                          <Button size="sm" onClick={handleNextCard} className="flex-1 h-8 text-xs font-bold">
                            Tiếp <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed p-8 text-center text-xs text-muted-foreground space-y-3">
                    <Layers className="mx-auto h-7 w-7 text-muted-foreground/60" />
                    <p className="font-bold text-foreground">Chưa có Flashcards cho tài liệu này</p>
                    <p>Tạo thẻ ghi nhớ chủ động (active recall) từ tài liệu gốc.</p>
                    <Button
                      size="sm"
                      className="h-8 text-xs font-bold"
                      disabled={generatingFeature === "flashcards"}
                      onClick={() => handleGenerateAction("flashcards")}
                    >
                      {generatingFeature === "flashcards" ? "Đang xử lý..." : "Tạo Flashcards ngay"}
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* 5. SUMMARY (BẢN RÚT GỌN) */}
            {activeTab === "summary" && (
              <div className="space-y-3 animate-in fade-in-50 duration-300">
                {summaryItems.length > 0 ? (
                  <div className="space-y-3">
                    {summaryItems.map((item, idx) => (
                      <div key={idx} className="rounded-xl border border-border/80 bg-card p-3.5 text-xs space-y-1.5 shadow-2xs">
                        <div className="flex items-center justify-between gap-2 font-bold text-foreground">
                          <span className="rounded bg-primary/10 px-2 py-0.5 text-primary text-[10px]">
                            # {idx + 1}
                          </span>
                          <span className="text-muted-foreground truncate">{item.chapter}</span>
                        </div>
                        <h4 className="font-bold text-foreground">{item.topic}</h4>
                        <p className="text-muted-foreground leading-relaxed">{item.content}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed p-8 text-center text-xs text-muted-foreground">
                    Chưa có tóm tắt ý chính.
                  </div>
                )}
              </div>
            )}

            {/* 6. SLIDES VIEW */}
            {activeTab === "slides" && (
              <div className="space-y-4 animate-in fade-in-50 duration-300">
                {loadingSlide ? (
                  <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
                    <Loader2 className="mb-2 h-6 w-6 animate-spin text-primary" />
                    <p className="text-xs font-medium">Đang nạp Slides bài giảng...</p>
                  </div>
                ) : slideData ? (
                  <SlideResultView result={slideData} documentId={courseId} />
                ) : (
                  <div className="rounded-xl border border-dashed p-8 text-center text-xs text-muted-foreground space-y-3">
                    <Presentation className="mx-auto h-7 w-7 text-muted-foreground/60" />
                    <p className="font-bold text-foreground">Chưa có Slides cho tài liệu này</p>
                    <p>Tạo slide bài giảng PPTX từ tài liệu gốc.</p>
                    <Button size="sm" className="h-8 text-xs font-bold" onClick={() => handleGenerateAction("slide")}>
                      Tạo Slides ngay
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* 7. VIDEO VIEW */}
            {activeTab === "video" && (
              <div className="space-y-4 animate-in fade-in-50 duration-300">
                {loadingVid ? (
                  <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
                    <Loader2 className="mb-2 h-6 w-6 animate-spin text-primary" />
                    <p className="text-xs font-medium">Đang nạp Video bài giảng...</p>
                  </div>
                ) : vidData ? (
                  <VidResultView
                    result={vidData}
                    documentId={courseId}
                    isRegenerating={generatingFeature === "vid"}
                    onGenerateMode={(mode, force) => {
                      setVideoMode(mode);
                      handleGenerateAction("vid", { videoMode: mode, force });
                    }}
                    onRenderVideo={async (videoIndex) => {
                      try {
                        const res = await renderPlaylistVideo(courseId, videoIndex);
                        setVidData(res);
                        toast.success("Đã tạo video MP4.");
                      } catch (err: unknown) {
                        toast.error(err instanceof Error ? err.message : "Không thể tạo video MP4.");
                      }
                    }}
                  />
                ) : (
                  <div className="rounded-xl border border-dashed p-8 text-xs text-muted-foreground space-y-4">
                    <div className="text-center space-y-2">
                      <FileVideo className="mx-auto h-7 w-7 text-muted-foreground/60" />
                      <p className="font-bold text-foreground">Chưa có Video cho tài liệu này</p>
                      <p>Chọn định dạng video phù hợp với thời gian học của bạn.</p>
                    </div>

                    {/* Video mode selector */}
                    <div className="grid grid-cols-2 gap-2 text-left">
                      {([
                        { id: "sixty_second", label: "60 giây", desc: "Giải thích 1 khái niệm" },
                        { id: "three_minute", label: "3 phút", desc: "Bài học ngắn đầy đủ" },
                        { id: "ten_minute", label: "10 phút", desc: "Bài giảng 1 chương" },
                        { id: "playlist_by_chapter", label: "Playlist", desc: "Nhiều video theo chương" },
                      ] as Array<{ id: VideoMode; label: string; desc: string }>).map((m) => (
                        <button
                          key={m.id}
                          type="button"
                          onClick={() => setVideoMode(m.id)}
                          className={cn(
                            "rounded-lg border p-2.5 transition-all",
                            videoMode === m.id
                              ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                              : "border-border/80 bg-card hover:border-primary/40",
                          )}
                        >
                          <span className="block text-xs font-bold text-foreground">{m.label}</span>
                          <span className="block text-[11px] text-muted-foreground">{m.desc}</span>
                        </button>
                      ))}
                    </div>

                    {/* Chapter selector: narrows a large document to one coherent topic */}
                    {(book?.chapters?.length ?? 0) > 0 && videoMode !== "playlist_by_chapter" && (
                      <div className="space-y-1.5">
                        <label className="block text-[11px] font-semibold text-foreground">
                          Chương / chủ đề (tùy chọn)
                        </label>
                        <select
                          value={videoChapter}
                          onChange={(e) => setVideoChapter(e.target.value)}
                          className="w-full rounded-lg border border-border/80 bg-background px-2.5 py-2 text-xs text-foreground"
                        >
                          <option value="">Toàn bộ tài liệu</option>
                          {book?.chapters?.map((ch: BookChapter, idx: number) => (
                            <option key={idx} value={ch.title}>
                              {ch.title}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    <Button
                      size="sm"
                      className="w-full h-8 text-xs font-bold"
                      disabled={generatingFeature === "vid"}
                      onClick={() => handleGenerateAction("vid")}
                    >
                      {generatingFeature === "vid" ? "Đang xử lý..." : "Tạo Video ngay"}
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* 8. GROUNDING (XEM NGUỒN) */}
            {activeTab === "grounding" && (
              <div className="space-y-4 animate-in fade-in-50 duration-300">
                <div className="rounded-xl border border-border/80 bg-card p-4 space-y-4 shadow-2xs">
                  <div className="flex items-center gap-2.5 border-b border-border/60 pb-3">
                    <ShieldCheck className="h-5 w-5 text-emerald-500" />
                    <div>
                      <h3 className="text-sm font-bold text-foreground">Nguồn Xác Thực (Grounded AI)</h3>
                      <p className="text-[11px] text-muted-foreground">
                        Học liệu được tạo từ {groundingCount || 0} đoạn nguồn sạch trong tài liệu của bạn.
                      </p>
                    </div>
                  </div>
                  <SourcesPanel
                    documentId={courseId}
                    sourceChunkIds={studyPackSourceIds}
                    fallbackCount={groundingCount}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Grounding & AI-accuracy disclaimer — shown wherever generated content is visible */}
          <div className="flex flex-col gap-1 rounded-xl border border-border/50 bg-muted/10 px-3 py-2.5 text-[11px] leading-relaxed text-muted-foreground">
            <span>Nội dung được tạo dựa trên nguồn trong file của bạn.</span>
            <span className="font-medium text-amber-700 dark:text-amber-400">
              AI có thể sai, hãy kiểm tra lại thông tin quan trọng.
            </span>
          </div>
            </>
          ) : (
            <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border/70 p-8 text-center">
              <Layers className="h-8 w-8 text-muted-foreground/50" />
              <p className="text-sm font-medium text-muted-foreground">
                Bộ học liệu sẽ xuất hiện ở đây.
              </p>
              <p className="text-xs text-muted-foreground max-w-xs">
                Bấm &quot;Tạo sách&quot; ở khung Không gian học tập để bắt đầu.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent className="max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-rose-600 font-bold">
              <Trash2 className="h-5 w-5" />
              Xác nhận xóa tài liệu
            </DialogTitle>
            <DialogDescription className="pt-2 text-sm text-muted-foreground leading-relaxed">
              Bạn có chắc muốn xóa tài liệu này? Hành động này sẽ xóa các học liệu đã tạo từ tài liệu (file gốc, trích xuất TXT/JSON, vector store và video/slides liên quan). Hành động này không thể hoàn tác.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4 flex gap-2 sm:justify-end">
            <Button
              variant="outline"
              disabled={isDeleting}
              onClick={() => setIsDeleteDialogOpen(false)}
            >
              Hủy
            </Button>
            <Button
              variant="destructive"
              disabled={isDeleting}
              onClick={handleDeleteDocument}
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Đang xóa...
                </>
              ) : (
                "Xóa vĩnh viễn"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
