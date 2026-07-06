import Link from "next/link";
import { getCoursesAll } from "@/lib/api";
import { Button } from "@/components/ui";

export default async function QuizLandingPage() {
  let courses: Awaited<ReturnType<typeof getCoursesAll>>["courses"] = [];

  try {
    const data = await getCoursesAll();
    courses = data.courses ?? [];
  } catch {
    // API chưa sẵn sàng — render danh sách rỗng
  }

  return (
    <div className="space-y-8">
      <div className="border-b border-border/60 pb-5">
        <h1 className="text-3xl font-extrabold tracking-tight text-foreground">
          Làm Quiz Trắc Nghiệm
        </h1>
        <p className="mt-1.5 text-base text-muted-foreground">
          Chọn bộ tài liệu đã xử lý để hệ thống AI sinh bài kiểm tra và đáp án chi tiết cho bạn.
        </p>
      </div>

      {courses.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-card/50 py-20 text-center shadow-sm">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-rose-500/10 text-rose-500">
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 002-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-foreground">Chưa có bài Quiz nào</h3>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Hãy tải lên tài liệu mới để bắt đầu tạo các bài thi trắc nghiệm AI ôn tập kiến thức.
          </p>
          <Link href="/generate" className="mt-6">
            <Button size="lg" className="shadow-md">Tải tài liệu ngay</Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {courses.map((course) => (
            <div
              key={course.course_id}
              className="flex flex-col rounded-xl border border-border bg-card p-5 shadow-sm transition-all hover:shadow-md"
            >
              <div className="flex-1 space-y-2.5">
                <h3 className="text-base font-semibold text-foreground">
                  Tài liệu {course.course_id.slice(0, 8)}...
                </h3>
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  Trạng thái:{" "}
                  <span
                    className={
                      course.status === "ready"
                        ? "text-emerald-600 font-semibold"
                        : "text-amber-600 font-semibold"
                    }
                  >
                    {course.status === "ready" ? "Sẵn sàng" : course.status}
                  </span>
                </p>
                {course.created_at && (
                  <p className="text-xs text-muted-foreground">
                    Tạo ngày: {course.created_at}
                  </p>
                )}
              </div>
              <div className="mt-4">
                <Link href={`/quiz/${course.course_id}`} className="w-full">
                  <Button
                    className="w-full shadow-sm"
                    disabled={course.status !== "ready"}
                  >
                    {course.status === "ready" ? "Làm quiz ngay" : "Đang xử lý..."}
                  </Button>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
