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
import { apiGetCourseStatus } from "@/lib/api";
import type { CourseStatusResponse } from "@/lib/types";
import { normalizeCourseStatus } from "@/lib/types";

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleRefetch = () => {
    if (!params.id) return;
    setLoading(true);
    setError(null);
    apiGetCourseStatus(params.id)
      .then(setCourse)
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
    apiGetCourseStatus(params.id)
      .then((data) => {
        if (active) {
          setCourse(data);
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

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:py-12 space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-12 w-full mt-4" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 text-center">
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
    course.filenames?.[0] ||
    course.filename ||
    `Khóa học ${course.course_id.slice(0, 8)}`;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:py-12">
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

        <div className="flex items-start justify-between gap-4">
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
              {course.quality_score !== undefined &&
                course.quality_score > 0 && (
                  <span>
                    Điểm chất lượng: {course.quality_score}/100
                  </span>
                )}
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
        <TabsList className="w-full justify-start">
          <TabsTrigger value="book" className="gap-1.5">
            📖 Tài liệu
          </TabsTrigger>
          <TabsTrigger value="slide" className="gap-1.5">
            📊 Slide
          </TabsTrigger>
          <TabsTrigger value="quiz" className="gap-1.5">
            ❓ Quiz
          </TabsTrigger>
          <TabsTrigger value="vid" className="gap-1.5">
            🎬 Video
          </TabsTrigger>
        </TabsList>

        <div className="mt-6 rounded-xl border bg-card p-6 min-h-[400px]">
          <TabsContent value="book" className="mt-0">
            <BookTab />
          </TabsContent>
          <TabsContent value="slide" className="mt-0">
            <SlideTab />
          </TabsContent>
          <TabsContent value="quiz" className="mt-0">
            <QuizTab />
          </TabsContent>
          <TabsContent value="vid" className="mt-0">
            <VidTab />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
