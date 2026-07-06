import React from "react";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function SlidesProtectedLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
