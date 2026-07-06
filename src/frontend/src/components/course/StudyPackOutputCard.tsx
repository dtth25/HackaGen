"use client";

import React from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type OutputStatus = "ready" | "limited" | "not_enough_context" | "not_started";

const STATUS_META: Record<OutputStatus, { label: string; dotClass: string }> = {
  ready: { label: "Sẵn sàng", dotClass: "bg-emerald-500" },
  limited: { label: "Bản rút gọn", dotClass: "bg-amber-500" },
  not_enough_context: { label: "Chưa đủ dữ liệu", dotClass: "bg-muted-foreground/50" },
  not_started: { label: "Chưa tạo", dotClass: "bg-muted-foreground/30" },
};

interface StudyPackOutputCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  status: OutputStatus;
  reason?: string;
  actionLabel: string;
  onAction: () => void;
  busy?: boolean;
  secondaryLabel?: string;
  onSecondaryAction?: () => void;
}

export function StudyPackOutputCard({
  icon,
  title,
  description,
  status,
  reason,
  actionLabel,
  onAction,
  busy,
  secondaryLabel,
  onSecondaryAction,
}: StudyPackOutputCardProps) {
  const meta = STATUS_META[status];

  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary text-foreground/80">
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-foreground">{title}</h3>
            <span className="inline-flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground">
              <span className={cn("h-1.5 w-1.5 rounded-full", meta.dotClass)} />
              {meta.label}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
          {reason && status !== "ready" && (
            <p className="mt-1 text-xs text-muted-foreground/80">{reason}</p>
          )}
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" variant={status === "ready" ? "outline" : "default"} disabled={busy} onClick={onAction} className="h-8 flex-1 gap-1.5 text-xs">
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          {actionLabel}
        </Button>
        {secondaryLabel && onSecondaryAction && (
          <Button size="sm" variant="ghost" disabled={busy} onClick={onSecondaryAction} className="h-8 text-xs">
            {secondaryLabel}
          </Button>
        )}
      </div>
    </div>
  );
}

export default StudyPackOutputCard;
