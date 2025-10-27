"""
Main FastAPI application entry point
Neurosurgery Knowledge Base - Backend API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import settings
from backend.utils import configure_root_logger, get_logger
from backend.api import auth_routes, pdf_routes, chapter_routes
from backend.database import db

# Configure logging
configure_root_logger()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events

    Startup:
        - Configure logging
        - Verify database connection
        - Log application start

    Shutdown:
        - Close database connections
        - Log application shutdown
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Verify database connection
    if db.health_check():
        logger.info("Database connection verified")
    else:
        logger.error("Database connection failed!")

    yield

    # Shutdown
    logger.info("Shutting down application")
    db.dispose()
    logger.info("Database connections closed")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered neurosurgery knowledge base with alive chapter generation",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# ==================== Root & Health Check Routes ====================

@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "message": "Neurosurgery Knowledge Base API is running",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    # Check database health
    db_healthy = db.health_check()

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "version": settings.APP_VERSION,
        "database": "connected" if db_healthy else "disconnected"
    }


# ==================== API Router Registration ====================

# Phase 2: Authentication routes
app.include_router(auth_routes.router, prefix="/api/v1", tags=["authentication"])
logger.info("Authentication routes registered at /api/v1/auth")

# Phase 3: PDF routes
app.include_router(pdf_routes.router, prefix="/api/v1", tags=["pdfs"])
logger.info("PDF routes registered at /api/v1/pdfs")

# Phase 4: Chapter routes
app.include_router(chapter_routes.router, prefix="/api/v1", tags=["chapters"])
logger.info("Chapter routes registered at /api/v1/chapters")

# Phase 5: Task routes
from backend.api import task_routes
app.include_router(task_routes.router, prefix="/api/v1", tags=["tasks"])
logger.info("Task routes registered at /api/v1/tasks")

# Future routes will be added here as we build each phase:
# Phase 6: WebSocket routes for real-time updates


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
