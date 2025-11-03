"""
Chapter API routes for generation and management
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db, User
from backend.services.chapter_service import ChapterService
from backend.services.export import PDFExporter, DOCXExporter, BibTeXExporter
from backend.services.cost_estimator import CostEstimator
from backend.utils import get_logger, get_current_active_user

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/chapters", tags=["chapters"])


# ==================== Request/Response Models ====================

class ChapterCreateRequest(BaseModel):
    """Request model for chapter creation"""
    topic: str = Field(..., min_length=3, description="Chapter topic or query")
    chapter_type: Optional[str] = Field(None, description="Chapter type (surgical_disease, pure_anatomy, surgical_technique)")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Management of traumatic brain injury",
                "chapter_type": "surgical_disease"
            }
        }


class ChapterResponse(BaseModel):
    """Response model for chapter information"""
    id: str
    title: str
    chapter_type: Optional[str] = None
    generation_status: str
    author_id: str
    version: Optional[str] = None
    is_current_version: bool
    depth_score: Optional[float] = None
    coverage_score: Optional[float] = None
    evidence_score: Optional[float] = None
    currency_score: Optional[float] = None
    total_sections: Optional[int] = None
    total_words: Optional[int] = None
    generation_cost_usd: Optional[float] = None
    created_at: str
    updated_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Management of traumatic brain injury",
                "chapter_type": "surgical_disease",
                "generation_status": "completed",
                "author_id": "user-123",
                "version": "1.0",
                "is_current_version": True,
                "depth_score": 0.85,
                "coverage_score": 0.90,
                "evidence_score": 0.88,
                "currency_score": 0.75,
                "total_sections": 7,
                "total_words": 2500,
                "generation_cost_usd": 0.45,
                "created_at": "2025-10-27T12:00:00",
                "updated_at": "2025-10-27T12:10:00"
            }
        }


class ChapterDetailResponse(ChapterResponse):
    """Detailed response model including sections"""
    sections: Optional[List[dict]] = None
    references: Optional[List[dict]] = None
    structure_metadata: Optional[dict] = None


class ChapterStatisticsResponse(BaseModel):
    """Response model for chapter statistics"""
    total_chapters: int
    completed: int
    failed: int
    in_progress: int
    average_depth_score: float
    completion_rate: float


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    details: Optional[dict] = None


class SectionEditRequest(BaseModel):
    """Request model for editing a section"""
    content: str = Field(..., min_length=10, description="Updated section content (HTML)")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "<h2>Updated Section</h2><p>New content here...</p>"
            }
        }


class SectionRegenerateRequest(BaseModel):
    """Request model for regenerating a section"""
    additional_sources: Optional[List[str]] = Field(None, description="Additional PDF IDs to use as sources")
    instructions: Optional[str] = Field(None, description="Special instructions for regeneration")

    class Config:
        json_schema_extra = {
            "example": {
                "additional_sources": ["123e4567-e89b-12d3-a456-426614174000"],
                "instructions": "Focus more on surgical technique and less on pathophysiology"
            }
        }


class SectionResponse(BaseModel):
    """Response model for section operations"""
    chapter_id: str
    section_number: int
    updated_content: Optional[str] = None
    regeneration_status: Optional[str] = None
    version: str
    cost_usd: Optional[float] = None
    updated_at: str


class AddSourcesRequest(BaseModel):
    """Request model for adding research sources"""
    pdf_ids: Optional[List[str]] = Field(None, description="Internal PDF IDs")
    external_dois: Optional[List[str]] = Field(None, description="External DOIs")
    pubmed_ids: Optional[List[str]] = Field(None, description="PubMed IDs")

    class Config:
        json_schema_extra = {
            "example": {
                "pdf_ids": ["123e4567-e89b-12d3-a456-426614174000"],
                "external_dois": ["10.1234/example"],
                "pubmed_ids": ["12345678"]
            }
        }


class AddSourcesResponse(BaseModel):
    """Response model for adding sources"""
    chapter_id: str
    sources_added: int
    total_sources: int


class GapAnalysisResponse(BaseModel):
    """Response model for gap analysis trigger"""
    success: bool
    chapter_id: str
    gap_analysis: dict

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "chapter_id": "123e4567-e89b-12d3-a456-426614174000",
                "gap_analysis": {
                    "total_gaps": 5,
                    "critical_gaps": 1,
                    "completeness_score": 0.82,
                    "requires_revision": False,
                    "analyzed_at": "2025-10-29T10:00:00Z"
                }
            }
        }


class GapAnalysisSummaryResponse(BaseModel):
    """Response model for gap analysis summary"""
    chapter_id: str
    chapter_title: str
    analyzed_at: Optional[str] = None
    total_gaps: int
    severity_distribution: dict
    completeness_score: float
    requires_revision: bool
    top_recommendations: List[dict]
    gap_categories_summary: dict

    class Config:
        json_schema_extra = {
            "example": {
                "chapter_id": "123e4567-e89b-12d3-a456-426614174000",
                "chapter_title": "Glioblastoma Management",
                "analyzed_at": "2025-10-29T10:00:00Z",
                "total_gaps": 8,
                "severity_distribution": {
                    "critical": 1,
                    "high": 2,
                    "medium": 3,
                    "low": 2
                },
                "completeness_score": 0.82,
                "requires_revision": False,
                "top_recommendations": [
                    {
                        "priority": 1,
                        "action": "address_critical_gaps",
                        "description": "Add missing complications section"
                    }
                ],
                "gap_categories_summary": {
                    "content_completeness": 2,
                    "source_coverage": 3,
                    "section_balance": 1,
                    "temporal_coverage": 1,
                    "critical_information": 1
                }
            }
        }


class CostEstimateRequest(BaseModel):
    """Request model for cost estimation"""
    topic: str = Field(..., min_length=3, description="Chapter topic for cost estimation")
    chapter_type: Optional[str] = Field(None, description="Chapter type (surgical_disease, pure_anatomy, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Management of traumatic brain injury",
                "chapter_type": "surgical_disease"
            }
        }


class CostEstimateResponse(BaseModel):
    """Response model for cost estimation"""
    estimated_cost_usd: float
    estimated_cost_base_usd: float
    buffer_percentage: int
    breakdown_by_stage: dict
    breakdown_by_category: dict
    estimated_duration_seconds: int
    estimated_duration_minutes: float
    chapter_type: str
    complexity_multiplier: float
    expected_sections: int
    topic: str
    estimated_at: str
    notes: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "estimated_cost_usd": 0.55,
                "estimated_cost_base_usd": 0.50,
                "buffer_percentage": 10,
                "breakdown_by_stage": {
                    "analysis": 0.02,
                    "research": 0.08,
                    "content_generation": 0.28,
                    "quality_assurance": 0.12
                },
                "breakdown_by_category": {
                    "analysis_research": 0.10,
                    "content_generation": 0.28,
                    "quality_enhancement": 0.12,
                    "finalization": 0.05
                },
                "estimated_duration_seconds": 150,
                "estimated_duration_minutes": 2.5,
                "chapter_type": "surgical_disease",
                "complexity_multiplier": 1.0,
                "expected_sections": 7,
                "topic": "Management of traumatic brain injury",
                "estimated_at": "2025-10-31T12:00:00",
                "notes": [
                    "Estimate includes 10% buffer for variability",
                    "Actual cost may vary based on available research sources"
                ]
            }
        }


# ==================== Health Check (must be before dynamic routes) ====================

@router.get(
    "/health",
    response_model=MessageResponse,
    summary="Chapter service health check"
)
async def chapter_health_check() -> MessageResponse:
    """
    Health check endpoint for chapter service

    No authentication required.
    """
    return MessageResponse(message="Chapter service is healthy")


# ==================== Chapter Routes ====================

@router.post(
    "/estimate-cost",
    response_model=CostEstimateResponse,
    summary="Estimate chapter generation cost",
    description="""
    Estimate the cost and duration of generating a chapter before creating it.

    This endpoint provides:
    - Total estimated cost in USD (with 10% buffer)
    - Breakdown by stage (analysis, research, generation, etc.)
    - Breakdown by category (analysis_research, content_generation, etc.)
    - Estimated duration in seconds and minutes
    - Expected number of sections based on chapter type
    - Complexity multiplier for the chapter type

    The estimate considers:
    - Chapter type complexity (surgical_disease, pure_anatomy, surgical_technique, etc.)
    - Expected number of sections
    - GPT-4o API pricing ($0.005/1K input, $0.015/1K output tokens)
    - Embedding costs ($0.00013/1K tokens)
    - PubMed research (free)

    Typical costs:
    - Simple anatomy chapter: $0.25 - $0.35
    - Standard disease chapter: $0.45 - $0.65
    - Complex review chapter: $0.75 - $1.00
    - Surgical technique: $0.55 - $0.80

    Note: Actual costs may vary by ±20% based on:
    - Available research sources
    - Topic complexity
    - Quality assurance depth
    - Fact-checking requirements
    """
)
async def estimate_chapter_cost(
    request: CostEstimateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> CostEstimateResponse:
    """
    Estimate cost for chapter generation

    Requires authentication.
    """
    cost_estimator = CostEstimator()

    estimate = cost_estimator.estimate_cost(
        topic=request.topic,
        chapter_type=request.chapter_type
    )

    logger.info(f"Cost estimated by user {current_user.email}: ${estimate['estimated_cost_usd']:.4f} for '{request.topic}'")

    return CostEstimateResponse(**estimate)


@router.post(
    "",
    response_model=ChapterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new chapter",
    description="""
    Generate a new neurosurgery chapter using the 14-stage workflow.

    The generation process includes:
    1. Topic validation and analysis
    2. Context building
    3. Internal research (indexed PDFs)
    4. External research (PubMed)
    5. Content synthesis planning
    6. Section generation with AI
    7. Image integration
    8. Citation network building
    9. Quality assurance
    10. Fact-checking
    11. Formatting
    12. Review and refinement
    13. Finalization
    14. Delivery

    This is an async operation that may take several minutes.
    """
)
async def create_chapter(
    request: ChapterCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ChapterResponse:
    """
    Generate new chapter

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    try:
        chapter = await chapter_service.create_chapter(
            topic=request.topic,
            user=current_user,
            chapter_type=request.chapter_type
        )

        logger.info(f"Chapter generated by user {current_user.email}: {chapter.id}")

        return ChapterResponse(**chapter.to_dict())

    except Exception as e:
        logger.error(f"Chapter creation failed: {str(e)}", exc_info=True)
        raise


