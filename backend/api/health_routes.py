"""
Health Check Routes for Phase 16: Production Readiness
Comprehensive health, readiness, and startup endpoints for monitoring
"""

from fastapi import APIRouter, status, Depends
from typing import Dict, Any
from datetime import datetime
import os
import psutil
from sqlalchemy import text

from backend.database import get_db
from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Health Check - Basic liveness probe
# =============================================================================

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint - Returns 200 if service is alive

    This is a lightweight check that verifies the application is running.
    Use this for Kubernetes liveness probes.

    Returns:
        dict: Basic health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "neurocore-api",
        "version": settings.APP_VERSION
    }


# =============================================================================
# Readiness Check - Complete system readiness
# =============================================================================

@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db=Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness check endpoint - Verifies all dependencies are ready

    Checks:
    - Database connection and query execution
    - Redis connection (if applicable)
    - Disk space availability
    - Memory availability

    Use this for Kubernetes readiness probes.

    Returns:
        dict: Detailed readiness status with all checks

    Raises:
        HTTPException: 503 if any check fails
    """
    checks = {}
    all_healthy = True

    # Check database
    try:
        result = db.execute(text("SELECT 1"))
        result.scalar()
        checks["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        checks["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        all_healthy = False

    # Check Redis (optional, won't fail readiness if Redis is down)
    try:
        from backend.config.redis import redis_manager
        redis_client = redis_manager.get_client()
        if redis_client:
            redis_client.ping()
            checks["redis"] = {
                "status": "healthy",
                "message": "Redis connection successful"
            }
        else:
            checks["redis"] = {
                "status": "degraded",
                "message": "Redis not configured"
            }
    except Exception as e:
        logger.warning(f"Redis health check failed: {str(e)}")
        checks["redis"] = {
            "status": "degraded",
            "message": f"Redis connection failed (non-critical): {str(e)}"
        }
        # Don't fail readiness for Redis issues

    # Check disk space
    try:
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent

        if disk_percent > 90:
            checks["disk_space"] = {
                "status": "critical",
                "message": f"Disk usage at {disk_percent}%",
                "available_gb": round(disk.free / (1024**3), 2)
            }
            all_healthy = False
        elif disk_percent > 80:
            checks["disk_space"] = {
                "status": "warning",
                "message": f"Disk usage at {disk_percent}%",
                "available_gb": round(disk.free / (1024**3), 2)
            }
        else:
            checks["disk_space"] = {
                "status": "healthy",
                "message": f"Disk usage at {disk_percent}%",
                "available_gb": round(disk.free / (1024**3), 2)
            }
    except Exception as e:
        logger.error(f"Disk space check failed: {str(e)}")
        checks["disk_space"] = {
            "status": "unknown",
            "message": f"Could not check disk space: {str(e)}"
        }

    # Check memory
    try:
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        if memory_percent > 90:
            checks["memory"] = {
                "status": "critical",
                "message": f"Memory usage at {memory_percent}%",
                "available_gb": round(memory.available / (1024**3), 2)
            }
            all_healthy = False
        elif memory_percent > 80:
            checks["memory"] = {
                "status": "warning",
                "message": f"Memory usage at {memory_percent}%",
                "available_gb": round(memory.available / (1024**3), 2)
            }
        else:
            checks["memory"] = {
                "status": "healthy",
                "message": f"Memory usage at {memory_percent}%",
                "available_gb": round(memory.available / (1024**3), 2)
            }
    except Exception as e:
        logger.error(f"Memory check failed: {str(e)}")
        checks["memory"] = {
            "status": "unknown",
            "message": f"Could not check memory: {str(e)}"
        }

    # Overall status
    overall_status = "ready" if all_healthy else "not_ready"

    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "neurocore-api",
        "version": settings.APP_VERSION,
        "checks": checks
    }

    # Return 503 if not ready
    if not all_healthy:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response
        )

    return response


# =============================================================================
# Startup Check - Initial system startup verification
# =============================================================================

@router.get("/startup", status_code=status.HTTP_200_OK)
async def startup_check(db=Depends(get_db)) -> Dict[str, Any]:
    """
    Startup check endpoint - Verifies initial system startup

    This should be called once during container startup to verify
    the application is fully initialized before accepting traffic.

    Checks:
    - Database migrations are applied
    - Required tables exist
    - Database is accessible

    Use this for Kubernetes startup probes.

    Returns:
        dict: Startup status

    Raises:
        HTTPException: 503 if startup checks fail
    """
    checks = {}
    all_ready = True

    # Check database connection
    try:
        result = db.execute(text("SELECT 1"))
        result.scalar()
        checks["database_connection"] = {
            "status": "ready",
            "message": "Database connection established"
        }
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        checks["database_connection"] = {
            "status": "not_ready",
            "message": f"Database connection failed: {str(e)}"
        }
        all_ready = False

    # Check required tables exist
    try:
        required_tables = ['users', 'pdfs', 'chapters', 'images']
        for table in required_tables:
            result = db.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = :table_name
                )
            """), {"table_name": table})

            exists = result.scalar()
            if not exists:
                checks[f"table_{table}"] = {
                    "status": "not_ready",
                    "message": f"Table {table} does not exist"
                }
                all_ready = False

        if all_ready:
            checks["database_schema"] = {
                "status": "ready",
                "message": "All required tables exist"
            }
    except Exception as e:
        logger.error(f"Database schema check failed: {str(e)}")
        checks["database_schema"] = {
            "status": "not_ready",
            "message": f"Schema check failed: {str(e)}"
        }
        all_ready = False

    # Check data directories
    try:
        pdf_dir = settings.PDF_STORAGE_PATH
        image_dir = settings.IMAGE_STORAGE_PATH

        dirs_ok = True
        if not os.path.exists(pdf_dir):
            checks["pdf_storage"] = {
                "status": "not_ready",
                "message": f"PDF storage directory does not exist: {pdf_dir}"
            }
            dirs_ok = False
            all_ready = False

        if not os.path.exists(image_dir):
            checks["image_storage"] = {
                "status": "not_ready",
                "message": f"Image storage directory does not exist: {image_dir}"
            }
            dirs_ok = False
            all_ready = False

        if dirs_ok:
            checks["storage"] = {
                "status": "ready",
                "message": "All storage directories exist"
            }
    except Exception as e:
        logger.error(f"Storage check failed: {str(e)}")
        checks["storage"] = {
            "status": "not_ready",
            "message": f"Storage check failed: {str(e)}"
        }
        all_ready = False

    # Overall status
    overall_status = "ready" if all_ready else "not_ready"

    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "neurocore-api",
        "version": settings.APP_VERSION,
        "checks": checks
    }

    # Return 503 if not ready
    if not all_ready:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response
        )

    return response


