import type { Metadata } from "next";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { UploadZone } from "@/components/course/UploadZone";

export const metadata: Metadata = {
  title: "Tạo khóa học mới",
  description:
    "Tải lên tài liệu PDF, DOCX hoặc TXT để AI tạo bộ học liệu hoàn chỉnh.",
};

export default function CreateCoursePage() {
  return (
    <AuthGuard>
      <div className="mx-auto max-w-2xl px-4 py-8 sm:py-12">
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground">
            Tạo khóa học mới
          </h1>
          <p className="mt-2 text-muted-foreground">
            Tải lên tài liệu để AI phân tích và tạo bộ học liệu hoàn chỉnh.
          </p>
        </div>
        <UploadZone />
      </div>
    </AuthGuard>
  );
}
