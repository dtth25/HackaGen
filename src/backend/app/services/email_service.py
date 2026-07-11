"""Transactional email sending (verification codes, password reset) via Resend.

Sends are synchronous and raise on failure — a user waiting on a code needs to
know immediately if delivery failed, not get a fake "email sent" response
(same "no silent fallback" stance already applied to LLM generation).
"""

import resend

from app.core.config import logger, settings

_BRAND = "HackaGen"
_ACCENT = "#2454c4"


class EmailNotConfiguredError(Exception):
    """RESEND_API_KEY / EMAIL_FROM_ADDRESS missing — operator setup incomplete."""


class EmailSendError(Exception):
    """Resend API call failed."""


def _require_configured() -> None:
    if not settings.RESEND_API_KEY or not settings.EMAIL_FROM_ADDRESS:
        raise EmailNotConfiguredError(
            "RESEND_API_KEY/EMAIL_FROM_ADDRESS chưa được cấu hình trên server."
        )


def _dev_fallback(to_email: str, code: str, reason: str) -> None:
    logger.warning(
        "[EMAIL_DEV_FALLBACK] %s — mã cho %s: %s "
        "(chỉ in ra log, KHÔNG gửi email thật — không được bật cờ này ở production)",
        reason,
        to_email,
        code,
    )


def _code_email_html(heading: str, body: str, code: str) -> str:
    return f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;">
      <p style="font-size:14px;color:#666;letter-spacing:0.02em;text-transform:uppercase;margin:0 0 16px;">{_BRAND}</p>
      <h1 style="font-size:20px;margin:0 0 12px;color:#111;">{heading}</h1>
      <p style="font-size:14px;color:#444;line-height:1.6;margin:0 0 24px;">{body}</p>
      <div style="font-size:32px;font-weight:700;letter-spacing:0.15em;color:{_ACCENT};background:#f3f5fa;border-radius:8px;padding:16px 24px;text-align:center;margin:0 0 24px;">{code}</div>
      <p style="font-size:13px;color:#888;line-height:1.5;margin:0;">Mã có hiệu lực trong {settings.EMAIL_OTP_EXPIRE_MINUTES} phút. Nếu bạn không yêu cầu email này, có thể bỏ qua.</p>
    </div>
    """.strip()


def _send(to_email: str, subject: str, heading: str, body: str, code: str) -> None:
    if not settings.RESEND_API_KEY or not settings.EMAIL_FROM_ADDRESS:
        if settings.EMAIL_DEV_FALLBACK:
            _dev_fallback(to_email, code, "RESEND_API_KEY/EMAIL_FROM_ADDRESS chưa cấu hình")
            return
        _require_configured()

    resend.api_key = settings.RESEND_API_KEY
    html = _code_email_html(heading, body, code)
    text = f"{heading}\n\n{body}\n\nMã: {code}\n\nMã có hiệu lực trong {settings.EMAIL_OTP_EXPIRE_MINUTES} phút."
    try:
        resend.Emails.send(
            {
                "from": settings.EMAIL_FROM_ADDRESS,
                "to": [to_email],
                "subject": subject,
                "html": html,
                "text": text,
            }
        )
    except Exception as e:
        if settings.EMAIL_DEV_FALLBACK:
            # Real send attempted and failed (e.g. Resend sending domain not verified
            # yet) — degrade to console instead of blocking local testing on it.
            _dev_fallback(to_email, code, f"Gửi email thật thất bại ({e})")
            return
        logger.error("Resend email send failed for %s: %s", to_email, e, exc_info=True)
        raise EmailSendError(f"Không gửi được email: {e}") from e


def send_verification_code(to_email: str, code: str) -> None:
    _send(
        to_email,
        subject=f"Mã xác thực {_BRAND} của bạn",
        heading="Xác thực địa chỉ email",
        body="Nhập mã bên dưới để hoàn tất đăng ký tài khoản.",
        code=code,
    )


def send_password_reset_code(to_email: str, code: str) -> None:
    _send(
        to_email,
        subject=f"Mã đặt lại mật khẩu {_BRAND}",
        heading="Đặt lại mật khẩu",
        body="Nhập mã bên dưới để đặt lại mật khẩu tài khoản của bạn.",
        code=code,
    )