# =============================================================================
# Detailed Health Check - Comprehensive system health
# =============================================================================

@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check(db=Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check endpoint - Comprehensive system health report

    Provides detailed information about system health including:
    - All basic health checks
    - Database connection pool stats
    - System resource usage
    - Application metrics

    This endpoint is more expensive and should be called less frequently.
    Use for monitoring dashboards and alerting.

    Returns:
        dict: Comprehensive health report
    """
    health_report = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "neurocore-api",
        "version": settings.APP_VERSION,
        "environment": "production" if not settings.DEBUG else "development",
        "checks": {},
        "metrics": {}
    }

    # Database health
    try:
        db.execute(text("SELECT 1")).scalar()
        health_report["checks"]["database"] = {
            "status": "healthy",
            "connection_string": f"postgresql://{settings.DB_USER}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        }
    except Exception as e:
        health_report["status"] = "degraded"
        health_report["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Redis health
    try:
        from backend.config.redis import redis_manager
        redis_client = redis_manager.get_client()
        if redis_client:
            redis_client.ping()
            info = redis_client.info()
            health_report["checks"]["redis"] = {
                "status": "healthy",
                "used_memory_mb": round(info.get('used_memory', 0) / (1024**2), 2),
                "connected_clients": info.get('connected_clients', 0),
                "uptime_days": round(info.get('uptime_in_seconds', 0) / 86400, 2)
            }
    except Exception as e:
        health_report["checks"]["redis"] = {
            "status": "unavailable",
            "error": str(e)
        }

    # System metrics
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        health_report["metrics"]["system"] = {
            "cpu_usage_percent": cpu_percent,
            "memory_usage_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_usage_percent": disk.percent,
            "disk_available_gb": round(disk.free / (1024**3), 2)
        }
    except Exception as e:
        health_report["metrics"]["system_error"] = str(e)

    # Application uptime
    try:
        import time
        if not hasattr(startup_check, 'start_time'):
            startup_check.start_time = time.time()

        uptime_seconds = time.time() - startup_check.start_time
        health_report["metrics"]["uptime_seconds"] = round(uptime_seconds, 2)
        health_report["metrics"]["uptime_hours"] = round(uptime_seconds / 3600, 2)
    except Exception as e:
        health_report["metrics"]["uptime_error"] = str(e)

    return health_report


# Initialize startup time
import time
startup_check.start_time = time.time()
