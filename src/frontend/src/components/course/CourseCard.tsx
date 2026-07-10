"use client";

import { useState } from "react";
import Link from "next/link";
import {
  FileText,
  Trash2,
  Pencil,
  ExternalLink,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { apiDeleteCourse, apiRenameCourse } from "@/lib/api";
import type { CourseListItem } from "@/lib/types";
import { normalizeCourseStatus } from "@/lib/types";

interface CourseCardProps {
  course: CourseListItem;
  onDeleted?: () => void;
  onRenamed?: () => void;
}

export function CourseCard({ course, onDeleted, onRenamed }: CourseCardProps) {
  const [deleting, setDeleting] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [renaming, setRenaming] = useState(false);
  const status = normalizeCourseStatus(course.status);

  const statusConfig = {
    processing: {
      label: "Đang xử lý",
      variant: "outline" as const,
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
      className: "border-warning text-warning",
    },
    ready: {
      label: "Sẵn sàng",
      variant: "outline" as const,
      icon: <CheckCircle2 className="h-3 w-3" />,
      className: "border-success text-success",
    },
    error: {
      label: "Lỗi",
      variant: "destructive" as const,
      icon: <AlertCircle className="h-3 w-3" />,
      className: "",
    },
  };

  const cfg = statusConfig[status];

  // AI course-title generation can lag behind (retried lazily by the backend on /status
  // polls, capped at a couple attempts) — while it might still land, show a pending label
  // instead of the raw filename and don't let the user rename over a title that could still
  // show up on its own. Backend flips this off once attempts are exhausted so rename never
  // stays stuck disabled forever.
  const namePending = !!course.name_pending;

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await apiDeleteCourse(course.course_id);
      setDialogOpen(false);
      onDeleted?.();
    } catch {
      // Error handled by API layer
    } finally {
      setDeleting(false);
    }
  };

  const displayName = namePending
    ? "Đang đặt tên..."
    : course.name || course.filenames?.[0] || `Khóa học ${course.course_id.slice(0, 6)}`;
  const exactTime = course.created_at ? formatExactTime(course.created_at) : "";
  const timeAgo = course.created_at ? formatTimeAgo(course.created_at) : "";

  const openRename = () => {
    setRenameValue(displayName);
    setRenameOpen(true);
  };

  const handleRename = async () => {
    const name = renameValue.trim();
    if (!name) return;
    setRenaming(true);
    try {
      await apiRenameCourse(course.course_id, name);
      setRenameOpen(false);
      onRenamed?.();
    } catch {
      // Error handled by API layer
    } finally {
      setRenaming(false);
    }
  };

  return (
    <Card className="flex flex-col transition-shadow hover:shadow-[var(--shadow-md)]">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base font-semibold leading-tight line-clamp-2">
            {displayName}
          </CardTitle>
          <Badge
            variant={cfg.variant}
            className={`shrink-0 gap-1 ${cfg.className}`}
          >
            {cfg.icon}
            {cfg.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex-1 pb-3">
        {course.filenames && course.filenames.length > 0 && (
          <div className="space-y-1">
            {course.filenames.slice(0, 3).map((f) => (
              <p
                key={f}
                className="flex items-center gap-1.5 text-sm text-muted-foreground"
              >
                <FileText className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{f}</span>
              </p>
            ))}
            {course.filenames.length > 3 && (
              <p className="text-xs text-muted-foreground">
                +{course.filenames.length - 3} file khác
              </p>
            )}
          </div>
        )}
        {status === "error" && course.error && (
          <p className="mt-2 flex items-start gap-1.5 text-xs text-destructive">
            <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
            <span className="line-clamp-2">{course.error}</span>
          </p>
        )}
        {timeAgo && (
          <p className="mt-2 text-xs text-muted-foreground">
            Tạo lúc {exactTime} · {timeAgo}
          </p>
        )}
      </CardContent>
      <CardFooter className="gap-2 pt-0">
        {status === "processing" ? (
          <Button variant="default" size="sm" className="flex-1" disabled>
            <ExternalLink className="mr-1 h-3.5 w-3.5" />
            Mở Dashboard
          </Button>
        ) : (
          <Link
            href={`/course/${course.course_id}`}
            className={buttonVariants({
              variant: "default",
              size: "sm",
              className: "flex-1",
            })}
          >
            <ExternalLink className="mr-1 h-3.5 w-3.5" />
            Mở Dashboard
          </Link>
        )}
        <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
          <DialogTrigger
            render={
              <Button
                variant="ghost"
                size="sm"
                onClick={openRename}
                disabled={namePending}
                title={namePending ? "Đợi đặt tên tự động xong đã nhé" : "Đổi tên khóa học"}
              />
            }
          >
            <Pencil className="h-3.5 w-3.5" />
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Đổi tên khóa học</DialogTitle>
              <DialogDescription>
                Đặt tên mới cho khóa học này.
              </DialogDescription>
            </DialogHeader>
            <Input
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              placeholder="Tên khóa học"
              maxLength={200}
              autoFocus
            />
            <DialogFooter>
              <Button variant="ghost" onClick={() => setRenameOpen(false)}>
                Hủy
              </Button>
              <Button
                onClick={handleRename}
                disabled={renaming || !renameValue.trim()}
              >
                {renaming && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Lưu
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger
            render={
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
              />
            }
          >
            <Trash2 className="h-3.5 w-3.5" />
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Xóa khóa học?</DialogTitle>
              <DialogDescription>
                Bạn có chắc muốn xóa khóa học này? Hành động này không thể hoàn
                tác.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setDialogOpen(false)}>
                Hủy
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Xóa
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardFooter>
    </Card>
  );
}

// Backend sends naive UTC timestamps (no "Z"/offset suffix). Without an explicit offset,
// `new Date(...)` parses the string as local time, which skews "time ago" by the local
// UTC offset (e.g. shows "7 giờ trước" right after creation for UTC+7 users).
function parseUtcDate(dateStr: string): Date {
  const hasOffset = /Z$|[+-]\d{2}:\d{2}$/.test(dateStr);
  return new Date(hasOffset ? dateStr : `${dateStr}Z`);
}

function formatExactTime(dateStr: string): string {
  const date = parseUtcDate(dateStr);
  const dd = String(date.getDate()).padStart(2, "0");
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const yyyy = date.getFullYear();
  const hh = String(date.getHours()).padStart(2, "0");
  const min = String(date.getMinutes()).padStart(2, "0");
  return `${dd}/${mm}/${yyyy} ${hh}:${min}`;
}

function formatTimeAgo(dateStr: string): string {
  const date = parseUtcDate(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);
  const diffWeek = Math.floor(diffDay / 7);
  const diffMonth = Math.floor(diffDay / 30);
  const diffYear = Math.floor(diffDay / 365);

  if (diffMin < 1) return "vừa xong";
  if (diffMin < 60) return `${diffMin} phút trước`;
  if (diffHr < 24) return `${diffHr} giờ trước`;
  if (diffDay < 7) return `${diffDay} ngày trước`;
  if (diffWeek < 5) return `${diffWeek} tuần trước`;
  if (diffMonth < 12) return `${diffMonth} tháng trước`;
  return `${diffYear} năm trước`;
}
