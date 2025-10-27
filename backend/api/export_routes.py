"""
Export API Routes
Endpoints for chapter export, templates, and citation styles
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field
import io

from backend.database.connection import get_db
from backend.database.models import User, ExportTemplate, CitationStyle
from backend.services.export_service import ExportService
from backend.services.citation_service import CitationService
from backend.services.bibliography_service import BibliographyService
from backend.utils.dependencies import get_current_user
from backend.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class ExportRequest(BaseModel):
    """Export chapter request"""
    chapter_id: str = Field(..., description="Chapter ID to export")
    format: str = Field(..., description="Export format: pdf, docx, html")
    template_id: Optional[str] = Field(None, description="Template ID (optional)")
    citation_style: str = Field(default="apa", description="Citation style")
    options: Optional[dict] = Field(default={}, description="Additional options")


# ==================== Export Endpoints ====================

@router.post("/export")
async def export_chapter(
    request: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export a chapter to specified format

    Supports PDF, DOCX, and HTML formats with custom templates and citation styles
    """
    try:
        export_service = ExportService(db)

        result = export_service.export_chapter(
            chapter_id=request.chapter_id,
            user_id=str(current_user.id),
            export_format=request.format,
            template_id=request.template_id,
            citation_style=request.citation_style,
            options=request.options
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Export failed"))

        # Return file as download
        content = result.get("content")
        file_name = result.get("file_name")

        # Determine content type
        content_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "html": "text/html"
        }
        content_type = content_types.get(request.format, "application/octet-stream")

        # Handle both bytes and string content
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content

        return StreamingResponse(
            io.BytesIO(content_bytes),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_name}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/preview/{chapter_id}")
async def preview_export(
    chapter_id: str,
    format: str = "html",
    template_id: Optional[str] = None,
    citation_style: str = "apa",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Preview export without downloading

    Returns HTML preview of the export
    """
    try:
        export_service = ExportService(db)

        result = export_service.export_chapter(
            chapter_id=chapter_id,
            user_id=str(current_user.id),
            export_format="html",  # Always preview as HTML
            template_id=template_id,
            citation_style=citation_style,
            options={"preview": True}
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))

        return Response(
            content=result.get("content"),
            media_type="text/html"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


# ==================== Template Endpoints ====================

@router.get("/templates")
async def get_export_templates(
    format: Optional[str] = None,
    public_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get available export templates

    Can filter by format and visibility
    """
    try:
        query = db.query(ExportTemplate)

        if format:
            query = query.filter(ExportTemplate.format == format)

        if public_only:
            query = query.filter(ExportTemplate.is_public == True)
        else:
            # Include user's private templates
            query = query.filter(
                (ExportTemplate.is_public == True) |
                (ExportTemplate.created_by == current_user.id)
            )

        templates = query.all()

        return {
            "templates": [t.to_dict() for t in templates],
            "count": len(templates)
        }

    except Exception as e:
        logger.error(f"Failed to get templates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific template"""
    try:
        template = db.query(ExportTemplate).filter(
            ExportTemplate.id == template_id
        ).first()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Check access
        if not template.is_public and template.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to private template")

        return template.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")


# ==================== Citation Style Endpoints ====================

@router.get("/citation-styles")
async def get_citation_styles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get available citation styles

    Returns all active citation styles (APA, MLA, Chicago, Vancouver, etc.)
    """
    try:
        citation_service = CitationService(db)
        styles = citation_service.get_all_citation_styles()

        return {
            "styles": styles,
            "count": len(styles)
        }

    except Exception as e:
        logger.error(f"Failed to get citation styles: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get citation styles: {str(e)}")


@router.get("/citation-styles/{style_name}")
async def get_citation_style(
    style_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific citation style"""
    try:
        citation_service = CitationService(db)
        style = citation_service.get_citation_style(style_name)

        if not style:
            raise HTTPException(status_code=404, detail=f"Citation style '{style_name}' not found")

        return style.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get citation style: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get citation style: {str(e)}")


# ==================== Bibliography Endpoints ====================

@router.get("/chapters/{chapter_id}/bibliography")
async def get_chapter_bibliography(
    chapter_id: str,
    citation_style: str = "apa",
    sort_by: str = "author",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get formatted bibliography for a chapter

    Returns bibliography without exporting the full chapter
    """
    try:
        from backend.database.models import Chapter

        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        bibliography_service = BibliographyService(db)

        result = bibliography_service.generate_bibliography(
            chapter=chapter,
            style_name=citation_style,
            sort_by=sort_by,
            include_in_text_markers=True
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get bibliography: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get bibliography: {str(e)}")


@router.get("/chapters/{chapter_id}/citations/summary")
async def get_citations_summary(
    chapter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get citation summary and statistics for a chapter

    Returns counts, year ranges, journals, etc.
    """
    try:
        from backend.database.models import Chapter

        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        bibliography_service = BibliographyService(db)

        summary = bibliography_service.generate_citation_summary(chapter)

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get citation summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get citation summary: {str(e)}")


# ==================== Export History Endpoints ====================

@router.get("/export/history")
async def get_export_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's export history

    Returns list of previous exports
    """
    try:
        from backend.database.models import ExportHistory
        from sqlalchemy import desc

        exports = db.query(ExportHistory).filter(
            ExportHistory.user_id == current_user.id
        ).order_by(desc(ExportHistory.created_at)).limit(limit).offset(offset).all()

        return {
            "exports": [e.to_dict() for e in exports],
            "count": len(exports)
        }

    except Exception as e:
        logger.error(f"Failed to get export history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get export history: {str(e)}")


# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """Export service health check"""
    return {
        "status": "healthy",
        "service": "export",
        "features": [
            "pdf_export",
            "docx_export",
            "html_export",
            "citation_management",
            "bibliography_generation",
            "custom_templates"
        ]
    }
