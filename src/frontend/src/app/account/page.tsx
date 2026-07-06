"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { User, Mail, Shield, LogOut, Loader2, GraduationCap, Sparkles, Check } from "lucide-react";
import {
  fetchCurrentUser,
  logout,
  updateLearningProfile,
  ROLE_MODES,
  ROLE_MODE_LABELS_VI,
  ROLE_MODE_DESCRIPTIONS_VI,
  UserPublic,
  type RoleMode,
} from "@/lib/auth";

export default function AccountPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingMode, setSavingMode] = useState<RoleMode | null>(null);
  const [modeError, setModeError] = useState<string | null>(null);

  useEffect(() => {
    async function loadUser() {
      const u = await fetchCurrentUser();
      if (!u) {
        router.push("/login");
      } else {
        setUser(u);
      }
      setLoading(false);
    }
    loadUser();
  }, [router]);

  const handleChangeMode = async (role: RoleMode) => {
    setSavingMode(role);
    setModeError(null);
    try {
      const updated = await updateLearningProfile({ role_mode: role });
      setUser(updated);
    } catch (err) {
      setModeError(err instanceof Error ? err.message : "Không thể đổi chế độ học tập.");
    } finally {
      setSavingMode(null);
    }
  };

  const handleLogout = async () => {
    await logout();
    router.push("/login");
    router.refresh();
  };

  if (loading) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-[calc(100vh-4rem)] py-12 px-4 sm:px-6 lg:px-8 max-w-3xl mx-auto">
      <div className="bg-card/80 backdrop-blur-md rounded-2xl border border-border/60 shadow-xl p-8 space-y-8">
        <div className="flex items-center gap-4 pb-6 border-b border-border/60">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-lg shadow-primary/20">
            <GraduationCap className="h-8 w-8" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">Hồ sơ cá nhân</h1>
            <p className="text-sm text-muted-foreground">Quản lý thông tin tài khoản AI Course Generator</p>
          </div>
        </div>

        <div className="space-y-6">
          <div className="flex items-center gap-3 p-4 rounded-xl bg-secondary/50 border border-border/40">
            <User className="h-5 w-5 text-primary" />
            <div>
              <p className="text-xs font-medium text-muted-foreground">Họ và tên</p>
              <p className="text-base font-semibold text-foreground">{user.full_name || "Chưa cập nhật"}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 p-4 rounded-xl bg-secondary/50 border border-border/40">
            <Mail className="h-5 w-5 text-primary" />
            <div>
              <p className="text-xs font-medium text-muted-foreground">Địa chỉ Email</p>
              <p className="text-base font-semibold text-foreground">{user.email}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 p-4 rounded-xl bg-secondary/50 border border-border/40">
            <Shield className="h-5 w-5 text-primary" />
            <div className="flex items-center gap-2">
              <div>
                <p className="text-xs font-medium text-muted-foreground">Vai trò hệ thống</p>
                <p className="text-base font-semibold text-foreground capitalize">{user.role}</p>
              </div>
              <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${user.role === "admin" ? "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300" : "bg-primary/10 text-primary"}`}>
                {user.role === "admin" ? "Admin" : "Thành viên"}
              </span>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <Shield className="h-5 w-5 text-emerald-600 dark:text-emerald-400 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-foreground">Quyền riêng tư & độ tin cậy</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Tài liệu được dùng để tạo học liệu, có thể xóa khỏi hệ thống và output có cảnh báo AI có thể sai.
              </p>
              <Link href="/privacy" className="mt-2 inline-flex text-xs font-semibold text-primary hover:underline">
                Xem chính sách quyền riêng tư
              </Link>
            </div>
          </div>
        </div>

        <div className="pt-8 border-t border-border/60 space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <div>
              <h2 className="text-lg font-bold text-foreground">Chế độ học tập</h2>
              <p className="text-xs text-muted-foreground">
                Quyết định cách hệ thống viết Sách, Slides, Mindmap, Quiz, Flashcards, Tóm tắt và Video từ
                tài liệu của bạn. Đổi chế độ không xóa học liệu đã tạo trước đó — hãy bấm &quot;Tạo lại&quot; ở
                trang tài liệu để áp dụng chế độ mới.
              </p>
            </div>
          </div>

          {modeError && <p className="text-sm text-destructive">{modeError}</p>}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {ROLE_MODES.map((role) => {
              const isCurrent = user.learning_profile?.role_mode === role;
              const isSaving = savingMode === role;
              return (
                <button
                  key={role}
                  type="button"
                  disabled={isSaving}
                  onClick={() => handleChangeMode(role)}
                  className={`flex items-start gap-3 rounded-xl border p-4 text-left transition-all disabled:opacity-60 ${
                    isCurrent
                      ? "border-primary bg-primary/10 ring-2 ring-primary"
                      : "border-border/70 bg-background hover:border-primary/50 hover:bg-muted/40"
                  }`}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                      isCurrent ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {isSaving ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : isCurrent ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <GraduationCap className="h-4 w-4" />
                    )}
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
        </div>

        <div className="pt-6 border-t border-border/60 flex justify-end">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 rounded-xl bg-destructive/10 text-destructive px-5 py-2.5 text-sm font-semibold hover:bg-destructive/20 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span>Đăng xuất</span>
          </button>
        </div>
      </div>
    </div>
  );
}
