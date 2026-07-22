"""Admin router: user management + upload-pipeline dependency diagnostics."""

import os
from typing import Any, Callable, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db, require_admin
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def get_all_users(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin endpoint to list all users."""
    users = db.query(User).all()
    user_list = [UserResponse.model_validate(u) for u in users]
    return {"users": user_list, "message": f"Hello Admin {admin_user.email}"}


def _classify_network_probe(exc: Exception) -> str:
    """Same network/auth vocabulary as document_processor._classify_pipeline_error, applied
    to a raw probe exception instead of a pipeline failure."""
    text = str(exc)
    lowered = text.lower()
    type_name = type(exc).__name__.lower()

    def _has(*markers: str) -> bool:
        return any(m in lowered or m in type_name for m in markers)

    if _has(
        "connectionerror", "connect timeout", "timed out", "timeout",
        "name or service not known", "getaddrinfo failed", "network is unreachable",
        "connection refused", "apiconnectionerror", "remote end closed", "dns",
    ):
        return "unreachable"
    if _has(
        "401", "unauthorized", "authenticationerror", "invalid_api_key",
        "invalid api key", "access_token_type_unsupported",
    ):
        return "unauthorized"
    return "error"


def _redact_secret(text: str, secret: str) -> str:
    """Defense in depth: strip the configured OpenRouter key out of any probe-failure detail
    before it reaches the response. Not known to trigger today (httpx/openai exception
    strings don't echo request headers) but this endpoint runs a raw HTTP call with the key
    in scope, and nothing upstream guarantees that stays true forever — cheap to make it
    provably safe rather than trust a library's current behavior."""
    if not secret:
        return text
    return text.replace(secret, "[redacted]")


def _probe_result(prober: Callable[[], Any]) -> Dict[str, Any]:
    """Run a probe callable and classify its outcome. Shared by the OpenRouter key-info
    check and the embedding round-trip check so both report status the same way."""
    try:
        prober()
        return {"status": "ok"}
    except Exception as e:
        detail = _redact_secret(str(e), getattr(settings, "OPENROUTER_API_KEY", ""))[:200]
        return {"status": _classify_network_probe(e), "detail": detail}


def _check_database(db: Session) -> Dict[str, Any]:
    try:
        db.execute(sa_text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:200]}


def _check_chroma() -> Dict[str, Any]:
    try:
        from app.services.vector_store import get_vector_store

        vs = get_vector_store()
        vs.client.list_collections()
        return {"status": "ok", "collection": vs.collection_name}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:200]}


def _check_openrouter_key() -> Dict[str, Any]:
    """Zero-generation-cost reachability + auth check: GET /api/v1/key returns usage/limit
    info for the configured key without spending any completion or embedding tokens — so
    this can distinguish "network can't reach OpenRouter at all" from "key is bad" without
    burning money on every diagnostics call."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        return {"status": "skipped", "reason": "test mode"}
    api_key = getattr(settings, "OPENROUTER_API_KEY", "")
    if not api_key:
        return {"status": "skipped", "reason": "no API key configured"}

    def _probe():
        import httpx

        resp = httpx.get(
            "https://openrouter.ai/api/v1/key",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        resp.raise_for_status()

    return _probe_result(_probe)


def _check_embedding() -> Dict[str, Any]:
    """Round-trips one real (near-free, single-token) embedding call through the exact
    OpenRouterEmbeddingFunction code path document_processor uses at upload time — a
    positive result here means the actual upload pipeline's embedding step can reach
    OpenRouter, not just that the host is up."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        return {"status": "skipped", "reason": "test mode"}
    api_key = getattr(settings, "OPENROUTER_API_KEY", "")
    if not api_key:
        return {"status": "skipped", "reason": "no API key configured"}

    from app.services.vector_store import OpenRouterEmbeddingFunction

    ef = OpenRouterEmbeddingFunction(
        api_key=api_key, model=settings.OPENROUTER_EMBEDDING_MODEL, max_retries=1
    )
    return _probe_result(lambda: ef(["ping"]))


@router.get("/diagnostics")
def get_diagnostics(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """One-call health probe for the upload pipeline's external dependencies — DB, Chroma,
    and OpenRouter (auth + a real embedding round-trip). Call this on a freshly-deployed
    server: if openrouter_key/openrouter_embedding come back "unreachable" while the same
    call from a local machine reports "ok", that's a definitive answer that the server's
    network is blocking outbound calls — not a code bug in this project."""
    return {
        "database": _check_database(db),
        "chroma": _check_chroma(),
        "openrouter_key": _check_openrouter_key(),
        "openrouter_embedding": _check_embedding(),
    }
