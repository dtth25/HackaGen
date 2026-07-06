import { apiFetch } from "@/lib/api";
import { UserPublic } from "@/lib/auth";

const ADMIN_API_BASE = "/api/backend/admin";

export async function fetchUsers(): Promise<UserPublic[]> {
  const res = await apiFetch(`${ADMIN_API_BASE}/users`);
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: "Lỗi tải danh sách người dùng." }));
    throw new Error(data.detail || "Lỗi tải danh sách người dùng.");
  }
  return res.json();
}

export async function fetchUser(userId: string): Promise<UserPublic> {
  const res = await apiFetch(`${ADMIN_API_BASE}/users/${userId}`);
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: "Lỗi tải thông tin người dùng." }));
    throw new Error(data.detail || "Lỗi tải thông tin người dùng.");
  }
  return res.json();
}

export async function updateUser(
  userId: string,
  data: { email?: string; full_name?: string; role?: string; is_active?: boolean }
): Promise<UserPublic> {
  const res = await apiFetch(`${ADMIN_API_BASE}/users/${userId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: "Cập nhật thất bại." }));
    throw new Error(errData.detail || "Cập nhật thất bại.");
  }
  return res.json();
}

export async function disableUser(userId: string): Promise<UserPublic> {
  const res = await apiFetch(`${ADMIN_API_BASE}/users/${userId}/disable`, { method: "POST" });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: "Vô hiệu hóa thất bại." }));
    throw new Error(errData.detail || "Vô hiệu hóa thất bại.");
  }
  return res.json();
}

export async function enableUser(userId: string): Promise<UserPublic> {
  const res = await apiFetch(`${ADMIN_API_BASE}/users/${userId}/enable`, { method: "POST" });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: "Kích hoạt thất bại." }));
    throw new Error(errData.detail || "Kích hoạt thất bại.");
  }
  return res.json();
}

export async function makeAdmin(userId: string): Promise<UserPublic> {
  const res = await apiFetch(`${ADMIN_API_BASE}/users/${userId}/make-admin`, { method: "POST" });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: "Thăng cấp thất bại." }));
    throw new Error(errData.detail || "Thăng cấp thất bại.");
  }
  return res.json();
}

export async function makeUser(userId: string): Promise<UserPublic> {
  const res = await apiFetch(`${ADMIN_API_BASE}/users/${userId}/make-user`, { method: "POST" });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: "Giáng chức thất bại." }));
    throw new Error(errData.detail || "Giáng chức thất bại.");
  }
  return res.json();
}

export async function deleteUser(userId: string): Promise<{ detail: string }> {
  const res = await apiFetch(`${ADMIN_API_BASE}/users/${userId}`, { method: "DELETE" });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: "Xóa tài khoản thất bại." }));
    throw new Error(errData.detail || "Xóa tài khoản thất bại.");
  }
  return res.json();
}

export async function resetUserPassword(userId: string, newPassword: string): Promise<UserPublic> {
  const res = await apiFetch(`${ADMIN_API_BASE}/users/${userId}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_password: newPassword }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: "Đặt lại mật khẩu thất bại." }));
    throw new Error(errData.detail || "Đặt lại mật khẩu thất bại.");
  }
  return res.json();
}
