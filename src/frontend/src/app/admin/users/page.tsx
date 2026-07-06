"use client";

import React, { useEffect, useState, useMemo } from "react";
import {
  Users,
  Shield,
  UserCheck,
  Search,
  Edit,
  Key,
  Trash2,
  Lock,
  Unlock,
  Loader2,
  Check,
  X,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import {
  fetchUsers,
  updateUser,
  disableUser,
  enableUser,
  makeAdmin,
  makeUser,
  deleteUser,
  resetUserPassword,
} from "@/lib/admin-api";
import { UserPublic, fetchCurrentUser } from "@/lib/auth";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentAdminId, setCurrentAdminId] = useState<string | null>(null);

  // Modals state
  const [editingUser, setEditingUser] = useState<UserPublic | null>(null);
  const [editFullName, setEditFullName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editRole, setEditRole] = useState<"user" | "admin">("user");
  const [editActive, setEditActive] = useState(true);
  const [editLoading, setEditLoading] = useState(false);

  const [resettingUser, setResettingUser] = useState<UserPublic | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetLoading, setResetLoading] = useState(false);

  const [deletingUser, setDeletingUser] = useState<UserPublic | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [uList, me] = await Promise.all([fetchUsers(), fetchCurrentUser()]);
      setUsers(uList);
      if (me) setCurrentAdminId(me.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lỗi tải danh sách người dùng.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void Promise.resolve().then(loadData);
  }, []);

  const stats = useMemo(() => {
    const total = users.length;
    const active = users.filter((u) => u.is_active).length;
    const admins = users.filter((u) => u.role === "admin" && u.is_active).length;
    return { total, active, admins };
  }, [users]);

  const filteredUsers = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        u.email.toLowerCase().includes(q) ||
        (u.full_name && u.full_name.toLowerCase().includes(q)) ||
        u.role.toLowerCase().includes(q)
    );
  }, [users, searchQuery]);

  // Handle quick role toggle
  const handleToggleRole = async (user: UserPublic) => {
    setActionLoadingId(user.id);
    setError(null);
    try {
      const updated = user.role === "admin" ? await makeUser(user.id) : await makeAdmin(user.id);
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Thao tác đổi quyền thất bại.");
    } finally {
      setActionLoadingId(null);
    }
  };

  // Handle quick status toggle
  const handleToggleStatus = async (user: UserPublic) => {
    setActionLoadingId(user.id);
    setError(null);
    try {
      const updated = user.is_active ? await disableUser(user.id) : await enableUser(user.id);
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Thao tác thay đổi trạng thái thất bại.");
    } finally {
      setActionLoadingId(null);
    }
  };

  // Handle Edit Submit
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setEditLoading(true);
    setError(null);
    try {
      const updated = await updateUser(editingUser.id, {
        full_name: editFullName.trim() || undefined,
        email: editEmail.trim(),
        role: editRole,
        is_active: editActive,
      });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      setEditingUser(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cập nhật thông tin thất bại.");
    } finally {
      setEditLoading(false);
    }
  };

  // Handle Reset Password Submit
  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resettingUser) return;
    if (newPassword.length < 8) {
      setError("Mật khẩu mới phải có ít nhất 8 ký tự.");
      return;
    }
    setResetLoading(true);
    setError(null);
    try {
      await resetUserPassword(resettingUser.id, newPassword);
      setResettingUser(null);
      setNewPassword("");
      alert("Đã đặt lại mật khẩu thành công.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đặt lại mật khẩu thất bại.");
    } finally {
      setResetLoading(false);
    }
  };

  // Handle Delete Submit
  const handleDeleteSubmit = async () => {
    if (!deletingUser) return;
    setDeleteLoading(true);
    setError(null);
    try {
      await deleteUser(deletingUser.id);
      setUsers((prev) => prev.filter((u) => u.id !== deletingUser.id));
      setDeletingUser(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xóa tài khoản thất bại.");
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2.5">
            <Shield className="h-7 w-7 text-purple-600 dark:text-purple-400" />
            Quản trị viên & Quản lý người dùng
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Kiểm soát quyền truy cập, vai trò và trạng thái tài khoản trên toàn hệ thống
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-xl bg-secondary px-4 py-2 text-sm font-semibold text-foreground hover:bg-secondary/80 transition-colors disabled:opacity-50 self-start sm:self-auto"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          <span>Làm mới</span>
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div className="rounded-xl bg-destructive/10 border border-destructive/20 p-4 text-sm text-destructive flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-border/60 bg-card/80 p-5 shadow-sm backdrop-blur-sm flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
            <Users className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Tổng tài khoản</p>
            <p className="text-2xl font-bold text-foreground">{stats.total}</p>
          </div>
        </div>

        <div className="rounded-2xl border border-border/60 bg-card/80 p-5 shadow-sm backdrop-blur-sm flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <UserCheck className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Đang hoạt động</p>
            <p className="text-2xl font-bold text-foreground">{stats.active}</p>
          </div>
        </div>

        <div className="rounded-2xl border border-border/60 bg-card/80 p-5 shadow-sm backdrop-blur-sm flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400">
            <Shield className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Quản trị viên (Admins)</p>
            <p className="text-2xl font-bold text-foreground">{stats.admins}</p>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
          <Search className="h-4 w-4 text-muted-foreground" />
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Tìm kiếm theo tên, email hoặc vai trò..."
          className="w-full rounded-xl border border-border bg-card/80 py-2.5 pl-10 pr-4 text-sm text-foreground placeholder-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      {/* Users Table */}
      <div className="rounded-2xl border border-border/60 bg-card/80 shadow-sm backdrop-blur-sm overflow-hidden">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Đang tải danh sách tài khoản...</p>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="py-16 text-center text-sm text-muted-foreground">
            Không tìm thấy người dùng nào phù hợp.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-secondary/60 text-xs uppercase text-muted-foreground border-b border-border/60">
                <tr>
                  <th className="py-3.5 px-6 font-semibold">Thành viên</th>
                  <th className="py-3.5 px-6 font-semibold">Vai trò</th>
                  <th className="py-3.5 px-6 font-semibold">Trạng thái</th>
                  <th className="py-3.5 px-6 font-semibold text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {filteredUsers.map((u) => {
                  const isMe = u.id === currentAdminId;
                  const isBusy = actionLoadingId === u.id;
                  return (
                    <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-4 px-6">
                        <div className="font-semibold text-foreground flex items-center gap-2">
                          {u.full_name || "Chưa đặt tên"}
                          {isMe && (
                            <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-bold text-primary uppercase">
                              Bạn
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground mt-0.5">{u.email}</div>
                      </td>
                      <td className="py-4 px-6">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            u.role === "admin"
                              ? "bg-purple-500/15 text-purple-600 dark:text-purple-300 border border-purple-500/20"
                              : "bg-secondary text-muted-foreground border border-border/60"
                          }`}
                        >
                          {u.role === "admin" ? <Shield className="h-3 w-3" /> : <Users className="h-3 w-3" />}
                          <span className="capitalize">{u.role === "admin" ? "Admin" : "Thành viên"}</span>
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            u.is_active
                              ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                              : "bg-destructive/15 text-destructive border border-destructive/20"
                          }`}
                        >
                          {u.is_active ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
                          <span>{u.is_active ? "Hoạt động" : "Vô hiệu hóa"}</span>
                        </span>
                      </td>
                      <td className="py-4 px-6 text-right space-x-1.5">
                        {isBusy ? (
                          <Loader2 className="h-4 w-4 animate-spin text-primary inline-block" />
                        ) : (
                          <>
                            <button
                              onClick={() => {
                                setEditingUser(u);
                                setEditFullName(u.full_name || "");
                                setEditEmail(u.email);
                                setEditRole(u.role);
                                setEditActive(u.is_active);
                              }}
                              title="Chỉnh sửa thông tin"
                              className="inline-flex items-center justify-center rounded-lg p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                            >
                              <Edit className="h-4 w-4" />
                            </button>

                            <button
                              onClick={() => handleToggleRole(u)}
                              disabled={isMe}
                              title={u.role === "admin" ? "Giáng chức thành viên" : "Thăng cấp Admin"}
                              className="inline-flex items-center justify-center rounded-lg p-1.5 text-muted-foreground hover:bg-purple-500/10 hover:text-purple-600 dark:hover:text-purple-300 disabled:opacity-30 transition-colors"
                            >
                              <Shield className="h-4 w-4" />
                            </button>

                            <button
                              onClick={() => handleToggleStatus(u)}
                              disabled={isMe}
                              title={u.is_active ? "Vô hiệu hóa tài khoản" : "Kích hoạt tài khoản"}
                              className="inline-flex items-center justify-center rounded-lg p-1.5 text-muted-foreground hover:bg-amber-500/10 hover:text-amber-600 dark:hover:text-amber-400 disabled:opacity-30 transition-colors"
                            >
                              {u.is_active ? <Lock className="h-4 w-4" /> : <Unlock className="h-4 w-4" />}
                            </button>

                            <button
                              onClick={() => {
                                setResettingUser(u);
                                setNewPassword("");
                              }}
                              title="Đặt lại mật khẩu"
                              className="inline-flex items-center justify-center rounded-lg p-1.5 text-muted-foreground hover:bg-blue-500/10 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                            >
                              <Key className="h-4 w-4" />
                            </button>

                            <button
                              onClick={() => setDeletingUser(u)}
                              disabled={isMe}
                              title="Xóa tài khoản"
                              className="inline-flex items-center justify-center rounded-lg p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-30 transition-colors"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Edit User Modal */}
      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-card p-6 border border-border shadow-2xl space-y-5">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Edit className="h-5 w-5 text-primary" />
              Chỉnh sửa thông tin tài khoản
            </h3>

            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Họ và tên</label>
                <input
                  type="text"
                  value={editFullName}
                  onChange={(e) => setEditFullName(e.target.value)}
                  placeholder="Nguyễn Văn A"
                  className="w-full rounded-xl border border-border bg-background py-2 px-3 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Email *</label>
                <input
                  type="email"
                  required
                  value={editEmail}
                  onChange={(e) => setEditEmail(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background py-2 px-3 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Vai trò</label>
                  <select
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value as "user" | "admin")}
                    disabled={editingUser.id === currentAdminId}
                    className="w-full rounded-xl border border-border bg-background py-2 px-3 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
                  >
                    <option value="user">Thành viên</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Trạng thái</label>
                  <select
                    value={editActive ? "true" : "false"}
                    onChange={(e) => setEditActive(e.target.value === "true")}
                    disabled={editingUser.id === currentAdminId}
                    className="w-full rounded-xl border border-border bg-background py-2 px-3 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
                  >
                    <option value="true">Hoạt động</option>
                    <option value="false">Vô hiệu hóa</option>
                  </select>
                </div>
              </div>

              <div className="pt-4 flex justify-end gap-2 border-t border-border/60">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="rounded-xl bg-secondary px-4 py-2 text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={editLoading}
                  className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {editLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                  <span>Lưu thay đổi</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {resettingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-card p-6 border border-border shadow-2xl space-y-5">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Key className="h-5 w-5 text-blue-500" />
              Đặt lại mật khẩu cho {resettingUser.email}
            </h3>

            <form onSubmit={handleResetPasswordSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Mật khẩu mới (tối thiểu 8 ký tự) *
                </label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-xl border border-border bg-background py-2 px-3 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="pt-4 flex justify-end gap-2 border-t border-border/60">
                <button
                  type="button"
                  onClick={() => setResettingUser(null)}
                  className="rounded-xl bg-secondary px-4 py-2 text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={resetLoading}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {resetLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                  <span>Cập nhật mật khẩu</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-card p-6 border border-destructive/40 shadow-2xl space-y-5">
            <div className="flex items-center gap-3 text-destructive">
              <AlertTriangle className="h-6 w-6 shrink-0" />
              <h3 className="text-lg font-bold">Xác nhận xóa tài khoản</h3>
            </div>

            <p className="text-sm text-muted-foreground leading-relaxed">
              Bạn có chắc chắn muốn xóa vĩnh viễn tài khoản <strong className="text-foreground">{deletingUser.email}</strong> không? Hành động này không thể khôi phục.
            </p>

            <div className="pt-4 flex justify-end gap-2 border-t border-border/60">
              <button
                type="button"
                onClick={() => setDeletingUser(null)}
                className="rounded-xl bg-secondary px-4 py-2 text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={handleDeleteSubmit}
                disabled={deleteLoading}
                className="inline-flex items-center gap-2 rounded-xl bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50 transition-colors"
              >
                {deleteLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>Xóa vĩnh viễn</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
