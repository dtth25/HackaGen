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
          "inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 shadow-sm",
          className
        )}
      >
        <Award className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
        <span>Chuẩn đại học • {score}/100</span>
      </span>
    );
  }

  if (score >= 60) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-700 dark:text-amber-400 border border-amber-500/20 shadow-sm",
          className
        )}
      >
        <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
        <span>Cần rà soát • {score}/100</span>
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-700 dark:text-rose-400 border border-rose-500/20 shadow-sm",
        className
      )}
    >
      <XCircle className="h-3.5 w-3.5 text-rose-600 dark:text-rose-400" />
      <span>Bản nháp • {score}/100</span>
    </span>
  );
}
