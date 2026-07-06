import React from "react";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function FlashcardsProtectedLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
