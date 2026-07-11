"""Models package."""
from app.models.user import User
from app.models.course import Course
from app.models.email_otp import EmailOtpCode

__all__ = ["User", "Course", "EmailOtpCode"]
