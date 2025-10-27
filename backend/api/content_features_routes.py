"""
Content Features API Routes for Phase 18: Advanced Content Features
Comprehensive REST API for templates, bookmarks, annotations, filters, and scheduling
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.database import get_db
from backend.api.auth_routes import get_current_user
from backend.services.content_template_service import ContentTemplateService
from backend.services.bookmark_service import BookmarkService
from backend.services.annotation_service import AnnotationService
from backend.services.advanced_filter_service import AdvancedFilterService
from backend.services.content_scheduling_service import ContentSchedulingService
from backend.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==================== Pydantic Models ====================

# Template Models
class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    template_type: str = Field(..., description="surgical_disease, anatomy, technique, case_study, custom")
    structure: Dict[str, Any]
    description: Optional[str] = None
    is_public: bool = False


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    structure: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None


# Bookmark Models
class BookmarkCreate(BaseModel):
    content_type: str
    content_id: str
    collection_id: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    is_favorite: bool = False


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_public: bool = False
    parent_collection_id: Optional[str] = None


class CollectionShare(BaseModel):
    shared_with_user_id: Optional[str] = None
    shared_with_email: Optional[str] = None
    permission_level: str = Field(default="view", description="view, edit, admin")


# Annotation Models
class HighlightCreate(BaseModel):
    content_type: str
    content_id: str
    highlight_text: str
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    position_data: Optional[Dict] = None
    color: str = "yellow"


class AnnotationCreate(BaseModel):
    content_type: str
    content_id: str
    annotation_text: str
    annotation_type: str = Field(default="note", description="note, question, correction, comment")
    position_data: Optional[Dict] = None
    highlight_id: Optional[str] = None
    is_private: bool = True


class AnnotationUpdate(BaseModel):
    annotation_text: Optional[str] = None
    is_private: Optional[bool] = None


class ReplyCreate(BaseModel):
    reply_text: str = Field(..., min_length=1)


class ReactionCreate(BaseModel):
    reaction_type: str = Field(..., description="like, agree, disagree, question")


# Filter Models
class FilterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    filter_config: Dict[str, Any]
    description: Optional[str] = None
    is_favorite: bool = False
    is_shared: bool = False


class FilterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    filter_config: Optional[Dict[str, Any]] = None
    is_favorite: Optional[bool] = None
    is_shared: Optional[bool] = None


class FilterApply(BaseModel):
    filter_config: Dict[str, Any]
    base_table: str = Field(default="chapters", description="chapters, pdfs")
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# Schedule Models
class ScheduleCreate(BaseModel):
    content_type: str
    content_id: str
    publish_at: datetime
    unpublish_at: Optional[datetime] = None
    timezone: str = "UTC"
    notification_enabled: bool = True


class RecurringScheduleCreate(BaseModel):
    content_type: str
    schedule_name: str
    recurrence_pattern: str = Field(..., description="daily, weekly, monthly, custom")
    start_date: datetime
    end_date: Optional[datetime] = None
    recurrence_config: Optional[Dict[str, Any]] = None
    timezone: str = "UTC"


class RecurringScheduleUpdate(BaseModel):
    schedule_name: Optional[str] = None
    is_active: Optional[bool] = None
    end_date: Optional[datetime] = None


# ==================== Content Template Routes ====================

@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_template(
    template: TemplateCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Create new content template"""
    service = ContentTemplateService(db)

    result = service.create_template(
        user_id=current_user['id'],
        name=template.name,
        template_type=template.template_type,
        structure=template.structure,
        description=template.description,
        is_public=template.is_public
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create template"
        )

    return {"success": True, "template": result}


