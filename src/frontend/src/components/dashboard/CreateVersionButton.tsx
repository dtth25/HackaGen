"use client";

import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CreateVersionButtonProps {
  label: string;
  busy?: boolean;
  onOpen: () => void;
}

export function CreateVersionButton({ label, busy = false, onOpen }: CreateVersionButtonProps) {
  return (
    <Button type="button" variant="outline" className="gap-1.5" disabled={busy} onClick={onOpen}>
      <Plus className="h-4 w-4" />
      Tạo mới {label}
    </Button>
  );
}
