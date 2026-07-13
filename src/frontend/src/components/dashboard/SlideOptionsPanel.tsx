"use client";

import { Loader2, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SlideOptionsPanelProps {
  value: Record<string, never>;
  onChange: (value: Record<string, never>) => void;
  onSubmit: () => void;
  busy: boolean;
  submitLabel: string;
  progress?: number;
  documentProcessing?: boolean;
}

export function SlideOptionsPanel({
  onSubmit,
  busy,
  submitLabel,
  progress = 0,
  documentProcessing = false,
}: SlideOptionsPanelProps) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (!busy && !documentProcessing) onSubmit();
      }}
      className="w-full max-w-sm space-y-2"
    >
      {busy ? (
        <>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${progress}%` }} />
          </div>
          <Button disabled size="lg" className="w-full gap-2 font-semibold">
            <RefreshCw className="h-5 w-5 animate-spin" /> Đang tạo slide ({progress}%)…
          </Button>
        </>
      ) : documentProcessing ? (
        <div className="flex items-center justify-center gap-2 rounded-lg border border-dashed border-border/60 px-4 py-3 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Tài liệu đang được xử lý, vui lòng đợi...
        </div>
      ) : (
        <Button type="submit" size="lg" className="gap-2 font-semibold">
          <Sparkles className="h-5 w-5" /> {submitLabel}
        </Button>
      )}
    </form>
  );
}