@router.get("/templates")
async def list_templates(
    template_type: Optional[str] = None,
    include_public: bool = True,
    include_system: bool = True,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """List available templates"""
    service = ContentTemplateService(db)

    templates = service.list_templates(
        user_id=current_user['id'],
        template_type=template_type,
        include_public=include_public,
        include_system=include_system
    )

    return {"success": True, "templates": templates, "count": len(templates)}


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get template by ID"""
    service = ContentTemplateService(db)

    template = service.get_template(template_id, current_user['id'])

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return {"success": True, "template": template}


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    updates: TemplateUpdate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Update template"""
    service = ContentTemplateService(db)

    success = service.update_template(
        template_id=template_id,
        user_id=current_user['id'],
        updates=updates.dict(exclude_unset=True)
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update template"
        )

    return {"success": True, "message": "Template updated"}


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Delete template"""
    service = ContentTemplateService(db)

    success = service.delete_template(template_id, current_user['id'])

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete template"
        )

    return {"success": True, "message": "Template deleted"}


@router.post("/templates/{template_id}/apply")
async def apply_template(
    template_id: str,
    chapter_id: Optional[str] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Apply template to content"""
    service = ContentTemplateService(db)

    result = service.apply_template(
        user_id=current_user['id'],
        template_id=template_id,
        chapter_id=chapter_id
    )

    if 'error' in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result['error']
        )

    return {"success": True, "template_content": result}


