import Link from "next/link";
import { BookOpen } from "lucide-react";

export default function AuthLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="min-h-screen flex">
      {/* Left branding - hidden on mobile */}
      <div className="hidden md:flex md:w-[35%] lg:w-[30%] flex-col items-center justify-center bg-primary p-8 text-primary-foreground">
        <Link href="/" className="flex items-center gap-3 mb-6">
          <BookOpen className="h-10 w-10" />
          <span className="text-2xl font-bold">ACG</span>
        </Link>
        <p className="text-center text-lg font-medium leading-relaxed opacity-90">
          Biến tài liệu thành
          <br />
          bộ học liệu hoàn chỉnh
        </p>
      </div>

      {/* Right form */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-8">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="md:hidden flex items-center justify-center gap-2 mb-8">
            <Link
              href="/"
              className="flex items-center gap-2 text-foreground"
            >
              <BookOpen className="h-8 w-8 text-primary" />
              <span className="text-xl font-bold">AI Course Generator</span>
            </Link>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
