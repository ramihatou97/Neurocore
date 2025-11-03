"""
Main FastAPI application entry point
Neurosurgery Knowledge Base - Backend API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import settings
from backend.utils import configure_root_logger, get_logger
from backend.api import auth_routes, pdf_routes, chapter_routes, textbook_routes
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

# Configure Security Headers (Phase 16)
from backend.middleware import SecurityHeadersMiddleware
app.add_middleware(
    SecurityHeadersMiddleware,
    x_frame_options="SAMEORIGIN",
    enable_hsts=not settings.DEBUG,  # Only enable HSTS in production
)
logger.info("Security headers middleware enabled")

# Configure Rate Limiting (Critical Security Fix)
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.services.rate_limit_service import RateLimitStrategy
app.add_middleware(
    RateLimitMiddleware,
    strategy=RateLimitStrategy.SLIDING_WINDOW
)
logger.info("Rate limiting middleware enabled (auth endpoints protected)")


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


# Health check routes - comprehensive monitoring endpoints
from backend.api import health_routes
app.include_router(health_routes.router, tags=["health"])
logger.info("Health check routes registered at /health, /ready, /startup")


# ==================== API Router Registration ====================

# Phase 2: Authentication routes
app.include_router(auth_routes.router, prefix="/api/v1", tags=["authentication"])
logger.info("Authentication routes registered at /api/v1/auth")

# Phase 3: PDF routes
app.include_router(pdf_routes.router, prefix="/api/v1", tags=["pdfs"])
logger.info("PDF routes registered at /api/v1/pdfs")

# Phase 3.5: Textbook routes (Chapter-Level Vector Search - Phase 5)
app.include_router(textbook_routes.router, prefix="/api/v1", tags=["textbooks"])
logger.info("Textbook routes registered at /api/v1/textbooks")

# Phase 4: Chapter routes
app.include_router(chapter_routes.router, prefix="/api/v1", tags=["chapters"])
logger.info("Chapter routes registered at /api/v1/chapters")

# Phase 5: Task routes
from backend.api import task_routes
app.include_router(task_routes.router, prefix="/api/v1", tags=["tasks"])
logger.info("Task routes registered at /api/v1/tasks")

# Phase 6: WebSocket routes
from backend.api import websocket_routes
app.include_router(websocket_routes.router, prefix="/api/v1", tags=["websocket"])
logger.info("WebSocket routes registered at /api/v1/ws")

# Phase 8: Search routes
from backend.api import search_routes
app.include_router(search_routes.router, prefix="/api/v1", tags=["search"])
logger.info("Search routes registered at /api/v1/search")

# Phase 9: Version routes
from backend.api import version_routes
app.include_router(version_routes.router, prefix="/api/v1", tags=["versions"])
logger.info("Version routes registered at /api/v1/versions")

# Phase 11: Export routes
from backend.api import export_routes
app.include_router(export_routes.router, prefix="/api/v1", tags=["export"])
logger.info("Export routes registered at /api/v1/export")

# Phase 12: Analytics routes
from backend.api import analytics_routes
app.include_router(analytics_routes.router, prefix="/api/v1/analytics", tags=["analytics"])
logger.info("Analytics routes registered at /api/v1/analytics")

# Phase 14: AI Features routes
from backend.api import ai_routes
app.include_router(ai_routes.router, prefix="/api/v1/ai", tags=["ai"])
logger.info("AI Features routes registered at /api/v1/ai")

# Phase 15: Performance & Optimization routes
from backend.api import performance_routes
app.include_router(performance_routes.router, prefix="/api/v1/performance", tags=["performance"])
logger.info("Performance monitoring routes registered at /api/v1/performance")

# Phase 18: Advanced Content Features routes
from backend.api import content_features_routes
app.include_router(content_features_routes.router, prefix="/api/v1/content", tags=["content-features"])
logger.info("Content features routes registered at /api/v1/content")

# Circuit Breaker Monitoring routes (Critical Performance Fix)
from backend.api import circuit_breaker_routes
app.include_router(circuit_breaker_routes.router, prefix="/api/v1/monitoring", tags=["monitoring"])
logger.info("Circuit breaker monitoring routes registered at /api/v1/monitoring/circuit-breakers")

# Phase 19: Image routes - recommendations and duplicate detection
from backend.api import image_routes
app.include_router(image_routes.router, tags=["images"])
logger.info("Image routes registered at /api/images")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
