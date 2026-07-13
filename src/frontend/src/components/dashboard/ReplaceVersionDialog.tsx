"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { ArtifactVersion } from "@/lib/types";

interface ReplaceVersionDialogProps {
  open: boolean;
  versions: ArtifactVersion[];
  onOpenChange: (open: boolean) => void;
  onConfirm: (versionId: string) => void;
}

export function ReplaceVersionDialog({ open, versions, onOpenChange, onConfirm }: ReplaceVersionDialogProps) {
  const [selected, setSelected] = useState<string>(versions[0]?.version_id ?? "");
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Chọn bản để thay thế</DialogTitle>
          <DialogDescription>Đã đạt giới hạn phiên bản. Bản được chọn sẽ bị xóa sau khi bản mới tạo xong.</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          {versions.map((version) => (
            <label key={version.version_id} className="flex cursor-pointer items-center gap-3 rounded-lg border border-border/60 px-3 py-2 text-sm hover:bg-muted/50">
              <input type="radio" name="replace-version" checked={selected === version.version_id} onChange={() => setSelected(version.version_id)} />
              <span className="font-medium">{version.label}</span>
            </label>
          ))}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Hủy</Button>
          <Button disabled={!selected} onClick={() => onConfirm(selected)}>Tạo bản mới</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
