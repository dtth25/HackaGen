"""Idempotent default-admin bootstrap, run once at app startup when enabled."""

from app.core.config import logger, settings
from app.core.security import get_password_hash
from app.models.user import User


def seed_default_admin() -> None:
    if not settings.CREATE_DEFAULT_ADMIN:
        return

    # Imported here (not at module scope) so tests that swap in an in-memory test
    # database after this module is first imported still get the patched engine.
    from app.services.database import SessionLocal

    db = SessionLocal()
    try:
        email = settings.ADMIN_EMAIL.strip().lower()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            logger.info("Default admin bootstrap: '%s' already exists, skipping.", email)
            return

        admin = User(
            email=email,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            full_name="Administrator",
            role="admin",
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        db.commit()
        logger.info("Default admin bootstrap: created admin account '%s'.", email)
    finally:
        db.close()
