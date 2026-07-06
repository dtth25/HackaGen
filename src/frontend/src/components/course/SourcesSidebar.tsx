"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui";
import { cn } from "@/lib/utils";
import { deleteDocument, getCoursesAll, type CourseListItem } from "@/lib/api";

function statusLabel(status: string): string {
  switch (status) {
    case "ready":
      return "Sẵn sàng";
    case "processing":
    case "pending":
      return "Đang xử lý";
    case "failed":
      return "Lỗi";
    case "paused_due_to_quota":
      return "Tạm dừng";
    default:
      return status;
  }
}

function statusDotClass(status: string): string {
  switch (status) {
    case "ready":
      return "bg-emerald-500";
    case "processing":
    case "pending":
      return "bg-amber-500";
    case "failed":
      return "bg-rose-500";
    default:
      return "bg-muted-foreground";
  }
}

function documentLabel(course: CourseListItem): string {
  if (course.filenames && course.filenames.length > 0) {
    const first = course.filenames[0];
    return course.filenames.length > 1 ? `${first} +${course.filenames.length - 1}` : first;
  }
  return `Tài liệu ${course.course_id.slice(0, 8)}`;
}

export function SourcesSidebar({ activeCourseId }: { activeCourseId?: string }) {
  const router = useRouter();
  const [courses, setCourses] = useState<CourseListItem[] | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getCoursesAll()
      .then((res) => {
        if (!cancelled) setCourses(res.courses ?? []);
      })
      .catch(() => {
        if (!cancelled) setCourses([]);
      });
    return () => {
      cancelled = true;
    };
  }, [activeCourseId]);

  const confirmDelete = async () => {
    if (!deletingId) return;
    setIsDeleting(true);
    try {
      await deleteDocument(deletingId);
      setCourses((prev) => (prev ? prev.filter((c) => c.course_id !== deletingId) : prev));
      toast.success("Đã xóa tài liệu.");
      if (deletingId === activeCourseId) router.push("/generate");
    } catch {
      toast.error("Không thể xóa tài liệu.");
    } finally {
      setIsDeleting(false);
      setDeletingId(null);
    }
  };

  return (
    <aside className="flex h-full flex-col gap-3">
      <div className="flex items-center justify-between px-1">
        <h2 className="text-sm font-semibold text-foreground">Nguồn</h2>
        <Link href="/generate">
          <Button size="sm" variant="ghost" className="h-7 gap-1 px-2 text-xs">
            <Plus className="h-3.5 w-3.5" />
            Thêm
          </Button>
        </Link>
      </div>

      {courses === null && (
        <div className="flex items-center gap-2 rounded-lg border border-dashed p-4 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Đang tải...
        </div>
      )}

      {courses !== null && courses.length === 0 && (
        <div className="rounded-lg border border-dashed p-4 text-center">
          <FileText className="mx-auto mb-2 h-5 w-5 text-muted-foreground" />
          <p className="text-xs font-medium text-foreground">Chưa có tài liệu</p>
          <p className="mt-1 text-xs text-muted-foreground">Thêm PDF, DOCX hoặc TXT để bắt đầu.</p>
        </div>
      )}

      {courses !== null && courses.length > 0 && (
        <ul className="flex-1 space-y-1 overflow-y-auto">
          {courses.map((course) => {
            const isActive = course.course_id === activeCourseId;
            return (
              <li key={course.course_id}>
                <div
                  className={cn(
                    "group flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors",
                    isActive ? "bg-secondary" : "hover:bg-secondary/50",
                  )}
                >
                  <Link
                    href={`/dashboard/${course.course_id}`}
                    className="flex min-w-0 flex-1 items-center gap-2"
                  >
                    <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", statusDotClass(course.status))} />
                    <span className="min-w-0 flex-1">
                      <span className={cn("block truncate", isActive ? "font-medium text-foreground" : "text-foreground/90")}>
                        {documentLabel(course)}
                      </span>
                      <span className="block text-[11px] text-muted-foreground">{statusLabel(course.status)}</span>
                    </span>
                  </Link>
                  <button
                    type="button"
                    onClick={() => setDeletingId(course.course_id)}
                    className="shrink-0 rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                    aria-label="Xóa tài liệu"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <Dialog open={Boolean(deletingId)} onOpenChange={(open) => !open && setDeletingId(null)}>
        <DialogContent className="max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle>Xóa tài liệu này?</DialogTitle>
            <DialogDescription>
              Học liệu đã tạo từ tài liệu này (Sách, quiz, slides, video) sẽ bị xóa. Không thể hoàn tác.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-2 flex gap-2 sm:justify-end">
            <Button variant="outline" disabled={isDeleting} onClick={() => setDeletingId(null)}>
              Hủy
            </Button>
            <Button variant="destructive" disabled={isDeleting} onClick={confirmDelete}>
              {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Xóa"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  );
}

export default SourcesSidebar;
