import { HelpCircle } from "lucide-react";

export function QuizTab() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="rounded-2xl bg-primary/5 p-5 mb-5">
        <HelpCircle className="h-12 w-12 text-primary" />
      </div>
      <h3 className="text-xl font-semibold text-foreground">
        Bài kiểm tra
      </h3>
      <p className="mt-2 text-muted-foreground max-w-md">
        Tạo câu hỏi trắc nghiệm để ôn luyện kiến thức — Sắp ra mắt
      </p>
    </div>
  );
}
