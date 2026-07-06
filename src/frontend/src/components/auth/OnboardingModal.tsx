"use client";

import React, { useState } from "react";
import {
  GraduationCap,
  Clock,
  Presentation,
  Lightbulb,
  Code2,
  Building2,
  Microscope,
  Loader2,
  Check,
} from "lucide-react";
import {
  ROLE_MODES,
  ROLE_MODE_LABELS_VI,
  ROLE_MODE_DESCRIPTIONS_VI,
  updateLearningProfile,
  type RoleMode,
  type UserPublic,
} from "@/lib/auth";

const ROLE_MODE_ICONS: Record<RoleMode, React.ComponentType<{ className?: string }>> = {
  student: GraduationCap,
  exam_prep: Clock,
  teacher: Presentation,
  self_learner: Lightbulb,
  developer: Code2,
  enterprise_trainer: Building2,
  researcher: Microscope,
};

export function OnboardingModal({
  onComplete,
}: {
  onComplete: (user: UserPublic) => void;
}) {
  const [selected, setSelected] = useState<RoleMode | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      const user = await updateLearningProfile({ role_mode: selected });
      onComplete(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể lưu chế độ học tập.");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/95 backdrop-blur-sm p-4">
      <div className="w-full max-w-3xl rounded-2xl border border-border/60 bg-card p-6 sm:p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-foreground">Chào mừng bạn đến với Study Pack AI</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Chọn vai trò phù hợp để hệ thống tạo học liệu (Sách, Mindmap, Quiz, Flashcards, Video...)
            theo đúng nhu cầu của bạn. Bạn có thể đổi lại bất cứ lúc nào trong phần Cài đặt.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {ROLE_MODES.map((role) => {
            const Icon = ROLE_MODE_ICONS[role];
            const isSelected = selected === role;
            return (
              <button
                key={role}
                type="button"
                onClick={() => setSelected(role)}
                className={`flex items-start gap-3 rounded-xl border p-4 text-left transition-all ${
                  isSelected
                    ? "border-primary bg-primary/10 ring-2 ring-primary"
                    : "border-border/70 bg-background hover:border-primary/50 hover:bg-muted/40"
                }`}
              >
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                    isSelected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  {isSelected ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">{ROLE_MODE_LABELS_VI[role]}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                    {ROLE_MODE_DESCRIPTIONS_VI[role]}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        {error && <p className="mt-4 text-sm text-destructive">{error}</p>}

        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            type="button"
            disabled={!selected || saving}
            onClick={handleConfirm}
            className="flex items-center gap-2 rounded-xl bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50 transition-all"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Bắt đầu
          </button>
        </div>
      </div>
    </div>
  );
}
