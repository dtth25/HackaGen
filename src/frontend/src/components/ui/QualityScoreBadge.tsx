import React from "react";
import { AlertTriangle, XCircle, Award } from "lucide-react";
import { cn } from "@/lib/utils";

interface QualityScoreBadgeProps {
  score?: number;
  isUniversityReady?: boolean;
  className?: string;
}

export function QualityScoreBadge({
  score = 85,
  isUniversityReady = true,
  className,
}: QualityScoreBadgeProps) {
  const ready = isUniversityReady ?? score >= 80;

  if (ready && score >= 80) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border border-success/20 bg-success/10 px-3 py-1 text-xs font-semibold text-success shadow-[var(--shadow-xs)]",
          className
        )}
      >
        <Award className="h-3.5 w-3.5" />
        <span>Chất lượng cao • {score}/100</span>
      </span>
    );
  }

  if (score >= 60) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border border-warning/20 bg-warning/10 px-3 py-1 text-xs font-semibold text-warning shadow-[var(--shadow-xs)]",
          className
        )}
      >
        <AlertTriangle className="h-3.5 w-3.5" />
        <span>Cần rà soát • {score}/100</span>
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-error/20 bg-error/10 px-3 py-1 text-xs font-semibold text-error shadow-[var(--shadow-xs)]",
        className
      )}
    >
      <XCircle className="h-3.5 w-3.5" />
      <span>Bản nháp • {score}/100</span>
    </span>
  );
}
