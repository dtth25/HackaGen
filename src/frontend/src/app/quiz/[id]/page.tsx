"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Lightbulb,
  RotateCcw,
  BarChart3,
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Button,
  Progress,
  RadioGroup,
  RadioGroupItem,
  Label,
  Separator,
} from "@/components/ui";
import { generateQuiz, type QuizResponse } from "@/lib/api";

/* ── Helpers ───────────────────────────────────────────── */

const DIFFICULTY_LABEL: Record<string, string> = {
  easy: "Dễ",
  medium: "Trung bình",
  hard: "Khó",
};

const DIFFICULTY_COLOR: Record<string, string> = {
  easy: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  medium:
    "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  hard: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

const QUESTION_TYPE_LABEL: Record<string, string> = {
  mcq: "Trắc nghiệm",
  true_false: "Đúng/Sai",
  short_answer: "Tự luận ngắn",
  scenario: "Tình huống",
  code_reading: "Đọc hiểu code",
};

/* ── Component ─────────────────────────────────────────── */

export default function QuizPage() {
  const params = useParams();
  const router = useRouter();
  const courseId = params.id as string;

  /* Data state */
  const [quiz, setQuiz] = useState<QuizResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Interaction state */
  const [answers, setAnswers] = useState<Record<number, number>>({});
  // For free-form questions (no options: short_answer/scenario/code_reading), track whether
  // the user has revealed the sample answer — these can't be auto-graded, so they don't
  // contribute to the score, only to progress.
  const [revealed, setRevealed] = useState<Record<number, boolean>>({});
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [showResults, setShowResults] = useState(false);

  /* Fetch quiz on mount */
  useEffect(() => {
    async function fetchQuiz() {
      try {
        setLoading(true);
        setError(null);
        const data = await generateQuiz(courseId);
        setQuiz(data);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Không thể tải quiz. Vui lòng thử lại."
        );
      } finally {
        setLoading(false);
      }
    }

    fetchQuiz();
  }, [courseId]);

  /* Derived values */
  const questions = useMemo(() => quiz?.questions ?? [], [quiz?.questions]);
  const totalQuestions = questions.length;
  const currentQ = questions[currentQuestion];

  const handleSelect = useCallback(
    (value: string) => {
      if (showResults) return;
      const optionIndex = parseInt(value, 10);
      setAnswers((prev) => ({ ...prev, [currentQuestion]: optionIndex }));
    },
    [currentQuestion, showResults]
  );

  const goToQuestion = useCallback(
    (index: number) => {
      if (index >= 0 && index < totalQuestions) {
        setCurrentQuestion(index);
      }
    },
    [totalQuestions]
  );

  const handleShowResults = useCallback(() => {
    setShowResults(true);
  }, []);

  const handleRestart = useCallback(() => {
    setAnswers({});
    setRevealed({});
    setCurrentQuestion(0);
    setShowResults(false);
  }, []);

  const handleReveal = useCallback((index: number) => {
    setRevealed((prev) => ({ ...prev, [index]: true }));
  }, []);

  /* Scoring: only option-bearing questions (mcq/true_false) can be auto-graded.
     Free-form questions (short_answer/scenario/code_reading) count toward progress
     but are excluded from the score fraction since there's no way to auto-check them. */
  const scoreableCount = useMemo(
    () => questions.filter((q) => (q.options?.length ?? 0) > 0).length,
    [questions]
  );
  const score = useMemo(() => {
    let correct = 0;
    for (let i = 0; i < totalQuestions; i++) {
      if ((questions[i]?.options?.length ?? 0) > 0 && answers[i] === questions[i]?.correct) {
        correct++;
      }
    }
    return correct;
  }, [answers, questions, totalQuestions]);

  /* ── Loading state ───────────────────────────── */
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-sm text-muted-foreground">
          Đang tạo quiz từ tài liệu...
        </p>
      </div>
    );
  }

  /* ── Error state ─────────────────────────────── */
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <HelpCircle className="h-12 w-12 text-destructive" />
        <p className="text-sm text-destructive font-medium">{error}</p>
        <Button variant="outline" onClick={() => router.back()}>
          Quay lại
        </Button>
      </div>
    );
  }

  /* ── Empty state ─────────────────────────────── */
  if (!quiz || totalQuestions === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <p className="text-sm text-muted-foreground">
          Quiz trống hoặc không tìm thấy.
        </p>
        <Button variant="outline" onClick={() => router.back()}>
          Quay lại
        </Button>
      </div>
    );
  }

  /* ── Result screen ───────────────────────────── */
  if (showResults) {
    const percentage = scoreableCount > 0 ? Math.round((score / scoreableCount) * 100) : 0;
    let resultColor = "text-red-500";
    let resultText = "Cần cố gắng hơn!";
    if (percentage >= 80) {
      resultColor = "text-green-500";
      resultText = "Xuất sắc!";
    } else if (percentage >= 60) {
      resultColor = "text-amber-500";
      resultText = "Khá tốt!";
    } else if (percentage >= 40) {
      resultColor = "text-amber-500";
      resultText = "Có thể làm tốt hơn!";
    }
    const freeFormCount = totalQuestions - scoreableCount;

    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <button
            onClick={() => router.back()}
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            Quay lại
          </button>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Kết quả
          </h1>
          <p className="text-sm text-muted-foreground">{quiz.quiz_title || quiz.topic}</p>
        </div>

        {/* Score card */}
        <Card className="text-center py-8">
          <CardContent className="space-y-4">
            <BarChart3 className="h-12 w-12 mx-auto text-primary" />
            <div className={`text-5xl font-bold ${resultColor}`}>
              {score}/{scoreableCount}
            </div>
            <p className="text-lg font-medium">{resultText}</p>
            <Progress value={percentage} className="w-full max-w-xs mx-auto" />
            <p className="text-sm text-muted-foreground">
              {percentage}% câu trắc nghiệm trả lời đúng
              {freeFormCount > 0 && ` · ${freeFormCount} câu tự luận không tính điểm tự động`}
            </p>
          </CardContent>
          <CardFooter className="justify-center gap-3">
            <Button variant="outline" onClick={handleRestart}>
              <RotateCcw className="h-4 w-4 mr-1" />
              Làm lại
            </Button>
            <Button onClick={() => router.back()}>Quay lại</Button>
          </CardFooter>
        </Card>

        {/* Review answers */}
        <div className="space-y-3">
          <h2 className="text-lg font-medium">Chi tiết câu trả lời</h2>
          {questions.map((q, idx) => {
            const hasOptions = (q.options?.length ?? 0) > 0;
            const userAnswer = answers[idx];
            const isCorrect = hasOptions && userAnswer === q.correct;
            const isAnswered = hasOptions ? userAnswer !== undefined : Boolean(revealed[idx]);

            return (
              <Card
                key={idx}
                className={`border-l-4 ${
                  !hasOptions
                    ? "border-l-blue-400"
                    : isAnswered
                      ? isCorrect
                        ? "border-l-green-500"
                        : "border-l-red-500"
                      : "border-l-muted"
                }`}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-sm font-medium">
                      Câu {idx + 1}: {q.question}
                    </CardTitle>
                    {hasOptions ? (
                      isAnswered ? (
                        isCorrect ? (
                          <CheckCircle2 className="h-5 w-5 shrink-0 text-green-500" />
                        ) : (
                          <XCircle className="h-5 w-5 shrink-0 text-red-500" />
                        )
                      ) : (
                        <HelpCircle className="h-5 w-5 shrink-0 text-muted-foreground" />
                      )
                    ) : (
                      <span className="shrink-0 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                        {QUESTION_TYPE_LABEL[q.type ?? ""] ?? "Tự luận"}
                      </span>
                    )}
                  </div>
                  {q.concept_tags && q.concept_tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {q.concept_tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </CardHeader>
                <CardContent className="space-y-1 pb-3">
                  {hasOptions ? (
                    q.options.map((opt, oi) => {
                      let optClass = "text-sm px-3 py-1.5 rounded-md";
                      if (oi === q.correct) {
                        optClass += " bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
                      } else if (oi === userAnswer && oi !== q.correct) {
                        optClass += " bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
                      } else {
                        optClass += " text-muted-foreground";
                      }
                      // why_wrong_options_are_wrong is aligned to the wrong options only, in
                      // the order they appear in `options` (the correct option has no entry).
                      const wrongOptionsBeforeThis = q.options
                        .slice(0, oi)
                        .filter((_, i) => i !== q.correct).length;
                      const whyWrong =
                        oi !== q.correct
                          ? q.why_wrong_options_are_wrong?.[wrongOptionsBeforeThis]
                          : undefined;
                      return (
                        <div key={oi}>
                          <div className={optClass}>{opt}</div>
                          {isAnswered && oi === userAnswer && whyWrong && (
                            <p className="px-3 pt-0.5 text-xs italic text-red-600 dark:text-red-400">
                              {whyWrong}
                            </p>
                          )}
                        </div>
                      );
                    })
                  ) : isAnswered ? (
                    <div className="rounded-md bg-primary/10 px-3 py-2 text-sm text-foreground">
                      <span className="font-medium">Đáp án mẫu: </span>
                      {q.correct_answer}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground italic">Chưa xem đáp án mẫu.</p>
                  )}
                  {q.explanation && (
                    <p className="flex items-start gap-1.5 text-xs text-muted-foreground mt-2 italic">
                      <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                      {q.explanation}
                    </p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    );
  }

  /* ── Quiz screen ─────────────────────────────── */
  const answeredCount = Object.keys(answers).length + Object.keys(revealed).length;
  const progressValue = totalQuestions > 0 ? (answeredCount / totalQuestions) * 100 : 0;
  const qualityReport = quiz.quality_report;
  const difficultyMix = quiz.difficulty_mix;

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {/* Header */}
      <div className="space-y-2">
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Quay lại
        </button>
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              {quiz.quiz_title || quiz.topic}
            </h1>
            <p className="text-sm text-muted-foreground">
              Tài liệu: {courseId.slice(0, 8)}...
            </p>
          </div>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${DIFFICULTY_COLOR[quiz.difficulty] ?? DIFFICULTY_COLOR.medium}`}
          >
            {DIFFICULTY_LABEL[quiz.difficulty] ?? quiz.difficulty}
          </span>
        </div>
        {difficultyMix && (difficultyMix.easy + difficultyMix.medium + difficultyMix.hard) > 0 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Cơ cấu độ khó:</span>
            <span className={`rounded-full px-2 py-0.5 ${DIFFICULTY_COLOR.easy}`}>Dễ {difficultyMix.easy}</span>
            <span className={`rounded-full px-2 py-0.5 ${DIFFICULTY_COLOR.medium}`}>TB {difficultyMix.medium}</span>
            <span className={`rounded-full px-2 py-0.5 ${DIFFICULTY_COLOR.hard}`}>Khó {difficultyMix.hard}</span>
          </div>
        )}
        {qualityReport && (qualityReport.score < 80 || (qualityReport.warnings?.length ?? 0) > 0) && (
          <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-300">
            <strong>Kiểm duyệt chất lượng (Score: {qualityReport.score}/100):</strong>{" "}
            {qualityReport.warnings?.join(" | ") || "Bộ câu hỏi đã được chuẩn hóa tự động."}
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>
            Đã trả lời: {answeredCount}/{totalQuestions}
          </span>
          <span>
            Câu {currentQuestion + 1}/{totalQuestions}
          </span>
        </div>
        <Progress value={progressValue} />
      </div>

      <Separator />

      {/* Question card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <CardDescription className="text-xs font-medium uppercase tracking-wide">
              Câu {currentQuestion + 1} / {totalQuestions}
            </CardDescription>
            {currentQ.type && QUESTION_TYPE_LABEL[currentQ.type] && (
              <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                {QUESTION_TYPE_LABEL[currentQ.type]}
              </span>
            )}
          </div>
          <CardTitle className="text-base font-medium leading-relaxed whitespace-pre-wrap">
            {currentQ.question}
          </CardTitle>
          {currentQ.concept_tags && currentQ.concept_tags.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {currentQ.concept_tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
                >
                  #{tag}
                </span>
              ))}
            </div>
          )}
        </CardHeader>
        <CardContent>
          {currentQ.options && currentQ.options.length > 0 ? (
            <>
              <RadioGroup
                value={
                  answers[currentQuestion] !== undefined
                    ? String(answers[currentQuestion])
                    : undefined
                }
                onValueChange={handleSelect}
                className="gap-2"
              >
                {currentQ.options.map((option, idx) => {
                  const isSelected = answers[currentQuestion] === idx;
                  const hasAnswer = answers[currentQuestion] !== undefined;
                  const isCorrect = idx === currentQ.correct;
                  const wrongOptionsBeforeThis = currentQ.options
                    .slice(0, idx)
                    .filter((_, i) => i !== currentQ.correct).length;
                  const whyWrong =
                    idx !== currentQ.correct
                      ? currentQ.why_wrong_options_are_wrong?.[wrongOptionsBeforeThis]
                      : undefined;

                  let optionClass =
                    "flex items-center gap-3 rounded-lg border px-4 py-3 text-sm transition-all cursor-pointer";
                  if (hasAnswer) {
                    if (isCorrect) {
                      optionClass += " border-green-500 bg-green-50 dark:bg-green-950/20";
                    } else if (isSelected && !isCorrect) {
                      optionClass += " border-red-500 bg-red-50 dark:bg-red-950/20";
                    } else {
                      optionClass += " border-border opacity-60";
                    }
                  } else {
                    optionClass +=
                      " border-border hover:border-primary hover:bg-muted/50";
                  }

                  return (
                    <div key={idx}>
                      <Label className={optionClass}>
                        <RadioGroupItem
                          value={String(idx)}
                          disabled={hasAnswer}
                          className={
                            hasAnswer && isCorrect
                              ? "border-green-500 text-green-500 data-[state=checked]:bg-green-500 data-[state=checked]:border-green-500"
                              : hasAnswer && isSelected && !isCorrect
                                ? "border-red-500 text-red-500 data-[state=checked]:bg-red-500 data-[state=checked]:border-red-500"
                                : ""
                          }
                        />
                        <span className="flex-1">{option}</span>
                        {hasAnswer && isCorrect && (
                          <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500" />
                        )}
                        {hasAnswer && isSelected && !isCorrect && (
                          <XCircle className="h-4 w-4 shrink-0 text-red-500" />
                        )}
                      </Label>
                      {hasAnswer && isSelected && !isCorrect && whyWrong && (
                        <p className="px-4 pt-1 text-xs italic text-red-600 dark:text-red-400">
                          {whyWrong}
                        </p>
                      )}
                    </div>
                  );
                })}
              </RadioGroup>

              {/* Explanation */}
              {answers[currentQuestion] !== undefined && currentQ.explanation && (
                <div className="mt-4 rounded-lg bg-muted/50 px-4 py-3 text-sm text-muted-foreground">
                  <p className="flex items-center gap-1.5 font-medium text-foreground mb-1">
                    <Lightbulb className="h-3.5 w-3.5" />
                    Giải thích
                  </p>
                  <p>{currentQ.explanation}</p>
                </div>
              )}
            </>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground">
                Câu tự luận — hãy tự trả lời trong đầu, sau đó xem đáp án mẫu để tự đối chiếu.
              </p>
              {!revealed[currentQuestion] ? (
                <Button variant="outline" onClick={() => handleReveal(currentQuestion)}>
                  Xem đáp án mẫu
                </Button>
              ) : (
                <>
                  <div className="rounded-lg border border-primary/30 bg-primary/10 px-4 py-3 text-sm text-foreground">
                    <p className="font-medium mb-1">Đáp án mẫu</p>
                    <p className="whitespace-pre-wrap">{currentQ.correct_answer}</p>
                  </div>
                  {currentQ.explanation && (
                    <div className="rounded-lg bg-muted/50 px-4 py-3 text-sm text-muted-foreground">
                      <p className="flex items-center gap-1.5 font-medium text-foreground mb-1">
                        <Lightbulb className="h-3.5 w-3.5" />
                        Giải thích
                      </p>
                      <p>{currentQ.explanation}</p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex items-center justify-between gap-3">
        <Button
          variant="outline"
          disabled={currentQuestion === 0}
          onClick={() => goToQuestion(currentQuestion - 1)}
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Câu trước
        </Button>

        <span className="text-xs text-muted-foreground">
          {currentQuestion + 1} / {totalQuestions}
        </span>

        {currentQuestion < totalQuestions - 1 ? (
          <Button
            variant="outline"
            onClick={() => goToQuestion(currentQuestion + 1)}
          >
            Câu sau
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        ) : (
          <Button onClick={handleShowResults}>
            Xem kết quả
            <BarChart3 className="h-4 w-4 ml-1" />
          </Button>
        )}
      </div>
    </div>
  );
}
