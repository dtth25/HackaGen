"use client";

import { Video, Construction } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";

interface VidTabProps {
  courseId: string;
}

export function VidTab({ courseId }: VidTabProps) {
  return (
    <div data-course-id={courseId}>
      <EmptyState
        icon={Video}
        title="Video bài giảng"
        description="Tính năng Video đang được hoàn thiện và sẽ sớm có mặt trong Study Pack của bạn."
        expandable
      >
        <Card className="w-full text-left bg-card/50 border-dashed border-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold flex items-center gap-2 text-muted-foreground">
              <Construction className="h-4 w-4 text-muted-foreground" />
              Storyboard &amp; kịch bản video
            </CardTitle>
            <CardDescription>Phân cảnh, lời đọc voiceover và chỉ dẫn hình ảnh</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              <Skeleton className="h-8 w-8 rounded-full" />
              <Skeleton className="h-6 w-1/2 rounded" />
            </div>
            <Skeleton className="h-16 w-full rounded-xl" />
            <div className="flex items-center gap-2 pt-2">
              <Skeleton className="h-8 w-8 rounded-full" />
              <Skeleton className="h-6 w-2/3 rounded" />
            </div>
            <Skeleton className="h-16 w-full rounded-xl" />
          </CardContent>
        </Card>
      </EmptyState>
    </div>
  );
}