@router.get(
    "",
    response_model=List[ChapterResponse],
    summary="List chapters",
    description="List all chapters with optional filtering by type and status"
)
async def list_chapters(
    chapter_type: Optional[str] = Query(None, description="Filter by chapter type"),
    status: Optional[str] = Query(None, description="Filter by generation status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[ChapterResponse]:
    """
    List chapters with filtering

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    chapters = chapter_service.list_chapters(
        user_id=None,  # Show all chapters (could filter by user)
        chapter_type=chapter_type,
        status=status,
        skip=skip,
        limit=limit
    )

    return [ChapterResponse(**chapter.to_dict()) for chapter in chapters]


@router.get(
    "/mine",
    response_model=List[ChapterResponse],
    summary="Get my chapters",
    description="Get all chapters created by the current user"
)
async def get_my_chapters(
    include_draft: bool = Query(True, description="Include chapters in progress"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[ChapterResponse]:
    """
    Get current user's chapters

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    chapters = chapter_service.get_user_chapters(
        user_id=str(current_user.id),
        include_draft=include_draft
    )

    return [ChapterResponse(**chapter.to_dict()) for chapter in chapters]


@router.get(
    "/statistics",
    response_model=ChapterStatisticsResponse,
    summary="Get chapter statistics",
    description="Get overall chapter generation statistics"
)
async def get_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ChapterStatisticsResponse:
    """
    Get chapter statistics

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    stats = chapter_service.get_chapter_statistics()

    return ChapterStatisticsResponse(**stats)


@router.get(
    "/search",
    response_model=List[ChapterResponse],
    summary="Search chapters",
    description="Search chapters by title or content"
)
async def search_chapters(
    q: str = Query(..., min_length=2, description="Search query"),
    max_results: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[ChapterResponse]:
    """
    Search chapters

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    chapters = chapter_service.search_chapters(
        query=q,
        max_results=max_results
    )

    return [ChapterResponse(**chapter.to_dict()) for chapter in chapters]


@router.get(
    "/{chapter_id}",
    response_model=ChapterDetailResponse,
    summary="Get chapter details",
    description="Get detailed information about a specific chapter including sections and references"
)
async def get_chapter(
    chapter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ChapterDetailResponse:
    """
    Get chapter by ID

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    chapter = chapter_service.get_chapter(chapter_id)

    return ChapterDetailResponse(**chapter.to_dict())


@router.get(
    "/{chapter_id}/versions",
    response_model=List[ChapterResponse],
    summary="Get chapter versions",
    description="Get all versions of a chapter"
)
async def get_chapter_versions(
    chapter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[ChapterResponse]:
    """
    Get all versions of a chapter

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    versions = chapter_service.get_chapter_versions(chapter_id)

    return [ChapterResponse(**v.to_dict()) for v in versions]


@router.get(
    "/{chapter_id}/export",
    summary="Export chapter as markdown",
    description="Export chapter in markdown format for download"
)
async def export_chapter(
    chapter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Export chapter as markdown

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    markdown = chapter_service.export_chapter_markdown(chapter_id)

    return {
        "chapter_id": chapter_id,
        "format": "markdown",
        "content": markdown
    }


@router.get(
    "/{chapter_id}/export/pdf",
    summary="Export chapter as PDF",
    description="""
    Export chapter as a professional PDF document.

    Templates available:
    - academic: Standard academic paper format with abstract, quality metrics, and bibliography
    - journal: Medical journal submission format (two-column, Vancouver citations)
    - hospital: Hospital letterhead format with clinical summary and quality assurance metrics

    The PDF export uses WeasyPrint by default (no LaTeX installation required).
    For LaTeX-based export (requires pdflatex), set use_latex=true.

    The generated PDF includes:
    - Title page with metadata
    - Quality and confidence metrics
    - All chapter sections with formatting
    - Bibliography/references
    - Professional styling appropriate for the template
    """
)
async def export_chapter_pdf(
    chapter_id: str,
    template: str = Query("academic", description="Template: academic, journal, or hospital"),
    include_images: bool = Query(True, description="Include images in the PDF"),
    use_latex: bool = Query(False, description="Use LaTeX compilation (requires pdflatex installed)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Response:
    """
    Export chapter as PDF

    Requires authentication.

    Returns PDF file with appropriate headers for download.
    """
    chapter_service = ChapterService(db)

    # Get chapter
    chapter = chapter_service.get_chapter(chapter_id)

    # Generate PDF
    pdf_exporter = PDFExporter()

    try:
        pdf_bytes = pdf_exporter.export_chapter_to_pdf(
            chapter=chapter,
            template=template,
            include_images=include_images,
            use_latex=use_latex
        )

        # Sanitize filename
        safe_title = "".join(c for c in chapter.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # Limit length
        filename = f"{safe_title}_v{chapter.version or '1.0'}.pdf"

        logger.info(f"PDF exported for chapter {chapter_id} by user {current_user.email} (template={template})")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )
    except Exception as e:
        logger.error(f"PDF export failed for chapter {chapter_id}: {str(e)}", exc_info=True)
        raise


@router.get(
    "/{chapter_id}/export/docx",
    summary="Export chapter as DOCX",
    description="""
    Export chapter as a Microsoft Word document (.docx).

    The DOCX export includes:
    - Professional title page with metadata (version, date, chapter type)
    - Quality and confidence metrics section (if requested)
    - All chapter sections with preserved formatting (headings, bold, italic, lists)
    - References section with all citations
    - Editable in Microsoft Word or compatible software

    The document uses professional styling:
    - Arial font for headings
    - Times New Roman for body text
    - Color-coded headings (dark blue)
    - Proper spacing and indentation
    - Structured tables for metrics

    This format is ideal for:
    - Further editing and customization
    - Collaboration and review
    - Integration into larger documents
    - Submission to journals or institutions
    """
)
async def export_chapter_docx(
    chapter_id: str,
    include_images: bool = Query(True, description="Include images in the document"),
    include_quality_metrics: bool = Query(True, description="Include quality and confidence metrics"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Response:
    """
    Export chapter as DOCX

    Requires authentication.

    Returns DOCX file with appropriate headers for download.
    """
    chapter_service = ChapterService(db)

    # Get chapter
    chapter = chapter_service.get_chapter(chapter_id)

    # Generate DOCX
    docx_exporter = DOCXExporter()

    try:
        docx_bytes = docx_exporter.export_chapter_to_docx(
            chapter=chapter,
            include_images=include_images,
            include_quality_metrics=include_quality_metrics
        )

        # Sanitize filename
        safe_title = "".join(c for c in chapter.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # Limit length
        filename = f"{safe_title}_v{chapter.version or '1.0'}.docx"

        logger.info(f"DOCX exported for chapter {chapter_id} by user {current_user.email}")

        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )
    except Exception as e:
        logger.error(f"DOCX export failed for chapter {chapter_id}: {str(e)}", exc_info=True)
        raise


@router.get(
    "/{chapter_id}/export/bibtex",
    summary="Export citations as BibTeX",
    description="""
    Export chapter citations in BibTeX format for reference managers.

    BibTeX is a widely-used reference format supported by:
    - LaTeX document preparation system
    - Reference managers (Zotero, Mendeley, EndNote, etc.)
    - Academic writing tools
    - Citation management software

    The export includes:
    - All chapter citations converted to proper BibTeX entries
    - Automatic entry type detection (article, book, inbook, etc.)
    - Unique citation keys (Author_Year_Index)
    - Properly formatted author names
    - All available metadata (DOI, PMID, URL, volume, pages, etc.)
    - Header comments with chapter information

    Citation styles (currently affects metadata completeness):
    - apa: American Psychological Association
    - vancouver: Vancouver/NLM style (medical journals)
    - chicago: Chicago Manual of Style

    The .bib file can be directly imported into:
    - LaTeX documents via \\bibliography{} command
    - Reference management software
    - Academic writing platforms

    Additional format available:
    - RIS format can be exported via format=ris query parameter
    """
)
async def export_chapter_bibtex(
    chapter_id: str,
    style: str = Query("apa", description="Citation style: apa, vancouver, or chicago"),
    format: str = Query("bibtex", description="Export format: bibtex or ris"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Response:
    """
    Export chapter citations as BibTeX

    Requires authentication.

    Returns .bib file (or .ris if format=ris) with appropriate headers for download.
    """
    chapter_service = ChapterService(db)

    # Get chapter
    chapter = chapter_service.get_chapter(chapter_id)

    # Generate BibTeX
    bibtex_exporter = BibTeXExporter()

    try:
        if format.lower() == "ris":
            content = bibtex_exporter.export_as_ris(chapter)
            media_type = "application/x-research-info-systems"
            extension = "ris"
        else:
            content = bibtex_exporter.export_chapter_citations(
                chapter=chapter,
                style=style
            )
            media_type = "application/x-bibtex"
            extension = "bib"

        # Sanitize filename
        safe_title = "".join(c for c in chapter.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # Limit length
        filename = f"{safe_title}_references.{extension}"

        logger.info(f"BibTeX exported for chapter {chapter_id} by user {current_user.email} (style={style}, format={format})")

        return Response(
            content=content.encode('utf-8'),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )
    except Exception as e:
        logger.error(f"BibTeX export failed for chapter {chapter_id}: {str(e)}", exc_info=True)
        raise


@router.post(
    "/{chapter_id}/regenerate",
    response_model=ChapterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Regenerate chapter",
    description="Create a new version of an existing chapter with updated research"
)
async def regenerate_chapter(
    chapter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ChapterResponse:
    """
    Regenerate chapter (create new version)

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    new_chapter = await chapter_service.regenerate_chapter(
        chapter_id=chapter_id,
        user=current_user
    )

    logger.info(f"Chapter regenerated by user {current_user.email}: {new_chapter.id}")

    return ChapterResponse(**new_chapter.to_dict())


@router.patch(
    "/{chapter_id}/sections/{section_number}",
    response_model=SectionResponse,
    summary="Edit section content",
    description="""
    Edit a specific section's content without regenerating the entire chapter.

    This creates a new version automatically for version control.
    Cost savings: ~84% compared to full regeneration ($0.08 vs $0.50)
    """
)
async def edit_section(
    chapter_id: str,
    section_number: int,
    request: SectionEditRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> SectionResponse:
    """
    Edit section content

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    chapter = chapter_service.edit_section(
        chapter_id=chapter_id,
        section_number=section_number,
        new_content=request.content,
        user=current_user
    )

    logger.info(f"Section {section_number} edited in chapter {chapter_id} by user {current_user.email}")

    return SectionResponse(
        chapter_id=str(chapter.id),
        section_number=section_number,
        updated_content=request.content,
        version=chapter.version,
        updated_at=chapter.updated_at.isoformat()
    )


@router.post(
    "/{chapter_id}/sections/{section_number}/regenerate",
    response_model=SectionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Regenerate single section",
    description="""
    Regenerate a specific section using AI while preserving the rest of the chapter.

    This operation:
    - Reuses existing research data (stages 3-5)
    - Only re-runs stage 6 for the target section
    - Creates a new version automatically
    - Cost: ~$0.08 (84% savings vs full regeneration)
    - Time: ~10-20 seconds

    Returns 202 Accepted and emits WebSocket event when complete.
    """
)
async def regenerate_section(
    chapter_id: str,
    section_number: int,
    request: SectionRegenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> SectionResponse:
    """
    Regenerate single section with AI

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    result = await chapter_service.regenerate_section(
        chapter_id=chapter_id,
        section_number=section_number,
        additional_sources=request.additional_sources,
        instructions=request.instructions,
        user=current_user
    )

    logger.info(f"Section {section_number} regenerated in chapter {chapter_id} by user {current_user.email}")

    return SectionResponse(
        chapter_id=str(result["chapter_id"]),
        section_number=section_number,
        regeneration_status="completed",
        updated_content=result.get("new_content"),
        version=result["version"],
        cost_usd=result.get("cost_usd"),
        updated_at=result["updated_at"]
    )


@router.post(
    "/{chapter_id}/sources",
    response_model=AddSourcesResponse,
    summary="Add research sources to chapter",
    description="""
    Add additional research sources to a chapter for future regenerations.

    Sources can be:
    - Internal PDFs from your library (by PDF ID)
    - External papers (by DOI)
    - PubMed articles (by PMID)

    These sources will be available when regenerating sections or the entire chapter.
    """
)
async def add_sources(
    chapter_id: str,
    request: AddSourcesRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> AddSourcesResponse:
    """
    Add research sources to chapter

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    result = chapter_service.add_sources(
        chapter_id=chapter_id,
        pdf_ids=request.pdf_ids,
        external_dois=request.external_dois,
        pubmed_ids=request.pubmed_ids
    )

    logger.info(f"Added {result['sources_added']} sources to chapter {chapter_id} by user {current_user.email}")

    return AddSourcesResponse(
        chapter_id=chapter_id,
        sources_added=result["sources_added"],
        total_sources=result["total_sources"]
    )


@router.post(
    "/{chapter_id}/gap-analysis",
    response_model=GapAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run gap analysis on chapter",
    description="""
    Run comprehensive Phase 2 Week 5 gap analysis on a completed chapter.

    This operation:
    - Analyzes content completeness against Stage 2 context
    - Identifies unused high-value research sources
    - Detects section balance issues
    - Checks temporal coverage (recent literature)
    - Uses AI to identify missing critical information
    - Generates actionable recommendations
    - Calculates overall completeness score (0-1)

    Results are stored in the chapter for future retrieval.

    Only the chapter author or admins can run gap analysis.
    Chapter must be in 'completed' status.

    Cost: ~$0.03-0.05 per analysis
    Time: ~2-10 seconds depending on chapter size
    """
)
async def run_gap_analysis(
    chapter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> GapAnalysisResponse:
    """
    Trigger gap analysis for a chapter

    Requires authentication (author or admin).
    """
    chapter_service = ChapterService(db)

    result = await chapter_service.run_gap_analysis(
        chapter_id=chapter_id,
        user=current_user
    )

    logger.info(
        f"Gap analysis triggered for chapter {chapter_id} by user {current_user.email}: "
        f"{result['gap_analysis']['total_gaps']} gaps found"
    )

    return GapAnalysisResponse(**result)


@router.get(
    "/{chapter_id}/gap-analysis",
    response_model=dict,
    summary="Get full gap analysis results",
    description="""
    Retrieve the complete gap analysis results for a chapter.

    Returns all identified gaps across 5 dimensions:
    - Content completeness
    - Source coverage
    - Section balance
    - Temporal coverage
    - Critical information

    Includes detailed recommendations and severity distribution.

    Returns 404 if no gap analysis has been run for this chapter.
    """
)
async def get_gap_analysis(
    chapter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get full gap analysis results

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    gap_analysis = chapter_service.get_gap_analysis(chapter_id)

    return gap_analysis


@router.get(
    "/{chapter_id}/gap-analysis/summary",
    response_model=GapAnalysisSummaryResponse,
    summary="Get gap analysis summary",
    description="""
    Retrieve a concise summary of the gap analysis results.

    Returns:
    - Total gaps and severity distribution
    - Completeness score
    - Whether revision is required
    - Top 3 recommendations
    - Gap counts by category

    This endpoint is optimized for UI display and provides a simplified view
    of the full gap analysis results.

    Returns 404 if no gap analysis has been run for this chapter.
    """
)
async def get_gap_analysis_summary(
    chapter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> GapAnalysisSummaryResponse:
    """
    Get concise gap analysis summary

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    summary = chapter_service.get_gap_analysis_summary(chapter_id)

    return GapAnalysisSummaryResponse(**summary)


@router.delete(
    "/{chapter_id}",
    response_model=MessageResponse,
    summary="Delete chapter",
    description="Delete a chapter and all its data"
)
async def delete_chapter(
    chapter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Delete chapter

    Requires authentication.
    """
    chapter_service = ChapterService(db)

    result = chapter_service.delete_chapter(chapter_id)

    logger.info(f"Chapter deleted by user {current_user.email}: {chapter_id}")

    return MessageResponse(
        message=f"Chapter deleted successfully",
        details=result
    )
