import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import { Navbar } from "@/components/layout/Navbar";
import { MainContent } from "@/components/layout/MainContent";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { DocumentTitleProvider } from "@/components/layout/DocumentTitleContext";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Study Pack AI",
  description: "Tạo Sách, Mindmap, Quiz và Flashcards từ tài liệu của bạn.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className={`dark ${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <DocumentTitleProvider>
          <Navbar />
          <div className="flex flex-1">
            <MainContent>{children}</MainContent>
          </div>
          <SiteFooter />
        </DocumentTitleProvider>
        <Toaster richColors position="bottom-right" />
      </body>
    </html>
  );
}
