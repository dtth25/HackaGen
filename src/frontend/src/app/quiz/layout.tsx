import React from "react";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function QuizProtectedLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
