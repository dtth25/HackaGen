import type { Metadata } from "next";
import { Toaster } from "@/components/ui/sonner";
import { Navbar } from "@/components/layout/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";
import { MainContent } from "@/components/layout/MainContent";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Course Generator",
  description:
    "Upload tài liệu (PDF, DOCX, TXT) và để AI tự động tạo khóa học, bài học, tóm tắt, flashcard, quiz, slide và mind map.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Navbar />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <MainContent>{children}</MainContent>
        </div>
        <Toaster richColors position="bottom-right" />
      </body>
    </html>
  );
}
