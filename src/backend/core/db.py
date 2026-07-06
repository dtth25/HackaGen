"""Database access layer for users using lightweight local SQLite."""

import json
import sqlite3
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from backend.core.config import DATABASE_URL, DATA_DIR, logger
from backend.models.user import UserInDB


def _sqlite_path_from_database_url(database_url: str) -> str:
    """Resolve supported local SQLite DATABASE_URL values to a filesystem path."""
    if database_url.startswith("sqlite:///"):
        return database_url.removeprefix("sqlite:///")
    if database_url.startswith("sqlite://"):
        return database_url.removeprefix("sqlite://")
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        raise RuntimeError(
            "Postgres DATABASE_URL is planned for production but not implemented yet. "
            "Use sqlite:///./data/app.db for local/dev mode."
        )
    return database_url or os.path.join(DATA_DIR, "users.db")


DB_PATH = _sqlite_path_from_database_url(DATABASE_URL)


def get_db_connection() -> sqlite3.Connection:
    """Return a connection to the local SQLite database with row factory enabled."""
    os.makedirs(os.path.dirname(DB_PATH) or DATA_DIR, exist_ok=True)
    conn = sqlite3.Connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize SQLite database schema and optionally bootstrap default admin."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'user' NOT NULL,
            is_active INTEGER DEFAULT 1 NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login_at TEXT,
            learning_profile TEXT
        )
        """
    )
    conn.commit()

    # Migration for pre-existing `users.db` files created before the learning_profile
    # column existed — sqlite has no "ADD COLUMN IF NOT EXISTS", so probe-and-catch.
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN learning_profile TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists.

    # Check for default admin bootstrap placeholder (PART K)
    create_admin = os.getenv("CREATE_DEFAULT_ADMIN", "false").lower() in {"1", "true", "yes"}
    if create_admin:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com").strip().lower()
        admin_pass = os.getenv("ADMIN_PASSWORD", "change-this-password")

        # Check if any admin exists
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin'")
        row = cursor.fetchone()
        if row and row["cnt"] == 0:
            # Avoid circular import at top level by importing get_password_hash inside inside function
            from backend.core.security import get_password_hash

            now_str = datetime.utcnow().isoformat()
            admin_id = str(uuid.uuid4())
            hashed = get_password_hash(admin_pass)
            try:
                cursor.execute(
                    """
                    INSERT INTO users (id, email, password_hash, full_name, role, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'admin', 1, ?, ?)
                    """,
                    (admin_id, admin_email, hashed, "System Administrator", now_str, now_str),
                )
                conn.commit()
                logger.info("[Auth] Bootstrapped default admin account: %s", admin_email)
            except sqlite3.IntegrityError:
                logger.warning("[Auth] Admin email already exists during bootstrap.")
    conn.close()


def _row_to_user(row: sqlite3.Row) -> UserInDB:
    raw_profile = row["learning_profile"] if "learning_profile" in row.keys() else None
    learning_profile = None
    if raw_profile:
        try:
            learning_profile = json.loads(raw_profile)
        except (TypeError, ValueError):
            learning_profile = None
    return UserInDB(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        full_name=row["full_name"],
        role=row["role"],
        is_active=bool(row["is_active"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_login_at=datetime.fromisoformat(row["last_login_at"]) if row["last_login_at"] else None,
        learning_profile=learning_profile,
    )


def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Retrieve user by normalized lowercase email."""
    normalized = email.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (normalized,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return _row_to_user(row)
    return None


def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """Retrieve user by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return _row_to_user(row)
    return None


def create_user(user: UserInDB) -> UserInDB:
    """Insert a new user into database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (id, email, password_hash, full_name, role, is_active, created_at, updated_at, last_login_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user.id,
            user.email.strip().lower(),
            user.password_hash,
            user.full_name,
            user.role,
            1 if user.is_active else 0,
            user.created_at.isoformat(),
            user.updated_at.isoformat(),
            user.last_login_at.isoformat() if user.last_login_at else None,
        ),
    )
    conn.commit()
    conn.close()
    return user


def update_last_login(user_id: str) -> None:
    """Update last_login_at timestamp upon successful login."""
    now_str = datetime.utcnow().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?",
        (now_str, now_str, user_id),
    )
    conn.commit()
    conn.close()


def update_learning_profile(user_id: str, profile: dict[str, Any]) -> None:
    """Persist the user's Learning Profile (personalization for generation output)."""
    now_str = datetime.utcnow().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET learning_profile = ?, updated_at = ? WHERE id = ?",
        (json.dumps(profile, ensure_ascii=False), now_str, user_id),
    )
    conn.commit()
    conn.close()


def get_all_users() -> list[UserInDB]:
    """Retrieve all users ordered by creation date descending."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_user(r) for r in rows]


def count_active_admins() -> int:
    """Count how many active users have role = 'admin'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin' AND is_active = 1")
    row = cursor.fetchone()
    conn.close()
    return row["cnt"] if row else 0


def update_user_fields(user_id: str, updates: dict[str, Any]) -> Optional[UserInDB]:
    """Update specific fields of a user in the database."""
    if not updates:
        return get_user_by_id(user_id)

    valid_cols = {"email", "full_name", "role", "is_active", "password_hash"}
    filtered_updates = {k: v for k, v in updates.items() if k in valid_cols and v is not None}
    if not filtered_updates:
        return get_user_by_id(user_id)

    now_str = datetime.utcnow().isoformat()
    filtered_updates["updated_at"] = now_str

    set_clauses = []
    values = []
    for col, val in filtered_updates.items():
        set_clauses.append(f"{col} = ?")
        if col == "is_active":
            values.append(1 if val else 0)
        elif col == "email" and isinstance(val, str):
            values.append(val.strip().lower())
        else:
            values.append(val)
    values.append(user_id)

    query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()

    return get_user_by_id(user_id)


def delete_user(user_id: str) -> bool:
    """Delete a user from the database by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

