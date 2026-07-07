import { BookOpen } from "lucide-react";

export function BookTab() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="rounded-2xl bg-primary/5 p-5 mb-5">
        <BookOpen className="h-12 w-12 text-primary" />
      </div>
      <h3 className="text-xl font-semibold text-foreground">
        Tài liệu học tập
      </h3>
      <p className="mt-2 text-muted-foreground max-w-md">
        Tạo tài liệu học tập chi tiết từ nội dung khóa học — Sắp ra mắt
      </p>
    </div>
  );
}
