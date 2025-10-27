"""
Version API Routes
Endpoints for chapter version management, comparison, and rollback
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from backend.database.connection import get_db
from backend.database.models import User
from backend.services.version_service import VersionService
from backend.services.diff_service import DiffService, DiffFormat
from backend.utils.dependencies import get_current_user
from backend.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class CreateVersionRequest(BaseModel):
    """Request model for creating a version"""
    change_description: Optional[str] = Field(None, description="Description of changes")
    change_type: str = Field(default="update", description="Type of change")


class RollbackRequest(BaseModel):
    """Request model for rollback"""
    version_number: int = Field(..., description="Version to rollback to", ge=1)
    reason: Optional[str] = Field(None, description="Reason for rollback")


class CompareVersionsRequest(BaseModel):
    """Request model for version comparison"""
    version1: int = Field(..., description="First version number", ge=1)
    version2: int = Field(..., description="Second version number", ge=1)
    format: DiffFormat = Field(default=DiffFormat.SIDE_BY_SIDE, description="Diff format")


# ==================== Version History Endpoints ====================

@router.get("/chapters/{chapter_id}/versions")
async def get_version_history(
    chapter_id: str,
    limit: Optional[int] = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get version history for a chapter

    Returns a list of all versions with metadata (without full content)
    """
    try:
        version_service = VersionService(db)

        versions = version_service.get_version_history(
            chapter_id=chapter_id,
            limit=limit,
            offset=offset
        )

        return {
            "chapter_id": chapter_id,
            "versions": versions,
            "count": len(versions),
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Failed to get version history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get version history: {str(e)}")


@router.get("/chapters/{chapter_id}/versions/{version_number}")
async def get_specific_version(
    chapter_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific version with full content

    Returns complete version data including full content
    """
    try:
        version_service = VersionService(db)

        version = version_service.get_version(
            chapter_id=chapter_id,
            version_number=version_number
        )

        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version_number} not found for chapter {chapter_id}"
            )

        return version.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get version: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get version: {str(e)}")


@router.get("/chapters/{chapter_id}/versions/latest")
async def get_latest_version(
    chapter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the latest version for a chapter

    Returns the most recent version snapshot
    """
    try:
        version_service = VersionService(db)

        version = version_service.get_latest_version(chapter_id)

        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"No versions found for chapter {chapter_id}"
            )

        return version.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest version: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get latest version: {str(e)}")


# ==================== Version Comparison Endpoints ====================

@router.post("/chapters/{chapter_id}/versions/compare")
async def compare_versions(
    chapter_id: str,
    request: CompareVersionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compare two versions of a chapter

    Returns a diff showing changes between the two versions
    """
    try:
        version_service = VersionService(db)

        # Get both versions
        version1 = version_service.get_version(chapter_id, request.version1)
        version2 = version_service.get_version(chapter_id, request.version2)

        if not version1:
            raise HTTPException(
                status_code=404,
                detail=f"Version {request.version1} not found"
            )

        if not version2:
            raise HTTPException(
                status_code=404,
                detail=f"Version {request.version2} not found"
            )

        # Generate diff
        diff_result = DiffService.generate_diff(
            text1=version1.content,
            text2=version2.content,
            format=request.format
        )

        # Get change summary
        change_summary = DiffService.get_change_summary(
            text1=version1.content,
            text2=version2.content
        )

        return {
            "chapter_id": chapter_id,
            "version1": {
                "number": version1.version_number,
                "title": version1.title,
                "created_at": version1.created_at.isoformat(),
                "changed_by": str(version1.changed_by)
            },
            "version2": {
                "number": version2.version_number,
                "title": version2.title,
                "created_at": version2.created_at.isoformat(),
                "changed_by": str(version2.changed_by)
            },
            "diff": diff_result,
            "summary": change_summary
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare versions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compare versions: {str(e)}")


@router.get("/chapters/{chapter_id}/versions/{version_number}/diff")
async def get_version_diff(
    chapter_id: str,
    version_number: int,
    compare_to: Optional[int] = Query(default=None, description="Version to compare to (defaults to current)"),
    format: DiffFormat = Query(default=DiffFormat.SIDE_BY_SIDE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get diff between a specific version and another version (or current)

    Convenient endpoint for comparing a version to current chapter state
    """
    try:
        from backend.database.models import Chapter

        version_service = VersionService(db)

        # Get the specified version
        version = version_service.get_version(chapter_id, version_number)
        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version_number} not found"
            )

        # Get comparison target
        if compare_to:
            compare_version = version_service.get_version(chapter_id, compare_to)
            if not compare_version:
                raise HTTPException(
                    status_code=404,
                    detail=f"Version {compare_to} not found"
                )
            compare_text = compare_version.content
            compare_label = f"Version {compare_to}"
        else:
            # Compare to current chapter
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                raise HTTPException(status_code=404, detail="Chapter not found")

            # Extract current content
            if hasattr(chapter, 'sections') and chapter.sections:
                if isinstance(chapter.sections, list):
                    compare_text = "\n\n".join(
                        section.get("content", "") for section in chapter.sections
                    )
                else:
                    compare_text = str(chapter.sections)
            else:
                compare_text = getattr(chapter, 'content', '')

            compare_label = "Current version"

        # Generate diff
        diff_result = DiffService.generate_diff(
            text1=version.content,
            text2=compare_text,
            format=format
        )

        return {
            "chapter_id": chapter_id,
            "version": version_number,
            "comparing_to": compare_label,
            "diff": diff_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get version diff: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get version diff: {str(e)}")


# ==================== Rollback Endpoint ====================

@router.post("/chapters/{chapter_id}/versions/rollback")
async def rollback_to_version(
    chapter_id: str,
    request: RollbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rollback chapter to a previous version

    Creates a new version with content from the specified version
    """
    try:
        version_service = VersionService(db)

        # Perform rollback
        chapter, new_version = version_service.rollback_to_version(
            chapter_id=chapter_id,
            version_number=request.version_number,
            user_id=str(current_user.id),
            reason=request.reason
        )

        logger.info(f"User {current_user.id} rolled back chapter {chapter_id} to version {request.version_number}")

        return {
            "success": True,
            "message": f"Successfully rolled back to version {request.version_number}",
            "chapter_id": str(chapter.id),
            "new_version": new_version.to_summary_dict(),
            "rolled_back_to": request.version_number
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to rollback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rollback: {str(e)}")


# ==================== Statistics Endpoints ====================

@router.get("/chapters/{chapter_id}/versions/stats")
async def get_version_statistics(
    chapter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about versions for a chapter

    Returns counts, contributors, and other metrics
    """
    try:
        version_service = VersionService(db)

        stats = version_service.get_version_statistics(chapter_id)

        return {
            "chapter_id": chapter_id,
            "statistics": stats
        }

    except Exception as e:
        logger.error(f"Failed to get version statistics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


# ==================== User Activity Endpoints ====================

@router.get("/users/{user_id}/versions")
async def get_user_versions(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get versions created by a specific user

    Returns version history for a user's contributions
    """
    try:
        # Check if user can access this data (must be same user or admin)
        if str(current_user.id) != user_id and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view this user's version history"
            )

        version_service = VersionService(db)

        versions = version_service.get_versions_by_user(
            user_id=user_id,
            limit=limit
        )

        return {
            "user_id": user_id,
            "versions": versions,
            "count": len(versions)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user versions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get user versions: {str(e)}")


# ==================== Maintenance Endpoints ====================

@router.delete("/chapters/{chapter_id}/versions/cleanup")
async def cleanup_old_versions(
    chapter_id: str,
    keep_count: int = Query(default=10, ge=5, le=100, description="Number of recent versions to keep"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete old versions, keeping only recent ones

    Requires admin role
    """
    try:
        # Check admin permission
        if current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Admin role required to cleanup versions"
            )

        version_service = VersionService(db)

        deleted_count = version_service.delete_old_versions(
            chapter_id=chapter_id,
            keep_count=keep_count
        )

        logger.info(f"Admin {current_user.id} cleaned up {deleted_count} versions from chapter {chapter_id}")

        return {
            "success": True,
            "message": f"Deleted {deleted_count} old versions",
            "kept_count": keep_count,
            "deleted_count": deleted_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup versions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cleanup versions: {str(e)}")


# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """Version service health check"""
    return {
        "status": "healthy",
        "service": "versions",
        "features": [
            "version_history",
            "version_comparison",
            "rollback",
            "diff_generation",
            "statistics"
        ]
    }
