"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  FileText,
  AlertCircle,
  Loader2,
  CheckCircle2,
  RefreshCw,
  BookOpen,
  Presentation,
  HelpCircle,
  Video,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { BookTab } from "@/components/dashboard/BookTab";
import { SlideTab } from "@/components/dashboard/SlideTab";
import { QuizTab } from "@/components/dashboard/QuizTab";
import { VidTab } from "@/components/dashboard/VidTab";
import { QualityScoreBadge } from "@/components/ui/QualityScoreBadge";
import { apiGetCourseStatus, apiGetStudyPack } from "@/lib/api";
import type { CourseStatusResponse, StudyPackResponse } from "@/lib/types";
import { normalizeCourseStatus } from "@/lib/types";
import { CONTAINER_NARROW } from "@/lib/layout";
import { cn } from "@/lib/utils";
import { DEFAULT_POLL_MS } from "@/hooks/usePollingArtifact";

export default function CourseDashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}

function DashboardContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [course, setCourse] = useState<CourseStatusResponse | null>(null);
  const [studyPack, setStudyPack] = useState<StudyPackResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleRefetch = () => {
    if (!params.id) return;
    setLoading(true);
    setError(null);
    Promise.all([
      apiGetCourseStatus(params.id),
      apiGetStudyPack(params.id).catch(() => null),
    ])
      .then(([statusData, packData]) => {
        setCourse(statusData);
        setStudyPack(packData);
      })
      .catch((err) =>
        setError(
          err instanceof Error
            ? err.message
            : "Không thể tải thông tin khóa học."
        )
      )
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!params.id) return;
    let active = true;
    Promise.all([
      apiGetCourseStatus(params.id),
      apiGetStudyPack(params.id).catch(() => null),
    ])
      .then(([statusData, packData]) => {
        if (active) {
          setCourse(statusData);
          setStudyPack(packData);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Không thể tải thông tin khóa học."
          );
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [params.id]);

  useEffect(() => {
    if (!params.id || !course) return;
    const isProcessing = course.status === "processing";
    if (!isProcessing) return;

    const interval = setInterval(async () => {
      try {
        const [statusData, packData] = await Promise.all([
          apiGetCourseStatus(params.id),
          apiGetStudyPack(params.id).catch(() => null),
        ]);
        setCourse(statusData);
        setStudyPack(packData);
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, DEFAULT_POLL_MS);

    return () => clearInterval(interval);
  }, [course, params.id]);

  if (loading) {
    return (
      <div className={cn(CONTAINER_NARROW, "py-8 sm:py-12 space-y-6")}>
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-12 w-full mt-4" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn(CONTAINER_NARROW, "py-16 text-center")}>
        <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-foreground">
          Không tìm thấy khóa học
        </h2>
        <p className="mt-2 text-muted-foreground max-w-md mx-auto">
          {error}
        </p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <Button
            variant="outline"
            onClick={() => router.push("/courses")}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Quay lại
          </Button>
          <Button variant="outline" onClick={handleRefetch}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Thử lại
          </Button>
        </div>
      </div>
    );
  }

  if (!course) return null;

  const status = normalizeCourseStatus(course.status);
  const statusConfig = {
    processing: {
      label: "Đang xử lý",
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
      className: "border-warning text-warning",
    },
    ready: {
      label: "Sẵn sàng",
      icon: <CheckCircle2 className="h-3 w-3" />,
      className: "border-success text-success",
    },
    error: {
      label: "Lỗi",
      icon: <AlertCircle className="h-3 w-3" />,
      className: "",
    },
  };
  const cfg = statusConfig[status];
  const displayTitle =
    course.name ||
    course.filenames?.[0] ||
    course.filename ||
    `Khóa học ${course.course_id.slice(0, 8)}`;

  return (
    <div className={cn(CONTAINER_NARROW, "py-8 sm:py-12")}>
      {/* Course Header */}
      <div className="mb-8">
        <Button
          variant="ghost"
          size="sm"
          className="mb-4 -ml-2 text-muted-foreground"
          onClick={() => router.push("/courses")}
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          Khóa học của tôi
        </Button>

        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground">
              {displayTitle}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              {course.filenames && course.filenames.length > 0 && (
                <span className="flex items-center gap-1">
                  <FileText className="h-3.5 w-3.5" />
                  {course.filenames.length} file
                </span>
              )}
              {course.quality_score !== undefined && course.quality_score > 0 ? (
                <QualityScoreBadge score={course.quality_score} />
              ) : studyPack?.study_pack?.grounding?.quality_score ? (
                <QualityScoreBadge
                  score={studyPack.study_pack.grounding.quality_score}
                />
              ) : null}
            </div>
          </div>
          <Badge
            variant="outline"
            className={`shrink-0 gap-1 ${cfg.className}`}
          >
            {cfg.icon}
            {cfg.label}
          </Badge>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="book" className="w-full">
        <TabsList className="w-full justify-start flex-wrap h-auto gap-1 p-1 bg-muted/60">
          <TabsTrigger value="book" className="gap-1.5">
            <BookOpen className="h-4 w-4" /> Study Guide
          </TabsTrigger>
          <TabsTrigger value="slide" className="gap-1.5">
            <Presentation className="h-4 w-4" /> Slide
          </TabsTrigger>
          <TabsTrigger value="quiz" className="gap-1.5">
            <HelpCircle className="h-4 w-4" /> Quiz
          </TabsTrigger>
          <TabsTrigger value="vid" className="gap-1.5">
            <Video className="h-4 w-4" /> Video
          </TabsTrigger>
        </TabsList>

        <div className="mt-6 rounded-xl border bg-card p-6 min-h-[400px]">
          <TabsContent value="book" className="mt-0">
            <BookTab courseId={course.course_id} documentProcessing={status === "processing"} />
          </TabsContent>
          <TabsContent value="slide" className="mt-0">
            <SlideTab courseId={course.course_id} documentProcessing={status === "processing"} />
          </TabsContent>
          <TabsContent value="quiz" className="mt-0">
            <QuizTab courseId={course.course_id} documentProcessing={status === "processing"} />
          </TabsContent>
          <TabsContent value="vid" className="mt-0">
            <VidTab courseId={course.course_id} documentProcessing={status === "processing"} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
