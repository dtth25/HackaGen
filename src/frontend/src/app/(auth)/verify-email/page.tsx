"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiVerifyEmail, apiResendVerification, ApiRequestError } from "@/lib/api";
import { setToken, setStoredUser } from "@/lib/auth";

const RESEND_COOLDOWN_SECONDS = 60;

function VerifyEmailForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const emailFromQuery = searchParams.get("email") || "";

  const [email, setEmail] = useState(emailFromQuery);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => setCooldown((c) => Math.max(0, c - 1)), 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setInfo("");
    if (!email.trim() || code.trim().length !== 6) {
      setError("Vui lòng nhập email và mã xác thực gồm 6 số.");
      return;
    }
    setLoading(true);
    try {
      const res = await apiVerifyEmail({ email: email.trim(), code: code.trim() });
      setToken(res.access_token);
      setStoredUser(res.user);
      router.push("/courses");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xác thực thất bại. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (!email.trim() || cooldown > 0) return;
    setError("");
    setInfo("");
    setResending(true);
    try {
      const res = await apiResendVerification(email.trim());
      setInfo(res.message);
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      setError(
        err instanceof ApiRequestError ? err.message : "Không gửi lại được mã. Vui lòng thử lại."
      );
    } finally {
      setResending(false);
    }
  };

  return (
    <>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground">Xác thực email</h1>
        <p className="mt-2 text-muted-foreground">
          Nhập mã 6 số vừa được gửi tới email của bạn để hoàn tất đăng ký.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}
        {info && (
          <div className="rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-primary">
            {info}
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="email@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="code">Mã xác thực</Label>
          <Input
            id="code"
            type="text"
            inputMode="numeric"
            maxLength={6}
            placeholder="000000"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            autoFocus
            className="tracking-[0.3em] text-center text-lg"
          />
        </div>

        <Button type="submit" className="w-full" size="lg" disabled={loading}>
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Xác thực
        </Button>
      </form>

      <div className="mt-6 text-center text-sm text-muted-foreground">
        Không nhận được mã?{" "}
        <button
          type="button"
          onClick={handleResend}
          disabled={resending || cooldown > 0}
          className="font-medium text-primary hover:underline disabled:cursor-not-allowed disabled:opacity-50 disabled:no-underline"
        >
          {cooldown > 0 ? `Gửi lại sau ${cooldown}s` : "Gửi lại mã"}
        </button>
      </div>

      <p className="mt-2 text-center text-sm text-muted-foreground">
        <Link href="/login" className="font-medium text-primary hover:underline">
          Quay lại đăng nhập
        </Link>
      </p>
    </>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailForm />
    </Suspense>
  );
}
