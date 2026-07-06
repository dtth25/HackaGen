import { CourseListClient } from "@/components/course/CourseListClient";

// Auth tokens only live in browser localStorage (see src/lib/auth.ts), and the
// backend now requires a logged-in user to list documents (privacy: users only
// see their own). A server-side fetch here would never carry the Authorization
// header and would always 401, so course loading happens client-side instead.
export default function CourseListPage() {
  return (
    <div className="space-y-8">
      <div className="border-b border-border/60 pb-5">
        <h1 className="text-3xl font-extrabold tracking-tight text-foreground">
          Tài liệu của tôi
        </h1>
        <p className="mt-1.5 text-base text-muted-foreground">
          Quản lý tài liệu đã tải lên và các Study Pack được sinh bằng RAG.
        </p>
      </div>

      <CourseListClient />
    </div>
  );
}
