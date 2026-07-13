"use client";

import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface RegenerateButtonProps {
  /** Vietnamese noun phrase describing the artifact, e.g. "sách ôn tập", "bộ slide". */
  label: string;
  regenUsed?: number | null;
  regenMax?: number | null;
  /** True while a generation job is already in flight — disables the trigger. */
  busy?: boolean;
  onOpen: () => void;
}

export function RegenerateButton({ label, busy, onOpen }: RegenerateButtonProps) {

  return (
    <Button
      variant="outline"
      className="gap-1.5"
      disabled={busy}
      onClick={onOpen}
    >
      <Plus className="h-4 w-4" />
      Tạo mới {label}
    </Button>
  );
}
