"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  Calculator,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  Download,
  Lightbulb,
  ListChecks,
  PenLine,
  Sparkles,
  Target,
} from "lucide-react";
import type { GenerateResponse } from "@/lib/api";
import {
  asArray,
  asString,
  DownloadLink,
  isObject,
  LessonList,
  MarkdownBlock,
  SourcesPanel,
  stripInternalMarkers,
  textList,
  type PlainObject,
} from "./resultHelpers";

export default function BookResultView({ result, documentId }: { result: GenerateResponse; documentId?: string }) {
  const book: PlainObject = isObject(result.book) ? result.book : {};
  const studyPack = isObject(book.study_pack) ? book.study_pack : {};
  const bookQuality = isObject(book.quality_report) ? book.quality_report : {};
  const chapters = asArray(book.chapters);
  const glossary = asArray(book.glossary);
  const generationStatus = isObject(book.generation_status) ? book.generation_status : {};
  const isLimited = generationStatus.status === "limited";
  const prerequisites = textList(book.prerequisites);
  const packFlashcards = asArray(studyPack.flashcards);
  const packSummary = asArray(studyPack.high_yield_summary);
  // Books use either `lessons` or `sections` for their per-chapter units depending
  // on which generator path produced them — treat the two as synonyms everywhere.
  const chapterUnits = (chapter: PlainObject) => {
    const lessons = asArray(chapter.lessons);
    return lessons.length ? lessons : asArray(chapter.sections);
  };
  const lessonCount = chapters.reduce<number>((total, chapter) => {
    return total + chapterUnits(isObject(chapter) ? chapter : {}).length;
  }, 0);

  // Keep track of which chapter/lesson is open to only render DOM tree for open lessons
  const [openLessons, setOpenLessons] = useState<Record<string, boolean>>({
    "0-0": true, // Default open first lesson of first chapter
  });

  const [showGlossary, setShowGlossary] = useState(false);

  const toggleLesson = (key: string) => {
    setOpenLessons((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <section className="space-y-6">
      {isLimited && (
        <div className="flex items-start gap-2.5 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800/60 dark:bg-amber-950/20">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700 dark:text-amber-400" />
          <div>
            <div className="font-semibold text-amber-900 dark:text-amber-200">
              Bản học trọng tâm (ngữ cảnh giới hạn)
            </div>
            <p className="mt-1 text-amber-800/90 dark:text-amber-300/90">
              {asString(
                generationStatus.reason,
                "Tài liệu chưa đủ ngữ cảnh sạch để tạo giáo trình đầy đủ, hệ thống đã tạo bản tóm tắt trọng tâm thay thế.",
              )}
            </p>
          </div>
        </div>
      )}

      <div className="rounded-lg border bg-card p-5 shadow-xs">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h3 className="text-2xl font-semibold text-foreground">
              {asString(book.title, "Sách từ tài liệu")}
            </h3>
            {Boolean(book.description) && (
              <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">
                {asString(book.description)}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <div className="rounded-md bg-muted px-3 py-2 text-center text-xs">
              <div className="font-semibold">{chapters.length}</div>
              <div className="text-muted-foreground">Chương</div>
            </div>
            <div className="rounded-md bg-muted px-3 py-2 text-center text-xs">
              <div className="font-semibold">{lessonCount}</div>
              <div className="text-muted-foreground">Bài</div>
            </div>
            <DownloadLink
              href={result.pdf_url}
              label="Tải PDF"
              icon={<Download className="h-4 w-4" />}
              variant="default"
            />
          </div>
        </div>
      </div>

      {prerequisites.length > 0 && (
        <div className="rounded-lg border bg-card p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <ListChecks className="h-4 w-4 text-primary" />
            Kiến thức cần có trước
          </div>
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {prerequisites.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-3 rounded-lg border bg-primary/5 p-4 sm:grid-cols-4">
        <div className="sm:col-span-4">
          <div className="text-sm font-semibold text-primary">Trung tâm bộ học liệu</div>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Mindmap, flashcards, quiz và bản tóm tắt trọng tâm đều được dựng từ chính Sách này.
          </p>
        </div>
        <div className="rounded-md bg-background p-3 text-sm">
          <div className="font-semibold">{chapters.length}</div>
          <div className="text-xs text-muted-foreground">Chương</div>
        </div>
        <div className="rounded-md bg-background p-3 text-sm">
          <div className="font-semibold">{packSummary.length || chapters.length}</div>
          <div className="text-xs text-muted-foreground">Summary</div>
        </div>
        <div className="rounded-md bg-background p-3 text-sm">
          <div className="font-semibold">{packFlashcards.length || glossary.length}</div>
          <div className="text-xs text-muted-foreground">Flashcards</div>
        </div>
        <div className="rounded-md bg-background p-3 text-sm">
          <div className="font-semibold">RAG</div>
          <div className="text-xs text-muted-foreground">Grounded</div>
        </div>
        <div className="sm:col-span-4">
          <SourcesPanel
            documentId={documentId}
            sourceChunkIds={bookQuality.source_chunk_ids ?? result.quality_report?.source_chunk_ids}
            fallbackCount={result.quality_report?.usable_chunks_count || result.quality_report?.used_chunks}
          />
        </div>
      </div>

      <div className="space-y-4">
        {chapters.map((chapter, chapterIndex) => {
          const item = isObject(chapter) ? chapter : {};
          const lessons = chapterUnits(item);

          return (
            <section key={chapterIndex} className="rounded-lg border bg-card shadow-xs overflow-hidden">
              <div className="border-b bg-muted/20 p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground">
                    {chapterIndex + 1}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="font-semibold leading-snug text-foreground">
                      {asString(item.title, `Chương ${chapterIndex + 1}`)}
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
                  const key = `${chapterIndex}-${lessonIndex}`;
                  const isOpen = Boolean(openLessons[key]);

                  return (
                    <div key={lessonIndex} className="transition-colors">
                      <button
                        type="button"
                        onClick={() => toggleLesson(key)}
                        className="w-full flex items-center justify-between gap-3 p-4 text-left hover:bg-muted/40 transition-colors"
                      >
                        <div className="min-w-0">
                          <div className="text-sm font-semibold leading-snug text-foreground">{title}</div>
                          {Boolean(lessonObj.duration) && (
                            <div className="mt-1 text-xs text-muted-foreground">
                              {asString(lessonObj.duration)}
                            </div>
                          )}
                        </div>
                        <span className="flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground shrink-0">
                          {isOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                          {isOpen ? "Thu gọn" : "Xem bài học"}
                        </span>
                      </button>

                      {/* Render DOM tree ONLY when lesson is open to conserve memory */}
                      {isOpen && (
                        <div className="space-y-5 px-4 pb-5 pt-2 border-t border-border/40 bg-muted/5">
                          {Boolean(lessonObj.core_idea) && (
                            <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4 dark:border-amber-900/50 dark:bg-amber-950/20">
                              <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-800 dark:text-amber-300">
                                <Sparkles className="h-3.5 w-3.5" />
                                Ý Tưởng Cốt Lõi (High-Yield Core Idea)
                              </div>
                              <p className="text-sm font-medium leading-relaxed text-amber-950 dark:text-amber-100">
                                {stripInternalMarkers(asString(lessonObj.core_idea))}
                              </p>
                              {Boolean(lessonObj.why_it_matters) && (
                                <p className="mt-2 border-t border-amber-200/60 pt-2 text-xs text-amber-800 dark:border-amber-800/40 dark:text-amber-300">
                                  <span className="font-semibold">Tại sao quan trọng: </span>
                                  {stripInternalMarkers(asString(lessonObj.why_it_matters))}
                                </p>
                              )}
                            </div>
                          )}
                          <LessonList
                            title="Mục tiêu"
                            icon={<Target className="h-4 w-4" />}
                            items={textList(lessonObj.objectives)}
                          />
                          <div>
                            <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                              <BookOpen className="h-4 w-4 text-primary" />
                              Nội dung diễn giải chi tiết
                            </div>
                            <div className="rounded-lg bg-background border p-4 shadow-2xs">
                              <MarkdownBlock
                                content={asString(
                                  lessonObj.simple_explanation ?? lessonObj.explanation ?? lessonObj.lecture,
                                  "Chưa có nội dung bài học."
                                )}
                              />
                            </div>
                          </div>

                          {asArray(lessonObj.key_concepts).length > 0 && (
                            <div>
                              <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                                <Lightbulb className="h-4 w-4 text-primary" />
                                Khái niệm chính
                              </div>
                              <div className="grid gap-2 sm:grid-cols-2">
                                {asArray(lessonObj.key_concepts).map((kc, i) => {
                                  const concept = isObject(kc) ? kc : {};
                                  return (
                                    <div key={i} className="rounded-md border bg-background p-3 text-sm">
                                      <div className="font-semibold text-foreground">{asString(concept.term)}</div>
                                      <div className="mt-1 text-xs text-muted-foreground">
                                        {stripInternalMarkers(asString(concept.definition))}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}

                          {Boolean(lessonObj.example) && (
                            <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4 dark:border-emerald-900/50 dark:bg-emerald-950/20">
                              <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-emerald-800 dark:text-emerald-300">
                                <BookOpen className="h-3.5 w-3.5" />
                                Ví dụ minh họa
                              </div>
                              <p className="text-sm leading-relaxed text-emerald-950 dark:text-emerald-100">
                                {stripInternalMarkers(asString(lessonObj.example))}
                              </p>
                              {Boolean(lessonObj.non_example) && (
                                <p className="mt-2 border-t border-emerald-200/60 pt-2 text-xs text-emerald-800 dark:border-emerald-800/40 dark:text-emerald-300">
                                  <span className="font-semibold">KHÔNG phải là: </span>
                                  {stripInternalMarkers(asString(lessonObj.non_example))}
                                </p>
                              )}
                            </div>
                          )}

                          {Boolean(isObject(lessonObj.common_misunderstanding) && (lessonObj.common_misunderstanding as PlainObject).mistake) && (
                            <div className="rounded-lg border border-rose-200 bg-rose-50/50 p-4 dark:border-rose-900/50 dark:bg-rose-950/20">
                              <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-rose-800 dark:text-rose-300">
                                <AlertTriangle className="h-3.5 w-3.5" />
                                Sai lầm thường gặp
                              </div>
                              <p className="text-sm leading-relaxed text-rose-950 dark:text-rose-100">
                                <span className="font-semibold">Sai: </span>
                                {stripInternalMarkers(asString((lessonObj.common_misunderstanding as PlainObject)?.mistake))}
                              </p>
                              <p className="mt-1 text-sm leading-relaxed text-rose-950 dark:text-rose-100">
                                <span className="font-semibold">Đúng: </span>
                                {stripInternalMarkers(asString((lessonObj.common_misunderstanding as PlainObject)?.correction))}
                              </p>
                            </div>
                          )}

                          {asArray(lessonObj.worked_examples).map((we, i) => {
                            const worked = isObject(we) ? we : {};
                            const steps = textList(worked.step_by_step_solution);
                            if (!worked.problem) return null;
                            return (
                              <div
                                key={i}
                                className="rounded-lg border border-sky-200 bg-sky-50/50 p-4 dark:border-sky-900/50 dark:bg-sky-950/20"
                              >
                                <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-sky-800 dark:text-sky-300">
                                  <Calculator className="h-3.5 w-3.5" />
                                  Ví dụ mẫu: {asString(worked.title, "Từng bước")}
                                </div>
                                <p className="text-sm font-medium text-sky-950 dark:text-sky-100">
                                  {stripInternalMarkers(asString(worked.problem))}
                                </p>
                                {steps.length > 0 && (
                                  <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-sky-900 dark:text-sky-200">
                                    {steps.map((step, si) => (
                                      <li key={si}>{step}</li>
                                    ))}
                                  </ol>
                                )}
                                {Boolean(worked.common_error) && (
                                  <p className="mt-2 border-t border-sky-200/60 pt-2 text-xs text-sky-800 dark:border-sky-800/40 dark:text-sky-300">
                                    <span className="font-semibold">Lỗi thường gặp: </span>
                                    {stripInternalMarkers(asString(worked.common_error))}
                                  </p>
                                )}
                              </div>
                            );
                          })}

                          <LessonList
                            title="Kiểm tra chủ động (Active Recall Quick Check)"
                            icon={<ClipboardCheck className="h-4 w-4" />}
                            items={textList(lessonObj.active_recall_questions ?? lessonObj.assessment)}
                          />

                          {asArray(lessonObj.practice_problems).length > 0 && (
                            <div className="rounded-lg border border-indigo-200 bg-indigo-50/50 p-4 dark:border-indigo-900/50 dark:bg-indigo-950/20">
                              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-800 dark:text-indigo-300">
                                <PenLine className="h-3.5 w-3.5" />
                                Bài tập thực hành
                              </div>
                              <div className="space-y-3">
                                {asArray(lessonObj.practice_problems).map((pp, i) => {
                                  const problem = isObject(pp) ? pp : {};
                                  if (!problem.question) return null;
                                  return (
                                    <div key={i} className="rounded-md border border-indigo-200/60 bg-background p-3 text-sm dark:border-indigo-900/40">
                                      <div className="flex items-start justify-between gap-2">
                                        <span className="font-medium text-foreground">{stripInternalMarkers(asString(problem.question))}</span>
                                        <span className="shrink-0 rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
                                          {asString(problem.difficulty, "medium")}
                                        </span>
                                      </div>
                                      {Boolean(problem.hint) && (
                                        <p className="mt-1.5 text-xs text-muted-foreground">
                                          <span className="font-semibold">Gợi ý: </span>
                                          {stripInternalMarkers(asString(problem.hint))}
                                        </p>
                                      )}
                                      {Boolean(problem.solution) && (
                                        <p className="mt-1 text-xs text-muted-foreground">
                                          <span className="font-semibold">Lời giải: </span>
                                          {stripInternalMarkers(asString(problem.solution))}
                                        </p>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}

                          <SourcesPanel
                            documentId={documentId}
                            sourceChunkIds={lessonObj.source_chunk_ids}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>

      {glossary.length > 0 && (
        <section className="rounded-lg border bg-card p-5">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-semibold">Bảng thuật ngữ ({glossary.length})</h4>
            <button
              type="button"
              onClick={() => setShowGlossary(!showGlossary)}
              className="text-xs font-medium text-primary hover:underline"
            >
              {showGlossary ? "Thu gọn bảng thuật ngữ" : "Xem bảng thuật ngữ"}
            </button>
          </div>
          {showGlossary && (
            <div className="mt-4 grid gap-3 md:grid-cols-2 pt-3 border-t">
              {glossary.map((entry, index) => {
                const item = isObject(entry) ? entry : {};
                return (
                  <div key={index} className="rounded-md border bg-background p-3">
                    <div className="text-sm font-semibold">
                      {asString(item.term, `Thuật ngữ ${index + 1}`)}
                    </div>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">
                      {stripInternalMarkers(
                        asString(item.plain_vietnamese ?? item.definition, "Giải thích đang được cập nhật.")
                      )}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}
    </section>
  );
}
