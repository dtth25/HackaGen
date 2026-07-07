"""Admin router skeleton."""

from fastapi import APIRouter, Depends
from app.core.deps import require_admin
from app.models.user import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def get_all_users(admin_user: User = Depends(require_admin)):
    """Skeleton admin endpoint to list users."""
    return {"users": [], "message": f"Hello Admin {admin_user.email}"}
