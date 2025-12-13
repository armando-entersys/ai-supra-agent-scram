"""AI-SupraAgent Backend - FastAPI Application Entry Point.

Main application module with CORS, health checks, and API routing.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings

# ═══════════════════════════════════════════════════════════════
# Logging Configuration
# ═══════════════════════════════════════════════════════════════
settings = get_settings()

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════
# Application Lifespan
# ═══════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None during application runtime
    """
    # Startup
    logger.info(
        "Starting AI-SupraAgent Backend",
        environment=settings.environment,
        log_level=settings.log_level,
    )
    yield
    # Shutdown
    logger.info("Shutting down AI-SupraAgent Backend")


# ═══════════════════════════════════════════════════════════════
# FastAPI Application
# ═══════════════════════════════════════════════════════════════
app = FastAPI(
    title="AI-SupraAgent API",
    description="Agente de IA conversacional con RAG y herramientas MCP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ═══════════════════════════════════════════════════════════════
# CORS Middleware
# ═══════════════════════════════════════════════════════════════
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# ═══════════════════════════════════════════════════════════════
# Health Check Endpoint
# ═══════════════════════════════════════════════════════════════
@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """Health check endpoint for container orchestration.

    Returns:
        JSONResponse: Health status with HTTP 200
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "ai-supra-agent-backend",
            "version": "1.0.0",
        },
    )


@app.get("/", tags=["Root"])
async def root() -> JSONResponse:
    """Root endpoint with API information.

    Returns:
        JSONResponse: API welcome message
    """
    return JSONResponse(
        status_code=200,
        content={
            "message": "AI-SupraAgent API",
            "docs": "/docs" if not settings.is_production else "Disabled in production",
            "health": "/health",
        },
    )


# ═══════════════════════════════════════════════════════════════
# API Routers
# ═══════════════════════════════════════════════════════════════
from src.api.v1 import chat, documents, health

app.include_router(health.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
