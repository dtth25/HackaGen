"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldAlert } from "lucide-react";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { apiGetCurrentUser, apiDeleteAccount } from "@/lib/api";
import { removeToken } from "@/lib/auth";
import type { User } from "@/lib/types";
import { CONTAINER_NARROW } from "@/lib/layout";
import { cn } from "@/lib/utils";

export default function AccountPage() {
  return (
    <AuthGuard>
      <AccountContent />
    </AuthGuard>
  );
}

function AccountContent() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiGetCurrentUser()
      .then((u) => active && setUser(u))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const handleDeleteAccount = async () => {
    if (!password) {
      setError("Vui lòng nhập mật khẩu để xác nhận.");
      return;
    }
    setDeleting(true);
    setError("");
    try {
      await apiDeleteAccount(password);
      removeToken();
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xóa tài khoản thất bại.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className={cn(CONTAINER_NARROW, "py-10 space-y-6")}>
      <div>
        <h1 className="text-2xl font-bold text-foreground">Tài khoản</h1>
        <p className="mt-1 text-muted-foreground">Quản lý thông tin tài khoản của bạn.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Thông tin</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between border-b pb-2">
            <span className="text-muted-foreground">Email</span>
            <span className="font-medium">{user?.email ?? "..."}</span>
          </div>
          {user?.full_name && (
            <div className="flex justify-between border-b pb-2">
              <span className="text-muted-foreground">Họ tên</span>
              <span className="font-medium">{user.full_name}</span>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base text-destructive">
            <ShieldAlert className="h-4 w-4" />
            Vùng nguy hiểm
          </CardTitle>
          <CardDescription>
            Xóa tài khoản sẽ xóa vĩnh viễn toàn bộ khóa học, tài liệu và học liệu đã tạo. Hành
            động này không thể hoàn tác.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Dialog
            open={dialogOpen}
            onOpenChange={(open) => {
              setDialogOpen(open);
              if (!open) {
                setPassword("");
                setError("");
              }
            }}
          >
            <DialogTrigger render={<Button variant="destructive" />}>
              Xóa tài khoản
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Xóa tài khoản vĩnh viễn?</DialogTitle>
                <DialogDescription>
                  Nhập lại mật khẩu để xác nhận. Toàn bộ dữ liệu của bạn sẽ bị xóa và không thể
                  khôi phục.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-2">
                <Label htmlFor="confirm-password">Mật khẩu</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoFocus
                />
                {error && <p className="text-sm text-destructive">{error}</p>}
              </div>
              <DialogFooter>
                <Button variant="ghost" onClick={() => setDialogOpen(false)}>
                  Hủy
                </Button>
                <Button variant="destructive" onClick={handleDeleteAccount} disabled={deleting}>
                  {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Xóa vĩnh viễn
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>
    </div>
  );
}
