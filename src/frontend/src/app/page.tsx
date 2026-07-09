import type { Metadata } from "next";
import Link from "next/link";
import {
  BookOpen,
  Presentation,
  HelpCircle,
  Video,
  ArrowRight,
} from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { RedirectIfAuthed } from "@/components/auth/RedirectIfAuthed";

export const metadata: Metadata = {
  title: "AI Course Generator — Biến tài liệu thành bộ học liệu AI",
  description:
    "Tự động biến tài liệu PDF, DOCX, TXT thành tài liệu học tập, slide, bài kiểm tra và video với AI.",
};

const features = [
  {
    icon: BookOpen,
    title: "Tài liệu học tập",
    description:
      "Tạo study guide chi tiết với tóm tắt, giải thích và bài tập",
  },
  {
    icon: Presentation,
    title: "Bài trình chiếu",
    description:
      "Slide chuyên nghiệp sẵn sàng trình bày, tải xuống PPTX",
  },
  {
    icon: HelpCircle,
    title: "Bài kiểm tra",
    description:
      "Câu hỏi trắc nghiệm để ôn luyện và đánh giá kiến thức",
  },
  {
    icon: Video,
    title: "Video bài giảng",
    description:
      "Video học tập với voiceover tự động từ nội dung",
  },
];

export default function WelcomePage() {
  return (
    <RedirectIfAuthed>
      <div className="flex flex-col">
        {/* Hero Section */}
        <section className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-primary/[0.03] to-transparent" />

          <div className="relative mx-auto max-w-4xl px-4 py-24 sm:py-32 text-center">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground">
              Học thông minh hơn
              <span className="block text-primary mt-2">với AI</span>
            </h1>
            <p className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
              Biến tài liệu của bạn thành bộ học liệu hoàn chỉnh — tài liệu học
              tập, slide trình chiếu, bài kiểm tra và video bài giảng.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/register"
                className={buttonVariants({
                  size: "lg",
                  className: "text-base px-8",
                })}
              >
                Bắt đầu ngay
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <Link
                href="/login"
                className={buttonVariants({
                  size: "lg",
                  variant: "outline",
                  className: "text-base px-8",
                })}
              >
                Đăng nhập
              </Link>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="mx-auto max-w-6xl px-4 pb-24">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="group rounded-xl border bg-card p-6 transition-all hover:shadow-lg hover:border-primary/20 hover:-translate-y-1"
              >
                <div className="rounded-lg bg-primary/5 p-3 w-fit mb-4 group-hover:bg-primary/10 transition-colors">
                  <feature.icon className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-semibold text-foreground">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </RedirectIfAuthed>
  );
}
