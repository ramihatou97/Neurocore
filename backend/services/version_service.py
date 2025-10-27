"""
Version Service - Chapter Version Management
Handles version creation, retrieval, comparison, and rollback
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime

from backend.database.models import Chapter, ChapterVersion, User
from backend.utils import get_logger

logger = get_logger(__name__)


class VersionService:
    """
    Service for managing chapter versions

    Provides functionality for:
    - Creating version snapshots
    - Retrieving version history
    - Comparing versions
    - Rolling back to previous versions
    - Version statistics and analytics
    """

    def __init__(self, db: Session):
        """
        Initialize version service

        Args:
            db: Database session
        """
        self.db = db

    def create_version(
        self,
        chapter: Chapter,
        changed_by: str,
        change_description: Optional[str] = None,
        change_type: str = "update"
    ) -> ChapterVersion:
        """
        Create a new version snapshot of a chapter

        Args:
            chapter: Chapter to create version for
            changed_by: User ID who made the change
            change_description: Optional description of changes
            change_type: Type of change (update, rollback, major_edit, initial)

        Returns:
            Created ChapterVersion object
        """
        try:
            # Get next version number
            next_version = self._get_next_version_number(chapter.id)

            # Get previous version for change size calculation
            previous_version = self._get_latest_version(chapter.id)
            change_size = 0
            if previous_version:
                change_size = len(chapter.content or "") - len(previous_version.content or "")

            # Calculate word count
            word_count = len((chapter.content or "").split())
            character_count = len(chapter.content or "")

            # Extract content from sections if chapter uses sections
            content = chapter.content if hasattr(chapter, 'content') else ""
            if hasattr(chapter, 'sections') and chapter.sections:
                # Concatenate section content
                if isinstance(chapter.sections, list):
                    content = "\n\n".join(
                        section.get("content", "") for section in chapter.sections
                    )
                    word_count = sum(section.get("word_count", 0) for section in chapter.sections)

            # Get summary from first section or chapter summary
            summary = ""
            if hasattr(chapter, 'sections') and chapter.sections and isinstance(chapter.sections, list):
                # Use first section as summary
                if len(chapter.sections) > 0:
                    summary = chapter.sections[0].get("content", "")[:500] + "..."
            elif hasattr(chapter, 'summary'):
                summary = chapter.summary

            # Create version snapshot
            version = ChapterVersion(
                chapter_id=chapter.id,
                version_number=next_version,
                title=chapter.title,
                content=content,
                summary=summary,
                word_count=word_count,
                character_count=character_count,
                change_size=change_size,
                changed_by=changed_by,
                change_description=change_description or f"Version {next_version}",
                change_type=change_type,
                metadata={
                    "chapter_type": chapter.chapter_type,
                    "generation_status": chapter.generation_status,
                    "version": chapter.version,  # Semantic version from chapter
                }
            )

            self.db.add(version)
            self.db.commit()
            self.db.refresh(version)

            logger.info(f"Created version {next_version} for chapter {chapter.id}")

            return version

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create version for chapter {chapter.id}: {str(e)}")
            raise

    def get_version_history(
        self,
        chapter_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a chapter

        Args:
            chapter_id: Chapter ID
            limit: Maximum number of versions to return
            offset: Pagination offset

        Returns:
            List of version summaries (without full content)
        """
        try:
            query = self.db.query(ChapterVersion).filter(
                ChapterVersion.chapter_id == chapter_id
            ).order_by(desc(ChapterVersion.version_number))

            if limit:
                query = query.limit(limit).offset(offset)

            versions = query.all()

            return [v.to_summary_dict() for v in versions]

        except Exception as e:
            logger.error(f"Failed to get version history for chapter {chapter_id}: {str(e)}")
            raise

    def get_version(
        self,
        chapter_id: str,
        version_number: int
    ) -> Optional[ChapterVersion]:
        """
        Get a specific version

        Args:
            chapter_id: Chapter ID
            version_number: Version number to retrieve

        Returns:
            ChapterVersion object or None if not found
        """
        try:
            version = self.db.query(ChapterVersion).filter(
                ChapterVersion.chapter_id == chapter_id,
                ChapterVersion.version_number == version_number
            ).first()

            return version

        except Exception as e:
            logger.error(f"Failed to get version {version_number} for chapter {chapter_id}: {str(e)}")
            raise

    def get_latest_version(self, chapter_id: str) -> Optional[ChapterVersion]:
        """
        Get the latest version for a chapter

        Args:
            chapter_id: Chapter ID

        Returns:
            Latest ChapterVersion or None
        """
        return self._get_latest_version(chapter_id)

    def rollback_to_version(
        self,
        chapter_id: str,
        version_number: int,
        user_id: str,
        reason: Optional[str] = None
    ) -> Tuple[Chapter, ChapterVersion]:
        """
        Rollback chapter to a previous version

        Creates a new version with content from the specified version

        Args:
            chapter_id: Chapter ID
            version_number: Version number to rollback to
            user_id: User performing the rollback
            reason: Optional reason for rollback

        Returns:
            Tuple of (updated Chapter, new ChapterVersion)

        Raises:
            ValueError: If version or chapter not found
        """
        try:
            # Get the chapter
            chapter = self.db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                raise ValueError(f"Chapter {chapter_id} not found")

            # Get the version to rollback to
            target_version = self.get_version(chapter_id, version_number)
            if not target_version:
                raise ValueError(f"Version {version_number} not found for chapter {chapter_id}")

            # Create a version snapshot of current state before rollback
            self.create_version(
                chapter=chapter,
                changed_by=user_id,
                change_description=f"Before rollback to version {version_number}",
                change_type="pre_rollback"
            )

            # Update chapter content from target version
            chapter.title = target_version.title

            # Handle content restoration
            if hasattr(chapter, 'sections'):
                # Parse content back into sections format
                # For simplicity, create one section with the full content
                chapter.sections = [{
                    "section_num": 1,
                    "title": "Content",
                    "content": target_version.content,
                    "word_count": target_version.word_count
                }]
            else:
                chapter.content = target_version.content

            chapter.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(chapter)

            # Create new version after rollback
            new_version = self.create_version(
                chapter=chapter,
                changed_by=user_id,
                change_description=reason or f"Rolled back to version {version_number}",
                change_type="rollback"
            )

            logger.info(f"Rolled back chapter {chapter_id} to version {version_number}")

            return chapter, new_version

        except ValueError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to rollback chapter {chapter_id} to version {version_number}: {str(e)}")
            raise

    def get_version_statistics(self, chapter_id: str) -> Dict[str, Any]:
        """
        Get statistics about versions for a chapter

        Args:
            chapter_id: Chapter ID

        Returns:
            Dictionary with version statistics
        """
        try:
            stats = self.db.query(
                func.count(ChapterVersion.id).label("total_versions"),
                func.min(ChapterVersion.created_at).label("first_version_date"),
                func.max(ChapterVersion.created_at).label("last_version_date"),
                func.count(func.distinct(ChapterVersion.changed_by)).label("unique_contributors"),
                func.sum(ChapterVersion.character_count).label("total_content_size"),
                func.avg(ChapterVersion.word_count).label("avg_word_count"),
                func.max(ChapterVersion.version_number).label("latest_version_number")
            ).filter(
                ChapterVersion.chapter_id == chapter_id
            ).first()

            if not stats or stats.total_versions == 0:
                return {
                    "total_versions": 0,
                    "first_version_date": None,
                    "last_version_date": None,
                    "unique_contributors": 0,
                    "total_content_size": 0,
                    "avg_word_count": 0,
                    "latest_version_number": 0
                }

            return {
                "total_versions": stats.total_versions,
                "first_version_date": stats.first_version_date.isoformat() if stats.first_version_date else None,
                "last_version_date": stats.last_version_date.isoformat() if stats.last_version_date else None,
                "unique_contributors": stats.unique_contributors,
                "total_content_size": stats.total_content_size or 0,
                "avg_word_count": float(stats.avg_word_count) if stats.avg_word_count else 0,
                "latest_version_number": stats.latest_version_number or 0
            }

        except Exception as e:
            logger.error(f"Failed to get version statistics for chapter {chapter_id}: {str(e)}")
            raise

    def delete_old_versions(
        self,
        chapter_id: str,
        keep_count: int = 10
    ) -> int:
        """
        Delete old versions, keeping only the most recent N versions

        Args:
            chapter_id: Chapter ID
            keep_count: Number of recent versions to keep

        Returns:
            Number of versions deleted
        """
        try:
            # Get versions to delete (older than keep_count)
            versions_to_delete = self.db.query(ChapterVersion).filter(
                ChapterVersion.chapter_id == chapter_id
            ).order_by(desc(ChapterVersion.version_number)).offset(keep_count).all()

            count = len(versions_to_delete)

            for version in versions_to_delete:
                self.db.delete(version)

            self.db.commit()

            logger.info(f"Deleted {count} old versions for chapter {chapter_id}")

            return count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete old versions for chapter {chapter_id}: {str(e)}")
            raise

    def get_versions_by_user(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get versions created by a specific user

        Args:
            user_id: User ID
            limit: Maximum number of versions to return

        Returns:
            List of version summaries
        """
        try:
            versions = self.db.query(ChapterVersion).filter(
                ChapterVersion.changed_by == user_id
            ).order_by(desc(ChapterVersion.created_at)).limit(limit).all()

            return [v.to_summary_dict() for v in versions]

        except Exception as e:
            logger.error(f"Failed to get versions for user {user_id}: {str(e)}")
            raise

    def _get_next_version_number(self, chapter_id: str) -> int:
        """Get the next version number for a chapter"""
        max_version = self.db.query(
            func.max(ChapterVersion.version_number)
        ).filter(
            ChapterVersion.chapter_id == chapter_id
        ).scalar()

        return (max_version or 0) + 1

    def _get_latest_version(self, chapter_id: str) -> Optional[ChapterVersion]:
        """Get the latest version for a chapter"""
        return self.db.query(ChapterVersion).filter(
            ChapterVersion.chapter_id == chapter_id
        ).order_by(desc(ChapterVersion.version_number)).first()
