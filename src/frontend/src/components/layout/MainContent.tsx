"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { AuthGuard } from "@/components/auth/AuthGuard";

interface MainContentProps {
  children: React.ReactNode;
}

export function MainContent({ children }: MainContentProps) {
  const pathname = usePathname();
  const isPublicRoute = pathname?.startsWith("/login") || pathname?.startsWith("/register");

  return (
    <main className="flex-1 pt-14">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        {isPublicRoute ? children : <AuthGuard>{children}</AuthGuard>}
      </div>
    </main>
  );
}
