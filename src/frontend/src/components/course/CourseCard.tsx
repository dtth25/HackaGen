"use client";

import { useState } from "react";
import Link from "next/link";
import {
  FileText,
  Trash2,
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { apiDeleteCourse } from "@/lib/api";
import type { CourseListItem } from "@/lib/types";
import { normalizeCourseStatus } from "@/lib/types";

interface CourseCardProps {
  course: CourseListItem;
  onDeleted?: () => void;
}

export function CourseCard({ course, onDeleted }: CourseCardProps) {
  const [deleting, setDeleting] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
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

  const displayName =
    course.filenames?.[0] || `Khóa học ${course.course_id.slice(0, 6)}`;
  const timeAgo = course.created_at ? formatTimeAgo(course.created_at) : "";

  return (
    <Card className="flex flex-col transition-shadow hover:shadow-md">
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
        {timeAgo && (
          <p className="mt-2 text-xs text-muted-foreground">
            Tạo lúc {timeAgo}
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

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffMin < 1) return "vừa xong";
  if (diffMin < 60) return `${diffMin} phút trước`;
  if (diffHr < 24) return `${diffHr} giờ trước`;
  if (diffDay < 30) return `${diffDay} ngày trước`;
  return date.toLocaleDateString("vi-VN");
}
