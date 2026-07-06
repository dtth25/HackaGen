"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { GraduationCap, BookOpen, Plus, User, LogIn, Shield, LogOut, UserPlus } from "lucide-react";
import { cn } from "@/lib/utils";
import { getStoredUser, fetchCurrentUser, logout, UserPublic } from "@/lib/auth";

import { useDocumentTitle } from "@/components/layout/DocumentTitleContext";

const NAV_LINKS = [
  { href: "/generate", label: "Thêm tài liệu", icon: Plus },
  { href: "/course", label: "Tài liệu", icon: BookOpen },
] as const;

export function Navbar() {
  const pathname = usePathname();
  const [user, setUser] = useState<UserPublic | null>(() => getStoredUser());
  const documentTitle = useDocumentTitle();

  useEffect(() => {
    let cancelled = false;
    fetchCurrentUser().then((u) => {
      if (!cancelled) setUser(u);
    });
    return () => {
      cancelled = true;
    };
  }, [pathname]);

  const handleLogout = async () => {
    await logout();
    setUser(null);
    window.location.href = "/login";
  };


  return (
    <header className="fixed top-0 z-50 flex h-14 w-full items-center border-b border-border/60 bg-background/80 px-4 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between">
        <Link href="/generate" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <GraduationCap className="h-4.5 w-4.5" />
          </div>
          <span className="text-sm font-semibold tracking-tight text-foreground">Study Pack AI</span>
        </Link>

        {documentTitle && (
          <span className="hidden md:inline-flex items-center truncate max-w-[280px] px-3 text-sm text-muted-foreground">
            <span className="mr-2 text-border">/</span>
            <span className="truncate font-medium text-foreground">{documentTitle}</span>
          </span>
        )}

        <nav className="flex items-center gap-1 sm:gap-1.5">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href || pathname?.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            );
          })}

          <div className="mx-1 h-5 w-px bg-border/60" />

          {user ? (
            <div className="flex items-center gap-1.5">
              {user.role === "admin" && (
                <Link
                  href="/admin/users"
                  className="inline-flex items-center gap-1.5 rounded-lg bg-purple-500/10 px-3 py-1.5 text-xs font-semibold text-purple-600 dark:text-purple-300 transition-colors hover:bg-purple-500/20"
                >
                  <Shield className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Admin</span>
                </Link>
              )}
              <Link
                href="/account"
                className="inline-flex items-center gap-2 rounded-lg bg-secondary/80 px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-secondary"
              >
                <User className="h-4 w-4 text-muted-foreground" />
                <span className="max-w-[120px] truncate">{user.full_name || user.email.split("@")[0]}</span>
              </Link>
              <button
                onClick={handleLogout}
                title="Đăng xuất"
                className="inline-flex items-center justify-center rounded-lg p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5">
              <Link
                href="/login"
                className="inline-flex items-center gap-1.5 rounded-lg bg-secondary px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-secondary/80"
              >
                <LogIn className="h-4 w-4" />
                <span>Đăng nhập</span>
              </Link>
              <Link
                href="/register"
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-1.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
              >
                <UserPlus className="h-4 w-4" />
                <span className="hidden sm:inline">Đăng ký</span>
              </Link>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
