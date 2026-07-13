"use client";

import { AlertCircle, Loader2, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ArtifactVersion } from "@/lib/types";

interface VersionSwitcherProps {
  versions: ArtifactVersion[];
  activeVersion: string | null;
  viewedVersion: string | null;
  onSwitch: (versionId: string) => void;
  onCreate?: () => void;
}

export function VersionSwitcher({ versions, activeVersion, viewedVersion, onSwitch, onCreate }: VersionSwitcherProps) {

  return (
    <div className="flex max-w-full items-center gap-1 border-b border-border/60" role="tablist" aria-label="Phiên bản học liệu">
      <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
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
              "flex shrink-0 items-center gap-1 border border-transparent px-3 py-2 text-xs font-semibold transition-colors",
              selected ? "-mb-px border-border/60 border-b-card bg-card text-foreground" : "text-muted-foreground hover:text-foreground"
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
      {onCreate && <button type="button" onClick={onCreate} className="grid h-8 w-8 shrink-0 place-items-center text-muted-foreground hover:text-foreground" title="Tạo phiên bản mới"><Plus className="h-4 w-4" /></button>}
    </div>
  );
}
