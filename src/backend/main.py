"""Main FastAPI application entry point."""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import logger, settings
from app.routers import admin, auth, courses, upload, generation

app = FastAPI(
    title="AI Course Generator API",
    version="3.0.0",
    description="RAG Learning Assistant API - Core Infrastructure & Auth",
)

# Configure CORS (CRITICAL)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,  # MUST BE TRUE for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(courses.router_single)
app.include_router(upload.router)
app.include_router(generation.router)
app.include_router(generation.router_single)
app.include_router(generation.router_generate)
app.include_router(admin.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Global exception handler for HTTPException with consistent format."""
    logger.warning(
        "HTTPException on %s %s - Status: %s - Detail: %s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Global exception handler for unexpected errors without exposing stack traces."""
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau."},
    )


@app.get("/", tags=["root"])
def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "AI Course Generator API v3.0.0"}
