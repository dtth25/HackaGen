"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

interface RedirectIfAuthedProps {
  children: React.ReactNode;
}

export function RedirectIfAuthed({ children }: RedirectIfAuthedProps) {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let mounted = true;
    Promise.resolve().then(() => {
      if (!mounted) return;
      if (isAuthenticated()) {
        router.replace("/courses");
      } else {
        setChecked(true);
      }
    });
    return () => {
      mounted = false;
    };
  }, [router]);

  if (!checked) {
    return null;
  }

  return <>{children}</>;
}
