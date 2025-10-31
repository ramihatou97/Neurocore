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
from backend.services.gap_analyzer import GapAnalyzer
from backend.config.settings import settings
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

    def edit_section(
        self,
        chapter_id: str,
        section_number: int,
        new_content: str,
        user: User
    ) -> Chapter:
        """
        Edit a section's content directly without AI regeneration

        Args:
            chapter_id: Chapter ID
            section_number: Section number to edit (0-indexed)
            new_content: New HTML content for the section
            user: User making the edit

        Returns:
            Updated Chapter object

        Raises:
            HTTPException: If chapter not found or section doesn't exist
        """
        chapter = self.get_chapter(chapter_id)

        # Validate sections exist
        if not chapter.sections or not isinstance(chapter.sections, list):
            raise HTTPException(
                status_code=400,
                detail="Chapter has no sections"
            )

        if section_number < 0 or section_number >= len(chapter.sections):
            raise HTTPException(
                status_code=400,
                detail=f"Section {section_number} does not exist (chapter has {len(chapter.sections)} sections)"
            )

        # Update section content
        chapter.sections[section_number]["content"] = new_content
        chapter.sections[section_number]["edited_at"] = str(chapter.updated_at)
        chapter.sections[section_number]["edited_by"] = str(user.id)

        # Increment version (simple versioning: 1.0 → 1.1 → 1.2)
        current_version = chapter.version
        parts = current_version.split(".")
        minor = int(parts[1]) + 1 if len(parts) > 1 else 1
        chapter.version = f"{parts[0]}.{minor}"

        # Mark as modified
        self.db.commit()
        self.db.refresh(chapter)

        logger.info(f"Section {section_number} edited in chapter {chapter_id}, new version {chapter.version}")

        return chapter

    async def regenerate_section(
        self,
        chapter_id: str,
        section_number: int,
        additional_sources: Optional[List[str]] = None,
        instructions: Optional[str] = None,
        user: User = None
    ) -> Dict[str, Any]:
        """
        Regenerate a single section using AI while preserving the rest

        This method reuses existing research data (stages 3-5) and only
        re-runs stage 6 for the target section, providing 84% cost savings.

        Args:
            chapter_id: Chapter ID
            section_number: Section number to regenerate (0-indexed)
            additional_sources: Optional list of PDF IDs to add as sources
            instructions: Optional special instructions for regeneration
            user: User requesting regeneration

        Returns:
            Dictionary with regeneration results

        Raises:
            HTTPException: If chapter not found or section doesn't exist
        """
        chapter = self.get_chapter(chapter_id)

        # Validate sections exist
        if not chapter.sections or not isinstance(chapter.sections, list):
            raise HTTPException(
                status_code=400,
                detail="Chapter has no sections"
            )

        if section_number < 0 or section_number >= len(chapter.sections):
            raise HTTPException(
                status_code=400,
                detail=f"Section {section_number} does not exist (chapter has {len(chapter.sections)} sections)"
            )

        # Merge additional sources if provided
        if additional_sources:
            existing_sources = chapter.stage_3_internal_research.get("sources", [])
            for pdf_id in additional_sources:
                # Check if source already exists
                if not any(s.get("pdf_id") == pdf_id for s in existing_sources):
                    existing_sources.append({"pdf_id": pdf_id, "manually_added": True})

            chapter.stage_3_internal_research["sources"] = existing_sources

        # Delegate to orchestrator for actual regeneration
        result = await self.orchestrator.regenerate_section(
            chapter=chapter,
            section_number=section_number,
            instructions=instructions
        )

        # Increment version
        current_version = chapter.version
        parts = current_version.split(".")
        minor = int(parts[1]) + 1 if len(parts) > 1 else 1
        chapter.version = f"{parts[0]}.{minor}"

        self.db.commit()
        self.db.refresh(chapter)

        logger.info(f"Section {section_number} regenerated in chapter {chapter_id}, cost: ${result.get('cost_usd', 0):.4f}")

        return {
            "chapter_id": str(chapter.id),
            "section_number": section_number,
            "new_content": result.get("new_content"),
            "version": chapter.version,
            "cost_usd": result.get("cost_usd"),
            "updated_at": chapter.updated_at.isoformat()
        }

    def add_sources(
        self,
        chapter_id: str,
        pdf_ids: Optional[List[str]] = None,
        external_dois: Optional[List[str]] = None,
        pubmed_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add research sources to a chapter for future regenerations

        Args:
            chapter_id: Chapter ID
            pdf_ids: Internal PDF IDs to add
            external_dois: External DOIs to add
            pubmed_ids: PubMed IDs to add

        Returns:
            Dictionary with sources added count

        Raises:
            HTTPException: If chapter not found
        """
        chapter = self.get_chapter(chapter_id)

        sources_added = 0

        # Add internal PDF sources
        if pdf_ids:
            existing_sources = chapter.stage_3_internal_research.get("sources", []) if chapter.stage_3_internal_research else []
            for pdf_id in pdf_ids:
                if not any(s.get("pdf_id") == pdf_id for s in existing_sources):
                    existing_sources.append({
                        "pdf_id": pdf_id,
                        "manually_added": True,
                        "source": "internal"
                    })
                    sources_added += 1

            if not chapter.stage_3_internal_research:
                chapter.stage_3_internal_research = {}
            chapter.stage_3_internal_research["sources"] = existing_sources

        # Add external sources (DOIs and PubMed IDs)
        if external_dois or pubmed_ids:
            existing_external = chapter.stage_4_external_research.get("pubmed_sources", []) if chapter.stage_4_external_research else []

            if external_dois:
                for doi in external_dois:
                    if not any(s.get("doi") == doi for s in existing_external):
                        existing_external.append({
                            "doi": doi,
                            "manually_added": True,
                            "source": "external"
                        })
                        sources_added += 1

            if pubmed_ids:
                for pmid in pubmed_ids:
                    if not any(s.get("pmid") == pmid for s in existing_external):
                        existing_external.append({
                            "pmid": pmid,
                            "manually_added": True,
                            "source": "pubmed"
                        })
                        sources_added += 1

            if not chapter.stage_4_external_research:
                chapter.stage_4_external_research = {}
            chapter.stage_4_external_research["pubmed_sources"] = existing_external

        self.db.commit()

        # Calculate total sources
        total_sources = 0
        if chapter.stage_3_internal_research:
            total_sources += len(chapter.stage_3_internal_research.get("sources", []))
        if chapter.stage_4_external_research:
            total_sources += len(chapter.stage_4_external_research.get("pubmed_sources", []))

        logger.info(f"Added {sources_added} sources to chapter {chapter_id}, total: {total_sources}")

        return {
            "sources_added": sources_added,
            "total_sources": total_sources
        }

    async def run_gap_analysis(
        self,
        chapter_id: str,
        user: User
    ) -> Dict[str, Any]:
        """
        Run Phase 2 Week 5 gap analysis on a completed chapter

        Args:
            chapter_id: Chapter ID
            user: User requesting the analysis

        Returns:
            Dictionary with gap analysis results

        Raises:
            HTTPException: If chapter not found, not completed, or analysis fails
        """
        # Check if gap analysis is enabled
        if not settings.GAP_ANALYSIS_ENABLED:
            raise HTTPException(
                status_code=400,
                detail="Gap analysis feature is not enabled"
            )

        chapter = self.get_chapter(chapter_id)

        # Validate chapter is completed
        if chapter.generation_status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Chapter must be completed before gap analysis (current status: {chapter.generation_status})"
            )

        # Check permissions (must be author or admin)
        if str(chapter.author_id) != str(user.id) and not user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Only the chapter author or admins can run gap analysis"
            )

        logger.info(f"Running gap analysis for chapter {chapter_id} by user {user.email}")

        try:
            # Initialize gap analyzer
            gap_analyzer = GapAnalyzer()

            # Prepare chapter data
            chapter_data = {
                "id": str(chapter.id),
                "title": chapter.title,
                "sections": chapter.sections or [],
                "chapter_type": chapter.chapter_type
            }

            # Get research sources
            internal_sources = []
            if chapter.stage_3_internal_research:
                internal_sources = chapter.stage_3_internal_research.get("sources", [])

            external_sources = []
            if chapter.stage_4_external_research:
                external_sources = chapter.stage_4_external_research.get("pubmed_sources", [])

            # Get Stage 2 context
            stage_2_context = chapter.stage_2_context or {}

            # Run gap analysis
            gap_analysis_result = await gap_analyzer.analyze_chapter_gaps(
                chapter=chapter_data,
                internal_sources=internal_sources,
                external_sources=external_sources,
                stage_2_context=stage_2_context
            )

            # Store results in chapter
            chapter.gap_analysis = gap_analysis_result
            self.db.commit()
            self.db.refresh(chapter)

            logger.info(
                f"Gap analysis complete for chapter {chapter_id}: "
                f"{gap_analysis_result.get('total_gaps', 0)} gaps identified, "
                f"completeness score: {gap_analysis_result.get('overall_completeness_score', 0):.2f}"
            )

            return {
                "success": True,
                "chapter_id": str(chapter.id),
                "gap_analysis": {
                    "total_gaps": gap_analysis_result.get("total_gaps", 0),
                    "critical_gaps": gap_analysis_result.get("severity_distribution", {}).get("critical", 0),
                    "completeness_score": gap_analysis_result.get("overall_completeness_score", 0.0),
                    "requires_revision": gap_analysis_result.get("requires_revision", False),
                    "analyzed_at": gap_analysis_result.get("analyzed_at")
                }
            }

        except Exception as e:
            logger.error(f"Gap analysis failed for chapter {chapter_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Gap analysis failed: {str(e)}"
            )

    def get_gap_analysis(self, chapter_id: str) -> Dict[str, Any]:
        """
        Get full gap analysis results for a chapter

        Args:
            chapter_id: Chapter ID

        Returns:
            Full gap analysis results

        Raises:
            HTTPException: If chapter not found or no gap analysis exists
        """
        chapter = self.get_chapter(chapter_id)

        if not chapter.gap_analysis:
            raise HTTPException(
                status_code=404,
                detail="No gap analysis found for this chapter. Run POST /chapters/{id}/gap-analysis first."
            )

        return chapter.gap_analysis

    def get_gap_analysis_summary(self, chapter_id: str) -> Dict[str, Any]:
        """
        Get concise gap analysis summary for a chapter

        Args:
            chapter_id: Chapter ID

        Returns:
            Simplified gap analysis summary

        Raises:
            HTTPException: If chapter not found or no gap analysis exists
        """
        chapter = self.get_chapter(chapter_id)

        if not chapter.gap_analysis:
            raise HTTPException(
                status_code=404,
                detail="No gap analysis found for this chapter. Run POST /chapters/{id}/gap-analysis first."
            )

        gap_data = chapter.gap_analysis

        # Build concise summary
        summary = {
            "chapter_id": str(chapter.id),
            "chapter_title": chapter.title,
            "analyzed_at": gap_data.get("analyzed_at"),
            "total_gaps": gap_data.get("total_gaps", 0),
            "severity_distribution": gap_data.get("severity_distribution", {}),
            "completeness_score": gap_data.get("overall_completeness_score", 0.0),
            "requires_revision": gap_data.get("requires_revision", False),
            "top_recommendations": gap_data.get("recommendations", [])[:3],  # Top 3 only
            "gap_categories_summary": {}
        }

        # Add category summaries (counts only)
        gap_categories = gap_data.get("gap_categories", {})
        for category, gaps in gap_categories.items():
            summary["gap_categories_summary"][category] = len(gaps) if isinstance(gaps, list) else 0

        return summary
