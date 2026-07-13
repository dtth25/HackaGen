"use client";

import { AlertCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ArtifactVersion } from "@/lib/types";

interface VersionSwitcherProps {
  versions: ArtifactVersion[];
  activeVersion: string | null;
  viewedVersion: string | null;
  onSwitch: (versionId: string) => void;
}

export function VersionSwitcher({ versions, activeVersion, viewedVersion, onSwitch }: VersionSwitcherProps) {
  if (versions.length < 2) return null;

  return (
    <div className="flex max-w-full items-center gap-1 overflow-x-auto rounded-lg border border-border/60 bg-muted/40 p-1" role="tablist" aria-label="Phiên bản học liệu">
      {versions.map((version) => {
        const selected = version.version_id === viewedVersion;
        return (
          <button
            key={version.version_id}
            type="button"
            role="tab"
            aria-selected={selected}
            title={version.created_at ? `Tạo lúc ${new Date(version.created_at).toLocaleString("vi-VN")}` : version.label}
            onClick={() => onSwitch(version.version_id)}
            className={cn(
              "flex shrink-0 items-center gap-1 rounded-md px-2 py-1.5 text-xs font-semibold transition-colors",
              selected ? "bg-card text-foreground shadow-[var(--shadow-xs)]" : "text-muted-foreground hover:text-foreground"
            )}
          >
            <span>{version.label}</span>
            {version.version_id === activeVersion && <span className="h-1.5 w-1.5 rounded-full bg-primary" aria-label="Đang dùng" />}
            {version.status === "processing" && <Loader2 className="h-3 w-3 animate-spin" aria-label="Đang tạo" />}
            {version.status === "error" && <AlertCircle className="h-3 w-3 text-error" aria-label="Lỗi" />}
          </button>
        );
      })}
    </div>
  );
}
