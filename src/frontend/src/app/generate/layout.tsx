import React from "react";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function GenerateProtectedLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
