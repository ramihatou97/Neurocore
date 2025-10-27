"""
Chapter Service - Business logic for chapter operations
Wraps ChapterOrchestrator and provides CRUD operations
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException

from backend.database.models import Chapter, User
from backend.services.chapter_orchestrator import ChapterOrchestrator
from backend.utils import get_logger

logger = get_logger(__name__)


class ChapterService:
    """
    Service for chapter management

    Provides:
    - Chapter generation (delegates to ChapterOrchestrator)
    - Chapter CRUD operations
    - Chapter versioning
    - Chapter search and filtering
    """

    def __init__(self, db_session: Session):
        """
        Initialize chapter service

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.orchestrator = ChapterOrchestrator(db_session)

    async def create_chapter(
        self,
        topic: str,
        user: User,
        chapter_type: Optional[str] = None
    ) -> Chapter:
        """
        Create and generate a new chapter

        Args:
            topic: Chapter topic/query
            user: User requesting the chapter
            chapter_type: Optional chapter type

        Returns:
            Generated Chapter object

        Raises:
            HTTPException: If generation fails
        """
        logger.info(f"Creating chapter: '{topic}' for user {user.email}")

        try:
            chapter = await self.orchestrator.generate_chapter(
                topic=topic,
                user=user,
                chapter_type=chapter_type
            )
            return chapter

        except Exception as e:
            logger.error(f"Chapter creation failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Chapter generation failed: {str(e)}"
            )

    def get_chapter(self, chapter_id: str) -> Chapter:
        """
        Get chapter by ID

        Args:
            chapter_id: Chapter ID

        Returns:
            Chapter object

        Raises:
            HTTPException: If chapter not found
        """
        chapter = self.db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")
        return chapter

    def list_chapters(
        self,
        user_id: Optional[str] = None,
        chapter_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Chapter]:
        """
        List chapters with filtering

        Args:
            user_id: Filter by user ID
            chapter_type: Filter by chapter type
            status: Filter by generation status
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of Chapter objects
        """
        query = self.db.query(Chapter)

        # Apply filters
        if user_id:
            query = query.filter(Chapter.author_id == user_id)

        if chapter_type:
            query = query.filter(Chapter.chapter_type == chapter_type)

        if status:
            query = query.filter(Chapter.generation_status == status)

        # Order by creation date (most recent first)
        query = query.order_by(Chapter.created_at.desc())

        # Pagination
        query = query.offset(skip).limit(limit)

        return query.all()

    def search_chapters(
        self,
        query: str,
        max_results: int = 20
    ) -> List[Chapter]:
        """
        Search chapters by title or content

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of matching Chapter objects
        """
        search_term = f"%{query}%"

        chapters = self.db.query(Chapter).filter(
            or_(
                Chapter.title.ilike(search_term),
                Chapter.generation_status == "completed"
            )
        ).limit(max_results).all()

        return chapters

    def get_chapter_versions(self, chapter_id: str) -> List[Chapter]:
        """
        Get all versions of a chapter

        Args:
            chapter_id: Chapter ID

        Returns:
            List of Chapter versions
        """
        # Get the base chapter
        chapter = self.get_chapter(chapter_id)

        # Find all related versions
        versions = self.db.query(Chapter).filter(
            or_(
                Chapter.id == chapter_id,
                Chapter.parent_version_id == chapter_id
            )
        ).order_by(Chapter.created_at.desc()).all()

        return versions

    async def regenerate_chapter(
        self,
        chapter_id: str,
        user: User
    ) -> Chapter:
        """
        Regenerate an existing chapter (create new version)

        Args:
            chapter_id: Original chapter ID
            user: User requesting regeneration

        Returns:
            New Chapter version

        Raises:
            HTTPException: If original chapter not found
        """
        original = self.get_chapter(chapter_id)

        logger.info(f"Regenerating chapter {chapter_id} for user {user.email}")

        # Create new version
        new_chapter = await self.orchestrator.generate_chapter(
            topic=original.title,
            user=user,
            chapter_type=original.chapter_type
        )

        # Link to original
        new_chapter.parent_version_id = original.id

        # Mark original as not current
        original.is_current_version = False

        self.db.commit()

        return new_chapter

    def delete_chapter(self, chapter_id: str) -> Dict[str, Any]:
        """
        Delete a chapter

        Args:
            chapter_id: Chapter ID

        Returns:
            Dictionary with deletion info

        Raises:
            HTTPException: If chapter not found
        """
        chapter = self.get_chapter(chapter_id)

        # Check if this chapter has child versions
        child_versions = self.db.query(Chapter).filter(
            Chapter.parent_version_id == chapter_id
        ).count()

        if child_versions > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete chapter with {child_versions} child versions"
            )

        self.db.delete(chapter)
        self.db.commit()

        logger.info(f"Chapter deleted: {chapter_id}")

        return {
            "chapter_id": chapter_id,
            "title": chapter.title,
            "status": "deleted"
        }

    def get_chapter_statistics(self) -> Dict[str, Any]:
        """
        Get overall chapter statistics

        Returns:
            Dictionary with statistics
        """
        total_chapters = self.db.query(Chapter).count()
        completed_chapters = self.db.query(Chapter).filter(
            Chapter.generation_status == "completed"
        ).count()
        failed_chapters = self.db.query(Chapter).filter(
            Chapter.generation_status == "failed"
        ).count()
        in_progress = self.db.query(Chapter).filter(
            Chapter.generation_status.like("stage_%")
        ).count()

        # Get average scores
        avg_depth = self.db.query(Chapter).filter(
            Chapter.depth_score.isnot(None)
        ).with_entities(Chapter.depth_score).all()

        avg_depth_score = sum(s[0] for s in avg_depth) / len(avg_depth) if avg_depth else 0

        return {
            "total_chapters": total_chapters,
            "completed": completed_chapters,
            "failed": failed_chapters,
            "in_progress": in_progress,
            "average_depth_score": round(avg_depth_score, 2),
            "completion_rate": round(completed_chapters / total_chapters * 100, 1) if total_chapters > 0 else 0
        }

    def get_user_chapters(
        self,
        user_id: str,
        include_draft: bool = True
    ) -> List[Chapter]:
        """
        Get all chapters for a specific user

        Args:
            user_id: User ID
            include_draft: Include chapters in progress

        Returns:
            List of user's chapters
        """
        query = self.db.query(Chapter).filter(Chapter.author_id == user_id)

        if not include_draft:
            query = query.filter(Chapter.generation_status == "completed")

        query = query.order_by(Chapter.created_at.desc())

        return query.all()

    def export_chapter_markdown(self, chapter_id: str) -> str:
        """
        Export chapter as markdown

        Args:
            chapter_id: Chapter ID

        Returns:
            Markdown-formatted chapter

        Raises:
            HTTPException: If chapter not found or not completed
        """
        chapter = self.get_chapter(chapter_id)

        if chapter.generation_status != "completed":
            raise HTTPException(
                status_code=400,
                detail="Chapter must be completed before export"
            )

        # Build markdown
        markdown = f"# {chapter.title}\n\n"

        # Add metadata
        markdown += f"**Type:** {chapter.chapter_type}\n\n"
        markdown += f"**Version:** {chapter.version}\n\n"
        markdown += f"**Generated:** {chapter.updated_at}\n\n"

        # Add scores
        markdown += "## Quality Metrics\n\n"
        markdown += f"- Depth Score: {chapter.depth_score:.2f}\n"
        markdown += f"- Coverage Score: {chapter.coverage_score:.2f}\n"
        markdown += f"- Evidence Score: {chapter.evidence_score:.2f}\n"
        markdown += f"- Currency Score: {chapter.currency_score:.2f}\n\n"

        markdown += "---\n\n"

        # Add sections
        sections = chapter.sections or []
        for section in sections:
            markdown += f"## {section.get('title')}\n\n"
            markdown += f"{section.get('content')}\n\n"

            # Add images if any
            images = section.get('images', [])
            for img in images:
                markdown += f"![{img.get('description', 'Image')}]({img.get('file_path')})\n\n"

        # Add references if available
        if hasattr(chapter, 'references') and chapter.references:
            markdown += "## References\n\n"
            references = chapter.references
            for ref in references:
                authors = ", ".join(ref.get('authors', [])[:3])
                if len(ref.get('authors', [])) > 3:
                    authors += " et al."

                markdown += f"{ref.get('ref_num')}. {authors} ({ref.get('year')}). "
                markdown += f"{ref.get('title')}. "
                markdown += f"*{ref.get('journal')}*. "

                if ref.get('doi'):
                    markdown += f"DOI: {ref.get('doi')}"

                markdown += "\n\n"

        return markdown
