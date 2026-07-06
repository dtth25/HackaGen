import React from "react";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function AdminProtectedLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard requireAdmin={true}>{children}</AuthGuard>;
}
