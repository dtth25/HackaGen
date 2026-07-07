"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, FolderOpen, AlertCircle, RefreshCw } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { CourseCard } from "@/components/course/CourseCard";
import { apiGetCourses } from "@/lib/api";
import type { CourseListItem } from "@/lib/types";

export default function CoursesPage() {
  return (
    <AuthGuard>
      <CoursesContent />
    </AuthGuard>
  );
}

function CoursesContent() {
  const [courses, setCourses] = useState<CourseListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCourses = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGetCourses();
      setCourses(res.courses || []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Không thể tải danh sách khóa học."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    apiGetCourses()
      .then((res) => {
        if (active) {
          setCourses(res.courses || []);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Không thể tải danh sách khóa học."
          );
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:py-12">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground">
            Khóa học của tôi
          </h1>
          <p className="mt-1 text-muted-foreground">
            Quản lý và truy cập các khóa học đã tạo
          </p>
        </div>
        <Link href="/courses/create" className={buttonVariants()}>
          <Plus className="mr-2 h-4 w-4" />
          Tạo mới
        </Link>
      </div>

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-xl border p-6 space-y-3">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-4 w-1/3" />
              <div className="flex gap-2 pt-2">
                <Skeleton className="h-9 flex-1" />
                <Skeleton className="h-9 w-9" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && error && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle className="h-12 w-12 text-destructive mb-4" />
          <h3 className="text-lg font-semibold text-foreground">
            Đã xảy ra lỗi
          </h3>
          <p className="mt-2 text-muted-foreground max-w-md">{error}</p>
          <Button variant="outline" className="mt-6" onClick={fetchCourses}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Thử lại
          </Button>
        </div>
      )}

      {!loading && !error && courses.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="rounded-2xl bg-muted p-6 mb-6">
            <FolderOpen className="h-12 w-12 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold text-foreground">
            Chưa có khóa học nào
          </h3>
          <p className="mt-2 text-muted-foreground max-w-md">
            Tải lên tài liệu để AI tạo bộ học liệu hoàn chỉnh cho bạn.
          </p>
          <Link
            href="/courses/create"
            className={buttonVariants({ className: "mt-6" })}
          >
            <Plus className="mr-2 h-4 w-4" />
            Tạo khóa học đầu tiên
          </Link>
        </div>
      )}

      {!loading && !error && courses.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {courses.map((course) => (
            <CourseCard
              key={course.course_id}
              course={course}
              onDeleted={fetchCourses}
            />
          ))}
        </div>
      )}
    </div>
  );
}
