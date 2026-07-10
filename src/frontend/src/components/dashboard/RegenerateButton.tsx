"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface RegenerateButtonProps {
  /** Vietnamese noun phrase describing the artifact, e.g. "sách ôn tập", "bộ slide". */
  label: string;
  regenUsed: number | null;
  regenMax: number | null;
  /** True while a generation job is already in flight — disables the trigger. */
  busy?: boolean;
  onConfirm: () => void;
}

export function RegenerateButton({ label, regenUsed, regenMax, busy, onConfirm }: RegenerateButtonProps) {
  const [open, setOpen] = useState(false);
  const known = regenUsed !== null && regenMax !== null;
  const remaining = known ? Math.max(0, (regenMax as number) - (regenUsed as number)) : null;
  const exhausted = known && remaining === 0;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button
            variant="outline"
            className="gap-1.5"
            disabled={busy || exhausted}
            title={exhausted ? `Đã hết lượt tạo lại cho ${label}` : undefined}
          />
        }
      >
        <RefreshCw className="h-4 w-4" />
        Tạo lại{known ? ` (còn ${remaining}/${regenMax})` : ""}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Tạo lại {label}?</DialogTitle>
          <DialogDescription>
            Nội dung {label} hiện tại sẽ được thay thế bằng bản mới.
            {known && ` Bạn còn ${remaining}/${regenMax} lượt tạo lại cho mục này.`}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Hủy
          </Button>
          <Button
            onClick={() => {
              setOpen(false);
              onConfirm();
            }}
            className="gap-1.5"
          >
            <RefreshCw className="h-4 w-4" /> Tạo lại
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