@router.get("/templates/statistics")
async def get_template_statistics(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get template usage statistics"""
    service = ContentTemplateService(db)

    stats = service.get_template_statistics(current_user['id'])

    return {"success": True, "statistics": stats}


# ==================== Bookmark Routes ====================

@router.post("/bookmarks", status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    bookmark: BookmarkCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Create bookmark"""
    service = BookmarkService(db)

    result = service.create_bookmark(
        user_id=current_user['id'],
        content_type=bookmark.content_type,
        content_id=bookmark.content_id,
        collection_id=bookmark.collection_id,
        title=bookmark.title,
        notes=bookmark.notes,
        tags=bookmark.tags,
        is_favorite=bookmark.is_favorite
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create bookmark"
        )

    return {"success": True, "bookmark": result}


@router.get("/bookmarks")
async def get_bookmarks(
    collection_id: Optional[str] = None,
    content_type: Optional[str] = None,
    favorites_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get user's bookmarks"""
    service = BookmarkService(db)

    bookmarks = service.get_user_bookmarks(
        user_id=current_user['id'],
        collection_id=collection_id,
        content_type=content_type,
        favorites_only=favorites_only,
        limit=limit,
        offset=offset
    )

    return {"success": True, "bookmarks": bookmarks, "count": len(bookmarks)}


@router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Delete bookmark"""
    service = BookmarkService(db)

    success = service.delete_bookmark(bookmark_id, current_user['id'])

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    return {"success": True, "message": "Bookmark deleted"}


@router.post("/bookmarks/collections", status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection: CollectionCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Create bookmark collection"""
    service = BookmarkService(db)

    result = service.create_collection(
        user_id=current_user['id'],
        name=collection.name,
        description=collection.description,
        icon=collection.icon,
        color=collection.color,
        is_public=collection.is_public,
        parent_collection_id=collection.parent_collection_id
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create collection"
        )

    return {"success": True, "collection": result}


@router.get("/bookmarks/collections")
async def get_collections(
    include_shared: bool = False,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get user's collections"""
    service = BookmarkService(db)

    collections = service.get_user_collections(
        user_id=current_user['id'],
        include_shared=include_shared
    )

    return {"success": True, "collections": collections, "count": len(collections)}


@router.post("/bookmarks/collections/{collection_id}/share")
async def share_collection(
    collection_id: str,
    share: CollectionShare,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Share collection with another user"""
    service = BookmarkService(db)

    success = service.share_collection(
        collection_id=collection_id,
        user_id=current_user['id'],
        shared_with_user_id=share.shared_with_user_id,
        shared_with_email=share.shared_with_email,
        permission_level=share.permission_level
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to share collection"
        )

    return {"success": True, "message": "Collection shared"}


@router.get("/bookmarks/recommendations/{content_type}/{content_id}")
async def get_bookmark_recommendations(
    content_type: str,
    content_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get collaborative bookmark recommendations"""
    service = BookmarkService(db)

    recommendations = service.get_collaborative_recommendations(
        user_id=current_user['id'],
        content_type=content_type,
        content_id=content_id,
        limit=limit
    )

    return {"success": True, "recommendations": recommendations}


@router.get("/bookmarks/popular")
async def get_popular_bookmarked_content(
    limit: int = Query(default=20, ge=1, le=50),
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get most bookmarked content"""
    service = BookmarkService(db)

    popular = service.get_popular_bookmarked_content(limit=limit)

    return {"success": True, "popular_content": popular}


@router.get("/bookmarks/statistics")
async def get_bookmark_statistics(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get user's bookmark statistics"""
    service = BookmarkService(db)

    stats = service.get_bookmark_statistics(current_user['id'])

    return {"success": True, "statistics": stats}


# ==================== Annotation Routes ====================

@router.post("/highlights", status_code=status.HTTP_201_CREATED)
async def create_highlight(
    highlight: HighlightCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Create text highlight"""
    service = AnnotationService(db)

    result = service.create_highlight(
        user_id=current_user['id'],
        content_type=highlight.content_type,
        content_id=highlight.content_id,
        highlight_text=highlight.highlight_text,
        context_before=highlight.context_before,
        context_after=highlight.context_after,
        position_data=highlight.position_data,
        color=highlight.color
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create highlight"
        )

    return {"success": True, "highlight": result}


@router.get("/highlights/{content_type}/{content_id}")
async def get_highlights(
    content_type: str,
    content_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get highlights for content"""
    service = AnnotationService(db)

    highlights = service.get_content_highlights(
        content_type=content_type,
        content_id=content_id,
        user_id=current_user['id']
    )

    return {"success": True, "highlights": highlights, "count": len(highlights)}


@router.delete("/highlights/{highlight_id}")
async def delete_highlight(
    highlight_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Delete highlight"""
    service = AnnotationService(db)

    success = service.delete_highlight(highlight_id, current_user['id'])

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Highlight not found"
        )

    return {"success": True, "message": "Highlight deleted"}


@router.post("/annotations", status_code=status.HTTP_201_CREATED)
async def create_annotation(
    annotation: AnnotationCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Create annotation"""
    service = AnnotationService(db)

    result = service.create_annotation(
        user_id=current_user['id'],
        content_type=annotation.content_type,
        content_id=annotation.content_id,
        annotation_text=annotation.annotation_text,
        annotation_type=annotation.annotation_type,
        position_data=annotation.position_data,
        highlight_id=annotation.highlight_id,
        is_private=annotation.is_private
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create annotation"
        )

    return {"success": True, "annotation": result}


@router.get("/annotations/{content_type}/{content_id}")
async def get_annotations(
    content_type: str,
    content_id: str,
    include_private: bool = False,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get annotations for content"""
    service = AnnotationService(db)

    annotations = service.get_content_annotations(
        content_type=content_type,
        content_id=content_id,
        user_id=current_user['id'],
        include_private=include_private
    )

    return {"success": True, "annotations": annotations, "count": len(annotations)}


@router.put("/annotations/{annotation_id}")
async def update_annotation(
    annotation_id: str,
    updates: AnnotationUpdate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Update annotation"""
    service = AnnotationService(db)

    success = service.update_annotation(
        annotation_id=annotation_id,
        user_id=current_user['id'],
        updates=updates.dict(exclude_unset=True)
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update annotation"
        )

    return {"success": True, "message": "Annotation updated"}


@router.post("/annotations/{annotation_id}/resolve")
async def resolve_annotation(
    annotation_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Mark annotation as resolved"""
    service = AnnotationService(db)

    success = service.resolve_annotation(annotation_id, current_user['id'])

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to resolve annotation"
        )

    return {"success": True, "message": "Annotation resolved"}


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(
    annotation_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Delete annotation"""
    service = AnnotationService(db)

    success = service.delete_annotation(annotation_id, current_user['id'])

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found"
        )

    return {"success": True, "message": "Annotation deleted"}


@router.post("/annotations/{annotation_id}/replies")
async def add_reply(
    annotation_id: str,
    reply: ReplyCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Add reply to annotation"""
    service = AnnotationService(db)

    result = service.add_reply(
        annotation_id=annotation_id,
        user_id=current_user['id'],
        reply_text=reply.reply_text
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add reply"
        )

    return {"success": True, "reply": result}


@router.get("/annotations/{annotation_id}/replies")
async def get_replies(
    annotation_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get replies for annotation"""
    service = AnnotationService(db)

    replies = service.get_annotation_replies(annotation_id)

    return {"success": True, "replies": replies, "count": len(replies)}


@router.post("/annotations/{annotation_id}/reactions")
async def add_reaction(
    annotation_id: str,
    reaction: ReactionCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Add reaction to annotation"""
    service = AnnotationService(db)

    success = service.add_reaction(
        annotation_id=annotation_id,
        user_id=current_user['id'],
        reaction_type=reaction.reaction_type
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add reaction"
        )

    return {"success": True, "message": "Reaction added"}


@router.delete("/annotations/{annotation_id}/reactions/{reaction_type}")
async def remove_reaction(
    annotation_id: str,
    reaction_type: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Remove reaction from annotation"""
    service = AnnotationService(db)

    success = service.remove_reaction(
        annotation_id=annotation_id,
        user_id=current_user['id'],
        reaction_type=reaction_type
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reaction not found"
        )

    return {"success": True, "message": "Reaction removed"}


@router.get("/annotations/{annotation_id}/reactions")
async def get_reactions(
    annotation_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get reaction counts for annotation"""
    service = AnnotationService(db)

    reactions = service.get_annotation_reactions(annotation_id)

    return {"success": True, "reactions": reactions}


# ==================== Advanced Filter Routes ====================

@router.post("/filters", status_code=status.HTTP_201_CREATED)
async def save_filter(
    filter_data: FilterCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Save filter configuration"""
    service = AdvancedFilterService(db)

    # Validate filter config
    is_valid, error_msg = service.validate_filter_config(filter_data.filter_config)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    result = service.save_filter(
        user_id=current_user['id'],
        name=filter_data.name,
        filter_config=filter_data.filter_config,
        description=filter_data.description,
        is_favorite=filter_data.is_favorite,
        is_shared=filter_data.is_shared
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to save filter"
        )

    return {"success": True, "filter": result}


@router.get("/filters")
async def get_filters(
    include_shared: bool = True,
    favorites_only: bool = False,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get user's saved filters"""
    service = AdvancedFilterService(db)

    filters = service.get_user_filters(
        user_id=current_user['id'],
        include_shared=include_shared,
        favorites_only=favorites_only
    )

    return {"success": True, "filters": filters, "count": len(filters)}


@router.put("/filters/{filter_id}")
async def update_filter(
    filter_id: str,
    updates: FilterUpdate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Update saved filter"""
    service = AdvancedFilterService(db)

    # Validate filter config if provided
    if updates.filter_config:
        is_valid, error_msg = service.validate_filter_config(updates.filter_config)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

    success = service.update_filter(
        filter_id=filter_id,
        user_id=current_user['id'],
        updates=updates.dict(exclude_unset=True)
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update filter"
        )

    return {"success": True, "message": "Filter updated"}


@router.delete("/filters/{filter_id}")
async def delete_filter(
    filter_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Delete saved filter"""
    service = AdvancedFilterService(db)

    success = service.delete_filter(filter_id, current_user['id'])

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter not found"
        )

    return {"success": True, "message": "Filter deleted"}


@router.post("/filters/apply")
async def apply_filter(
    filter_apply: FilterApply,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Apply filter to content"""
    service = AdvancedFilterService(db)

    # Validate filter config
    is_valid, error_msg = service.validate_filter_config(filter_apply.filter_config)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    results, total_count = service.apply_filter(
        filter_config=filter_apply.filter_config,
        base_table=filter_apply.base_table,
        user_id=current_user['id'],
        limit=filter_apply.limit,
        offset=filter_apply.offset
    )

    return {
        "success": True,
        "results": results,
        "count": len(results),
        "total": total_count,
        "limit": filter_apply.limit,
        "offset": filter_apply.offset
    }


@router.get("/filters/presets")
async def get_filter_presets(
    preset_type: Optional[str] = None,
    active_only: bool = True,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get system filter presets"""
    service = AdvancedFilterService(db)

    presets = service.get_filter_presets(
        preset_type=preset_type,
        active_only=active_only
    )

    return {"success": True, "presets": presets, "count": len(presets)}


@router.get("/filters/popular")
async def get_popular_filters(
    limit: int = Query(default=10, ge=1, le=50),
    days: int = Query(default=30, ge=1, le=365),
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get most popular shared filters"""
    service = AdvancedFilterService(db)

    popular = service.get_popular_filters(limit=limit, days=days)

    return {"success": True, "popular_filters": popular}


# ==================== Content Scheduling Routes ====================

@router.post("/schedules", status_code=status.HTTP_201_CREATED)
async def schedule_publication(
    schedule: ScheduleCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Schedule content publication"""
    service = ContentSchedulingService(db)

    # Validate publish time is in the future
    if schedule.publish_at <= datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Publish time must be in the future"
        )

    result = service.schedule_publication(
        user_id=current_user['id'],
        content_type=schedule.content_type,
        content_id=schedule.content_id,
        publish_at=schedule.publish_at,
        unpublish_at=schedule.unpublish_at,
        timezone=schedule.timezone,
        notification_enabled=schedule.notification_enabled
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to schedule publication"
        )

    return {"success": True, "schedule": result}


@router.get("/schedules")
async def get_scheduled_content(
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    upcoming_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get scheduled content"""
    service = ContentSchedulingService(db)

    schedules = service.get_scheduled_content(
        user_id=current_user['id'],
        content_type=content_type,
        status=status,
        upcoming_only=upcoming_only,
        limit=limit
    )

    return {"success": True, "schedules": schedules, "count": len(schedules)}


@router.get("/schedules/upcoming")
async def get_upcoming_schedules(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=50, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get upcoming schedules"""
    service = ContentSchedulingService(db)

    upcoming = service.get_upcoming_schedules(hours=hours, limit=limit)

    return {"success": True, "upcoming_schedules": upcoming}


@router.post("/schedules/{schedule_id}/cancel")
async def cancel_schedule(
    schedule_id: str,
    reason: Optional[str] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Cancel scheduled publication"""
    service = ContentSchedulingService(db)

    success = service.cancel_schedule(
        schedule_id=schedule_id,
        user_id=current_user['id'],
        reason=reason
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to cancel schedule"
        )

    return {"success": True, "message": "Schedule cancelled"}


@router.post("/schedules/recurring", status_code=status.HTTP_201_CREATED)
async def create_recurring_schedule(
    schedule: RecurringScheduleCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Create recurring schedule"""
    service = ContentSchedulingService(db)

    result = service.create_recurring_schedule(
        user_id=current_user['id'],
        content_type=schedule.content_type,
        schedule_name=schedule.schedule_name,
        recurrence_pattern=schedule.recurrence_pattern,
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        recurrence_config=schedule.recurrence_config,
        timezone=schedule.timezone
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create recurring schedule"
        )

    return {"success": True, "recurring_schedule": result}


@router.get("/schedules/recurring")
async def get_recurring_schedules(
    active_only: bool = True,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get recurring schedules"""
    service = ContentSchedulingService(db)

    schedules = service.get_recurring_schedules(
        user_id=current_user['id'],
        active_only=active_only
    )

    return {"success": True, "recurring_schedules": schedules, "count": len(schedules)}


@router.put("/schedules/recurring/{schedule_id}")
async def update_recurring_schedule(
    schedule_id: str,
    updates: RecurringScheduleUpdate,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Update recurring schedule"""
    service = ContentSchedulingService(db)

    success = service.update_recurring_schedule(
        schedule_id=schedule_id,
        user_id=current_user['id'],
        updates=updates.dict(exclude_unset=True)
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update recurring schedule"
        )

    return {"success": True, "message": "Recurring schedule updated"}


@router.get("/schedules/statistics")
async def get_schedule_statistics(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get scheduling statistics"""
    service = ContentSchedulingService(db)

    stats = service.get_schedule_statistics(current_user['id'])

    return {"success": True, "statistics": stats}
