import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AccountPage from "./page";
import { apiGetCurrentUser, apiDeleteAccount } from "@/lib/api";
import { isAuthenticated, removeToken } from "@/lib/auth";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

vi.mock("@/lib/auth", () => ({
  isAuthenticated: vi.fn(() => true),
  removeToken: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  apiGetCurrentUser: vi.fn(),
  apiDeleteAccount: vi.fn(),
}));

const user = { id: "u1", email: "test@example.com", full_name: "Người Test", role: "user" };

describe("Account deletion — irreversible, password-confirmed", () => {
  beforeEach(() => {
    vi.mocked(isAuthenticated).mockReturnValue(true);
    vi.mocked(apiGetCurrentUser).mockResolvedValue(user as never);
    vi.mocked(apiDeleteAccount).mockReset();
    vi.mocked(removeToken).mockReset();
    push.mockReset();
  });

  it("blocks deletion with no API call when the password field is empty", async () => {
    const u = userEvent.setup({ pointerEventsCheck: 0 });
    render(<AccountPage />);

    await u.click(await screen.findByRole("button", { name: "Xóa tài khoản" }));
    await u.click(await screen.findByRole("button", { name: "Xóa vĩnh viễn" }));

    expect(await screen.findByText("Vui lòng nhập mật khẩu để xác nhận.")).toBeInTheDocument();
    expect(apiDeleteAccount).not.toHaveBeenCalled();
  });

  it("deletes the account, clears the token, and redirects home on success", async () => {
    vi.mocked(apiDeleteAccount).mockResolvedValueOnce({ message: "Tài khoản đã được xóa vĩnh viễn." });
    const u = userEvent.setup({ pointerEventsCheck: 0 });
    render(<AccountPage />);

    await u.click(await screen.findByRole("button", { name: "Xóa tài khoản" }));
    await u.type(screen.getByLabelText("Mật khẩu"), "password123");
    await u.click(screen.getByRole("button", { name: "Xóa vĩnh viễn" }));

    await waitFor(() => expect(apiDeleteAccount).toHaveBeenCalledWith("password123"));
    await waitFor(() => expect(removeToken).toHaveBeenCalled());
    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
  });

  it("shows the real backend error (e.g. wrong password) and does NOT clear the session", async () => {
    vi.mocked(apiDeleteAccount).mockRejectedValueOnce(new Error("Mật khẩu không chính xác."));
    const u = userEvent.setup({ pointerEventsCheck: 0 });
    render(<AccountPage />);

    await u.click(await screen.findByRole("button", { name: "Xóa tài khoản" }));
    await u.type(screen.getByLabelText("Mật khẩu"), "wrong-password");
    await u.click(screen.getByRole("button", { name: "Xóa vĩnh viễn" }));

    expect(await screen.findByText("Mật khẩu không chính xác.")).toBeInTheDocument();
    expect(removeToken).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });
});
