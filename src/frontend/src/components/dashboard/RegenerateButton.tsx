"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface RegenerateButtonProps {
  /** Vietnamese noun phrase describing the artifact, e.g. "sách ôn tập", "bộ slide". */
  label: string;
  regenUsed: number | null;
  regenMax: number | null;
  /** True while a generation job is already in flight — disables the trigger. */
  busy?: boolean;
  onOpen: () => void;
}

export function RegenerateButton({ label, regenUsed, regenMax, busy, onOpen }: RegenerateButtonProps) {
  const known = regenUsed !== null && regenMax !== null;
  const remaining = known ? Math.max(0, (regenMax as number) - (regenUsed as number)) : null;
  const exhausted = known && remaining === 0;

  return (
    <Button
      variant="outline"
      className="gap-1.5"
      disabled={busy || exhausted}
      title={exhausted ? `Đã hết lượt tạo lại cho ${label}` : undefined}
      onClick={onOpen}
    >
      <RefreshCw className="h-4 w-4" />
      Tạo lại{known ? ` (còn ${remaining}/${regenMax})` : ""}
    </Button>
  );
}
