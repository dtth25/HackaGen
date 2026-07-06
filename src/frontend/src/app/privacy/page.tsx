import React from "react";
import Link from "next/link";
import { ShieldCheck, Lock, Trash2, Sparkles, AlertTriangle, ChevronLeft } from "lucide-react";

export default function PrivacyPolicyPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-8 py-8 px-4">
      <div className="space-y-3">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          Quay lại trang chủ
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-600">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-foreground">
              Chính Sách Bảo Mật & Quyền Riêng Tư (Privacy & Trust Layer)
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Cam kết minh bạch về cách thức xử lý tài liệu, trích xuất dữ liệu gốc và quyền kiểm soát của bạn.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {/* Section 1 */}
        <div className="rounded-2xl border border-border/80 bg-card p-6 shadow-sm space-y-3">
          <div className="flex items-center gap-2.5 text-lg font-bold text-foreground">
            <Lock className="h-5 w-5 text-emerald-500" />
            1. Tài liệu tải lên & Xử lý nội bộ
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Khi bạn tải lên tài liệu (PDF, DOCX, TXT), hệ thống sử dụng file đó để trích xuất văn bản, tạo embedding và sinh Study Pack như Sách, Mindmap, Flashcards và Quiz. Ở chế độ local/dev, file và output được lưu trong storage cấu hình của ứng dụng; ở môi trường production sau này, chính sách lưu trữ sẽ phụ thuộc provider được bật.
          </p>
        </div>

        {/* Section 2 */}
        <div className="rounded-2xl border border-border/80 bg-card p-6 shadow-sm space-y-3">
          <div className="flex items-center gap-2.5 text-lg font-bold text-foreground">
            <Sparkles className="h-5 w-5 text-primary" />
            2. Nguyên tắc Grounded AI (Xác thực nguồn)
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Hệ thống dùng Retrieval-Augmented Generation (RAG) với Vector DB để ưu tiên các đoạn nguồn trong tài liệu của bạn khi tạo học liệu. Một số output có thể hiển thị panel &ldquo;Xem nguồn được dùng&rdquo; với excerpt ngắn và số trang nếu có; mã chunk nội bộ chỉ nên bật trong developer mode.
          </p>
        </div>

        {/* Section 3 */}
        <div className="rounded-2xl border border-border/80 bg-card p-6 shadow-sm space-y-3">
          <div className="flex items-center gap-2.5 text-lg font-bold text-foreground">
            <Trash2 className="h-5 w-5 text-amber-500" />
            3. Quyền tự do xóa tài liệu bất cứ lúc nào
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Khi bạn nhấn nút <strong>&ldquo;Xóa tài liệu&rdquo;</strong>, hệ thống sẽ xóa các dữ liệu do ứng dụng đang quản lý cho document đó khi có thể:
          </p>
          <ul className="list-disc pl-6 text-sm text-muted-foreground space-y-1">
            <li>Xóa file gốc tải lên trong local/file storage của ứng dụng.</li>
            <li>Xóa dữ liệu trích xuất, metadata và cache document hash liên quan nếu có.</li>
            <li>Gỡ các đoạn embedding của document khỏi Vector DB provider đang cấu hình.</li>
            <li>Xóa các học liệu phái sinh như Sách PDF, video, slide và quiz trong output storage.</li>
          </ul>
          <p className="text-xs leading-5 text-muted-foreground">
            Việc xóa này không đại diện cho backup ngoài hệ thống, log của nhà cung cấp hạ tầng, hoặc bản sao bạn đã tải xuống trước đó.
          </p>
        </div>

        {/* Section 4 */}
        <div className="rounded-2xl border border-border/80 bg-card p-6 shadow-sm space-y-3">
          <div className="flex items-center gap-2.5 text-lg font-bold text-foreground">
            <AlertTriangle className="h-5 w-5 text-rose-500" />
            4. Giới hạn của trí tuệ nhân tạo (AI Limitations)
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Nội dung do AI tạo có thể có sai sót trong diễn giải, tóm tắt, công thức hoặc số liệu. Vui lòng đối chiếu các thông tin quan trọng với tài liệu gốc trước khi sử dụng trong kỳ thi, nghiên cứu hoặc môi trường học thuật chính thức.
          </p>
          <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 p-3.5 text-xs text-amber-800 dark:text-amber-300 font-medium">
            Khuyến nghị: Không tải lên tài liệu chứa thông tin rất nhạy cảm như mật khẩu, giấy tờ định danh, dữ liệu bí mật hoặc tài liệu bạn không có quyền sử dụng, trừ khi bạn chấp nhận rủi ro.
          </div>
        </div>
      </div>
    </div>
  );
}
