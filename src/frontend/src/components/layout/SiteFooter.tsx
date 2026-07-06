import Link from "next/link";
import { GraduationCap, MessageCircle, ShieldCheck, Users } from "lucide-react";

/**
 * Real project footer: who built this, how to reach us, and what the app
 * honestly promises. No invented testimonials, no inflated claims.
 */
export function SiteFooter() {
  return (
    <footer className="mt-12 border-t border-border/60 bg-card/40">
      <div className="mx-auto grid w-full max-w-7xl gap-8 px-4 py-8 text-sm sm:grid-cols-3">
        <div className="space-y-2">
          <div className="flex items-center gap-2 font-semibold text-foreground">
            <GraduationCap className="h-4 w-4 text-primary" />
            Study Pack AI
          </div>
          <p className="text-xs leading-relaxed text-muted-foreground">
            Đồ án dự thi DTTH Hackathon 2026: biến một tài liệu bạn tải lên thành bộ
            học liệu có trích dẫn nguồn — Sách, Mindmap, Quiz, Flashcards,
            Slides và Video. Kết quả tốt nhất với PDF có lớp văn bản, từ 5 trang trở lên.
          </p>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 font-semibold text-foreground">
            <Users className="h-4 w-4 text-primary" />
            Nhóm phát triển
          </div>
          <ul className="space-y-1 text-xs text-muted-foreground">
            <li>Ngo Duc Minh</li>
            <li>Dang Duc Luong</li>
          </ul>
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <MessageCircle className="h-3.5 w-3.5" />
            Discord: <span className="font-mono text-foreground/80">ilovesingqui._.</span>
          </p>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 font-semibold text-foreground">
            <ShieldCheck className="h-4 w-4 text-primary" />
            Cam kết với người dùng
          </div>
          <ul className="space-y-1 text-xs leading-relaxed text-muted-foreground">
            <li>Tài liệu của bạn được giữ riêng tư và xóa được bất cứ lúc nào.</li>
            <li>Nội dung tạo ra luôn kèm trích đoạn nguồn từ chính file của bạn.</li>
            <li>AI có thể sai — hãy đối chiếu thông tin quan trọng với tài liệu gốc.</li>
          </ul>
          <Link href="/privacy" className="inline-block text-xs font-medium text-primary hover:underline">
            Chính sách quyền riêng tư
          </Link>
        </div>
      </div>
    </footer>
  );
}
