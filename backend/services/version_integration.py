"""
Version Integration Helper
Provides easy integration of versioning into chapter workflows
"""

from sqlalchemy.orm import Session
from typing import Optional

from backend.database.models import Chapter
from backend.services.version_service import VersionService
from backend.utils import get_logger

logger = get_logger(__name__)


def auto_create_version_on_update(
    db: Session,
    chapter: Chapter,
    user_id: str,
    change_description: Optional[str] = None,
    change_type: str = "update"
) -> bool:
    """
    Automatically create a version snapshot before chapter update

    Call this BEFORE updating a chapter to capture the current state

    Args:
        db: Database session
        chapter: Chapter being updated
        user_id: User making the change
        change_description: Optional description
        change_type: Type of change (update, major_edit, etc.)

    Returns:
        True if version created successfully, False otherwise

    Example:
        # Before updating chapter
        auto_create_version_on_update(db, chapter, str(user.id), "Fixed typos")

        # Then update chapter
        chapter.title = new_title
        db.commit()
    """
    try:
        version_service = VersionService(db)

        version_service.create_version(
            chapter=chapter,
            changed_by=user_id,
            change_description=change_description,
            change_type=change_type
        )

        logger.info(f"Auto-created version for chapter {chapter.id} by user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to auto-create version: {str(e)}")
        # Don't fail the update if versioning fails
        return False


def create_initial_version_if_needed(
    db: Session,
    chapter: Chapter,
    user_id: str
) -> bool:
    """
    Create initial version for chapter if it doesn't have one

    Args:
        db: Database session
        chapter: Chapter to create initial version for
        user_id: User ID

    Returns:
        True if version created, False otherwise
    """
    try:
        version_service = VersionService(db)

        # Check if chapter already has versions
        existing_versions = version_service.get_version_history(
            chapter_id=str(chapter.id),
            limit=1
        )

        if len(existing_versions) == 0:
            version_service.create_version(
                chapter=chapter,
                changed_by=user_id,
                change_description="Initial version",
                change_type="initial"
            )
            logger.info(f"Created initial version for chapter {chapter.id}")
            return True

        return False

    except Exception as e:
        logger.error(f"Failed to create initial version: {str(e)}")
        return False
