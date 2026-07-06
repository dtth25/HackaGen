import React from "react";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function MindmapProtectedLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
