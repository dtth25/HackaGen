"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Trash2, Loader2, BookOpen, LogIn } from "lucide-react";
import { toast } from "sonner";
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui";
import { deleteDocument, getCoursesAll } from "@/lib/api";

interface CourseItem {
  course_id: string;
  status: string;
  created_at?: string | number;
}

export function CourseListClient() {
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [needsLogin] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getCoursesAll()
      .then((data) => {
        if (!cancelled) setCourses(data.courses ?? []);
      })
      .catch(() => {
        if (!cancelled) toast.error("Không thể tải danh sách tài liệu. Vui lòng thử lại sau.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const confirmDelete = async () => {
    if (!deletingId) return;
    setIsDeleting(true);
    try {
      await deleteDocument(deletingId);
      setCourses((prev) => prev.filter((c) => c.course_id !== deletingId));
      toast.success("Đã xóa tài liệu và học liệu liên quan.");
    } catch {
      toast.error("Không thể xóa tài liệu. Vui lòng thử lại sau.");
    } finally {
      setIsDeleting(false);
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-border bg-card/50 py-20 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Đang tải tài liệu của bạn...
      </div>
    );
  }

  if (needsLogin) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-card/50 py-20 text-center shadow-sm">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
          <LogIn className="h-8 w-8" />
        </div>
        <h3 className="text-lg font-semibold text-foreground">Đăng nhập để xem tài liệu của bạn</h3>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          Tài liệu của bạn được giữ riêng tư — chỉ tài khoản của bạn mới xem được sau khi đăng nhập.
        </p>
        <Link href="/login" className="mt-6">
          <Button size="lg" className="shadow-md">Đăng nhập</Button>
        </Link>
      </div>
    );
  }

  if (courses.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-card/50 py-20 text-center shadow-sm">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
          <BookOpen className="h-8 w-8" />
        </div>
        <h3 className="text-lg font-semibold text-foreground">Chưa có tài liệu nào</h3>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          Tải lên file PDF, DOCX hoặc TXT để AI bắt đầu phân tích và tạo bộ học liệu tự động cho bạn.
        </p>
        <Link href="/generate" className="mt-6">
          <Button size="lg" className="shadow-md">Tải tài liệu ngay</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => {
          const courseLabel =
            course.status === "ready"
              ? `Tài liệu ${course.course_id.slice(0, 8)}...`
              : `Tài liệu ${course.course_id.slice(0, 8)}... (${
                  course.status === "processing" ? "đang xử lý" : course.status
                })`;

          return (
            <Card key={course.course_id} className="flex flex-col justify-between transition-shadow hover:shadow-md">
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-lg text-foreground">{courseLabel}</CardTitle>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-rose-600 hover:bg-rose-500/10"
                    onClick={() => setDeletingId(course.course_id)}
                    title="Xóa tài liệu này"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                {course.created_at && (
                  <CardDescription className="text-xs">
                    Tạo ngày: {course.created_at}
                  </CardDescription>
                )}
                <CardDescription className="text-xs">
                  Trạng thái:{" "}
                  <span
                    className={
                      course.status === "ready"
                        ? "text-emerald-600 font-semibold"
                        : "text-amber-600 font-medium"
                    }
                  >
                    {course.status}
                  </span>
                </CardDescription>
              </CardHeader>
              <CardFooter className="mt-auto pt-2">
                <Link href={`/course/${course.course_id}`} className="w-full">
                  <Button className="w-full font-semibold shadow-sm">Mở Study Pack</Button>
                </Link>
              </CardFooter>
            </Card>
          );
        })}
      </div>

      <Dialog open={!!deletingId} onOpenChange={(open) => !open && setDeletingId(null)}>
        <DialogContent className="max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-rose-600 font-bold">
              <Trash2 className="h-5 w-5" />
              Xác nhận xóa tài liệu
            </DialogTitle>
            <DialogDescription className="pt-2 text-sm text-muted-foreground leading-relaxed">
              Bạn có chắc muốn xóa tài liệu này? Hành động này sẽ xóa các học liệu đã tạo từ tài liệu (file gốc, trích xuất TXT/JSON, vector store và các file video/slides).
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4 flex gap-2 sm:justify-end">
            <Button variant="outline" disabled={isDeleting} onClick={() => setDeletingId(null)}>
              Hủy
            </Button>
            <Button variant="destructive" disabled={isDeleting} onClick={confirmDelete}>
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
