"""Health check endpoints for monitoring."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check() -> JSONResponse:
    """Basic health check endpoint.

    Returns:
        JSONResponse: Service health status
    """
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "service": "ai-supra-agent"},
    )


@router.get("/db")
async def database_health(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Database connectivity health check.

    Args:
        db: Database session dependency

    Returns:
        JSONResponse: Database connection status
    """
    try:
        await db.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=200,
            content={"status": "healthy", "database": "connected"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)},
        )
