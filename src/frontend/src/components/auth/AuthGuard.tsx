"use client";

import React, { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { fetchCurrentUser, getStoredUser } from "@/lib/auth";
import { Loader2 } from "lucide-react";

interface AuthGuardProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export function AuthGuard({ children, requireAdmin = false }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    let active = true;

    async function checkAuth() {
      // Step 1: Quick synchronous role hint via localStorage, then validate
      // against backend. Backend may also authenticate through HttpOnly cookie.
      const cachedUser = getStoredUser();
      if (requireAdmin && cachedUser && cachedUser.role !== "admin") {
        router.replace("/course");
        return;
      }

      // Step 2: Validate token and fetch latest user state from backend
      const user = await fetchCurrentUser();
      if (!active) return;

      if (!user) {
        const redirectUrl = pathname ? `/login?redirect=${encodeURIComponent(pathname)}` : "/login";
        router.replace(redirectUrl);
        return;
      }

      if (requireAdmin && user.role !== "admin") {
        router.replace("/course");
        return;
      }

      setAuthorized(true);
    }

    checkAuth();

    return () => {
      active = false;
    };
  }, [router, pathname, requireAdmin]);

  if (!authorized) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center gap-3 bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm font-medium text-muted-foreground animate-pulse">
          Đang xác thực quyền truy cập...
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
