"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  BookMarked,
  Brain,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Download,
  Eye,
  Flag,
  Layers,
  Lightbulb,
  PenLine,
  RotateCcw,
  Target,
  Trophy,
  XCircle,
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
  SourcesPanel,
  stripInternalMarkers,
  type PlainObject,
} from "./resultHelpers";

function optionEntries(options: unknown) {
  return asArray(options).map((option, index) => ({
    key: String(index),
    label: String.fromCharCode(65 + index),
    value: asString(option),
  }));
}

export default function QuizResultView({ result, documentId }: { result: GenerateResponse; documentId?: string }) {
  const questions = asArray(result.questions);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [revealedQuestions, setRevealedQuestions] = useState<Record<number, boolean>>({});
  const [submitted, setSubmitted] = useState(false);
  const [showExamPack, setShowExamPack] = useState(false);

  const current = isObject(questions[currentIndex]) ? questions[currentIndex] : {};
  const options = optionEntries(current.options);
  const correct = Number(current.correct ?? 0);
  const selected = answers[currentIndex];
  const isRevealed = Boolean(revealedQuestions[currentIndex]) || submitted;
  const answeredCount = Object.keys(answers).length;
  const progress = questions.length ? ((currentIndex + 1) / questions.length) * 100 : 0;
  const answerProgress = questions.length ? (answeredCount / questions.length) * 100 : 0;
  const questionType = stripInternalMarkers(asString(current.question_type ?? current.type, "concept"));
  const conceptTags = asArray(current.concept_tags).map((tag) => stripInternalMarkers(asString(tag)));
  const whyWrongOptionsAreWrong = asArray(current.why_wrong_options_are_wrong).map((reason) =>
    stripInternalMarkers(asString(reason))
  );

  const score = questions.reduce<number>((total, question, index) => {
    const item = isObject(question) ? question : {};
    return total + (answers[index] === Number(item.correct ?? 0) ? 1 : 0);
  }, 0);
  const scorePercent = questions.length ? Math.round((score / questions.length) * 100) : 0;

  if (questions.length === 0) {
    return <EmptyResult message="Chưa có câu hỏi để hiển thị." />;
  }

  const resetQuiz = () => {
    setAnswers({});
    setRevealedQuestions({});
    setSubmitted(false);
    setCurrentIndex(0);
  };

  return (
    <section className="space-y-4">
      <div className="rounded-lg border bg-card p-5 shadow-xs">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
              <ClipboardCheck className="h-4 w-4 text-primary" />
              Câu {currentIndex + 1} / {questions.length}
            </div>
            <h3 className="text-xl font-semibold leading-snug text-foreground">
              {stripInternalMarkers(asString(current.question, "Câu hỏi"))}
            </h3>
            {conceptTags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {conceptTags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <DownloadLink
              href={result.answer_key_url}
              label="Tải key đáp án"
              icon={<Download className="h-4 w-4" />}
              variant="default"
            />
          </div>
        </div>

        <Progress value={progress} className="mb-3 h-2" />

        <div className="mb-5 grid gap-3 md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
              <span>Tiến trình hoàn thành</span>
              <span>
                {answeredCount}/{questions.length}
              </span>
            </div>
            <Progress value={answerProgress} className="h-1.5" />
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
              <Flag className="h-3.5 w-3.5" />
              {questionType}
            </span>
            <button
              type="button"
              onClick={() =>
                setRevealedQuestions((prev) => ({ ...prev, [currentIndex]: true }))
              }
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              <Eye className="h-3.5 w-3.5" />
              Xem đáp án
            </button>
            <button
              type="button"
              onClick={resetQuiz}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Làm lại
            </button>
            <button
              type="button"
              disabled={answeredCount === 0}
              onClick={() => setSubmitted(true)}
              className={buttonVariants({
                variant: submitted ? "secondary" : "default",
                size: "sm",
              })}
            >
              Chấm điểm
            </button>
            {submitted && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300">
                <Trophy className="h-3.5 w-3.5" />
                {scorePercent}%
              </span>
            )}
          </div>
        </div>

        {submitted && (
          <div className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200">
            Kết quả: {score}/{questions.length} câu đúng. Dùng các ô bên dưới để review lại từng câu.
          </div>
        )}

        <div className="mb-5 flex flex-wrap gap-2">
          {questions.map((question, index) => {
            const item = isObject(question) ? question : {};
            const isAnswered = answers[index] !== undefined;
            const isCorrect = isAnswered && answers[index] === Number(item.correct ?? 0);
            return (
              <button
                key={index}
                type="button"
                onClick={() => setCurrentIndex(index)}
                className={cn(
                  "h-8 min-w-8 rounded-md border px-2 text-xs font-semibold transition-colors shrink-0",
                  currentIndex === index && "border-primary bg-primary text-primary-foreground",
                  currentIndex !== index && !submitted && isAnswered && "border-primary/30 bg-primary/10 text-primary",
                  currentIndex !== index && !submitted && !isAnswered && "bg-background text-muted-foreground",
                  currentIndex !== index && submitted && isCorrect && "border-emerald-200 bg-emerald-50 text-emerald-700",
                  currentIndex !== index && submitted && !isCorrect && "border-rose-200 bg-rose-50 text-rose-700"
                )}
                aria-label={`Câu ${index + 1}${isAnswered ? " đã trả lời" : " chưa trả lời"}`}
              >
                {index + 1}
              </button>
            );
          })}
        </div>

        {options.length > 0 ? (
          <div className="grid gap-3">
            {options.map((option, optionIndex) => {
              const isSelected = selected === optionIndex;
              const isCorrect = optionIndex === correct;
              const isWrongSelection = isRevealed && isSelected && !isCorrect;
              // why_wrong_options_are_wrong is aligned to the wrong options only (correct
              // option has no entry), in the order they appear in `options`.
              const wrongOptionsBeforeThis = options.slice(0, optionIndex).filter((_, i) => i !== correct).length;
              const whyWrong = optionIndex !== correct ? whyWrongOptionsAreWrong[wrongOptionsBeforeThis] : undefined;

              return (
                <div key={option.key}>
                  <button
                    type="button"
                    disabled={isRevealed}
                    aria-pressed={isSelected}
                    onClick={() =>
                      setAnswers((prev) => ({ ...prev, [currentIndex]: optionIndex }))
                    }
                    className={cn(
                      "flex w-full items-start gap-3 rounded-md border p-4 text-left text-sm transition-colors",
                      !isRevealed && isSelected && "border-primary bg-primary/10",
                      !isRevealed && !isSelected && "bg-background hover:bg-muted/50",
                      isRevealed && isCorrect && "border-emerald-300 bg-emerald-50 text-emerald-950 dark:bg-emerald-950/30 dark:text-emerald-200",
                      isWrongSelection && "border-rose-300 bg-rose-50 text-rose-950 dark:bg-rose-950/30 dark:text-rose-200"
                    )}
                  >
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-muted text-xs font-semibold">
                      {option.label}
                    </span>
                    <span className="leading-6">{stripInternalMarkers(option.value)}</span>
                    {isRevealed && isCorrect && (
                      <CheckCircle2 className="ml-auto h-4 w-4 shrink-0 text-emerald-600" />
                    )}
                    {isWrongSelection && <XCircle className="ml-auto h-4 w-4 shrink-0 text-rose-600" />}
                  </button>
                  {isWrongSelection && whyWrong && (
                    <p className="pl-4 pt-1 text-xs italic text-rose-600 dark:text-rose-400">{whyWrong}</p>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          isRevealed && (
            <div className="rounded-md border border-primary/30 bg-primary/10 p-4 text-sm text-foreground">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-primary">
                Đáp án mẫu
              </p>
              {stripInternalMarkers(asString(current.correct_answer))}
            </div>
          )
        )}

        {isRevealed && Boolean(current.explanation) && (
          <div className="mt-4 rounded-md bg-muted/50 p-3 text-sm leading-6 text-muted-foreground">
            <div className="mb-1 flex items-center gap-2 font-semibold text-foreground">
              <Eye className="h-4 w-4" />
              Giải thích
            </div>
            {stripInternalMarkers(asString(current.explanation))}
          </div>
        )}

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
              setCurrentIndex((prev) => Math.min(questions.length - 1, prev + 1))
            }
            disabled={currentIndex === questions.length - 1}
          >
            Tiếp
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {submitted && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-5 dark:border-blue-900/50 dark:bg-blue-950/30">
          <div className="mb-2 flex items-center gap-2 text-base font-bold text-blue-900 dark:text-blue-100">
            <Brain className="h-4 w-4" />
            Chẩn đoán điểm yếu
          </div>
          {questions.filter((q, idx) => answers[idx] !== Number((isObject(q) ? q : {}).correct ?? 0)).length === 0 ? (
            <p className="flex items-center gap-1.5 text-sm font-medium text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              Xuất sắc! Bạn đã trả lời đúng toàn bộ câu hỏi.
            </p>
          ) : (
            <div className="space-y-3 text-sm text-blue-950 dark:text-blue-100">
              <p className="flex items-center gap-1.5 font-semibold text-red-700 dark:text-red-400">
                <AlertTriangle className="h-4 w-4" />
                Khái niệm chưa nắm vững ({questions.filter((q, idx) => answers[idx] !== Number((isObject(q) ? q : {}).correct ?? 0)).length} câu sai)
              </p>
              <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                {questions.map((q, idx) => {
                  if (answers[idx] === Number((isObject(q) ? q : {}).correct ?? 0)) return null;
                  const item = isObject(q) ? q : {};
                  return (
                    <li key={idx}>
                      <span className="font-semibold text-foreground">Câu {idx + 1}: </span>
                      {asString(item.question).slice(0, 70)}... <br />
                      <span className="inline-flex items-center gap-1 text-xs text-primary">
                        <Lightbulb className="h-3 w-3" />
                        Giải thích: {asString(item.explanation)}
                      </span>
                    </li>
                  );
                })}
              </ul>
              <div className="mt-3 rounded-lg bg-background/80 p-3 text-xs border">
                <span className="inline-flex items-center gap-1 font-bold">
                  <Target className="h-3.5 w-3.5" />
                  Khuyến nghị:
                </span>{" "}
                Mở sang <span className="font-semibold text-primary">Sách</span> hoặc <span className="font-semibold text-primary">Slides</span> để rà soát lại các phần bị sai ở trên trước khi làm lại đề.
              </div>
            </div>
          )}
        </div>
      )}

      {isObject(result.exam_pack) && (
        <div className="rounded-xl border bg-card p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-lg font-bold text-primary">
              <BookMarked className="h-5 w-5" />
              {asString((result.exam_pack as PlainObject).title, "Bộ ôn thi trọng tâm")}
            </div>
            <button
              type="button"
              onClick={() => setShowExamPack(!showExamPack)}
              className="text-xs font-medium text-primary hover:underline"
            >
              {showExamPack ? "Thu gọn bộ ôn thi" : "Xem chi tiết bộ ôn thi"}
            </button>
          </div>
          <p className="text-sm text-muted-foreground">{asString((result.exam_pack as PlainObject).mock_exam_guide)}</p>
          
          {showExamPack && (
            <div className="space-y-4 pt-3 border-t">
              {Array.isArray((result.exam_pack as PlainObject).flashcards) && (
                <div>
                  <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold">
                    <Layers className="h-4 w-4" />
                    Thẻ ôn tập nhanh
                  </h4>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {((result.exam_pack as PlainObject).flashcards as unknown[]).map((fc, i) => {
                      const card = isObject(fc) ? fc : {};
                      return (
                        <div key={i} className="rounded-md border p-3 bg-muted/20">
                          <div className="text-xs font-bold text-primary">{asString(card.front)}</div>
                          <div className="mt-1 text-xs text-muted-foreground">{asString(card.back)}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {Array.isArray((result.exam_pack as PlainObject).short_answer_questions) && (
                <div>
                  <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold">
                    <PenLine className="h-4 w-4" />
                    Câu tự luận ngắn
                  </h4>
                  <div className="space-y-2">
                    {((result.exam_pack as PlainObject).short_answer_questions as unknown[]).map((sq, i) => {
                      const item = isObject(sq) ? sq : {};
                      return (
                        <div key={i} className="rounded-md border p-3 bg-muted/10 space-y-1">
                          <div className="text-xs font-semibold text-foreground">Câu {i+1}: {asString(item.question)}</div>
                          <div className="text-xs text-emerald-700 dark:text-emerald-400"><strong>Đáp án chuẩn:</strong> {asString(item.answer_model)}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <SourcesPanel
        documentId={documentId}
        sourceChunkIds={result.quality_report?.source_chunk_ids}
        fallbackCount={result.quality_report?.usable_chunks_count || result.quality_report?.used_chunks}
      />
    </section>
  );
}
