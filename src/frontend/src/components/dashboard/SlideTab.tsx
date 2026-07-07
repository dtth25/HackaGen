import { Presentation } from "lucide-react";

export function SlideTab() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="rounded-2xl bg-primary/5 p-5 mb-5">
        <Presentation className="h-12 w-12 text-primary" />
      </div>
      <h3 className="text-xl font-semibold text-foreground">
        Bài trình chiếu
      </h3>
      <p className="mt-2 text-muted-foreground max-w-md">
        Tạo slide trình chiếu chuyên nghiệp từ nội dung khóa học — Sắp ra mắt
      </p>
    </div>
  );
}
