"""
AI Features API Routes
Endpoints for recommendations, tagging, similarity, suggestions, summaries, and Q&A
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.database.connection import get_db
from backend.database.models import User
from backend.services.recommendation_service import RecommendationService
from backend.services.tagging_service import TaggingService
from backend.services.similarity_service import SimilarityService
from backend.services.suggestion_service import SuggestionService
from backend.services.summary_service import SummaryService
from backend.services.qa_service import QuestionAnsweringService
from backend.utils.dependencies import get_current_user
from backend.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==================== Request Models ====================

class AutoTagRequest(BaseModel):
    content_type: str = Field(..., description="Content type (chapter, pdf)")
    content_id: str = Field(..., description="Content ID")
    max_tags: int = Field(default=5, description="Maximum tags to generate")


class QuestionRequest(BaseModel):
    question: str = Field(..., description="Question to answer")
    session_id: Optional[str] = Field(None, description="Session ID for conversation")


class FeedbackRequest(BaseModel):
    was_helpful: bool = Field(..., description="Was the answer helpful")
    feedback_text: Optional[str] = Field(None, description="Optional feedback text")


class SummaryRequest(BaseModel):
    content_type: str = Field(..., description="Content type (chapter, pdf)")
    content_id: str = Field(..., description="Content ID")
    summary_type: str = Field(default="brief", description="Type: brief, detailed, technical, layman")
    force_regenerate: bool = Field(default=False, description="Force new generation")


# ==================== Recommendations ====================

@router.get("/recommendations")
async def get_recommendations(
    algorithm: str = Query("hybrid", description="Algorithm: content_based, collaborative, hybrid"),
    source_type: Optional[str] = Query(None, description="Source content type"),
    source_id: Optional[str] = Query(None, description="Source content ID"),
    limit: int = Query(10, description="Max recommendations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get personalized content recommendations

    Uses collaborative filtering, content-based, or hybrid algorithms
    """
    try:
        rec_service = RecommendationService(db)

        recommendations = rec_service.get_recommendations(
            user_id=str(current_user.id),
            source_type=source_type,
            source_id=source_id,
            algorithm=algorithm,
            limit=limit
        )

        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations),
            "algorithm": algorithm
        }

    except Exception as e:
        logger.error(f"Recommendations failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/interaction")
async def track_interaction(
    interaction_type: str,
    content_type: str,
    content_id: str,
    duration_seconds: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Track user interaction for recommendation training"""
    try:
        rec_service = RecommendationService(db)

        rec_service.track_user_interaction(
            user_id=str(current_user.id),
            interaction_type=interaction_type,
            content_type=content_type,
            content_id=content_id,
            duration_seconds=duration_seconds
        )

        return {"success": True}

    except Exception as e:
        logger.error(f"Interaction tracking failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Tagging ====================

@router.post("/tags/auto-tag")
async def auto_tag_content(
    request: AutoTagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Auto-tag content using AI

    Analyzes content and generates relevant tags
    """
    try:
        tagging_service = TaggingService(db)

        # Get content text
        content_text = await _get_content_text(db, request.content_type, request.content_id)

        if not content_text:
            raise HTTPException(status_code=404, detail="Content not found")

        tags = tagging_service.auto_tag_content(
            content_type=request.content_type,
            content_id=request.content_id,
            content_text=content_text,
            max_tags=request.max_tags
        )

        return {
            "success": True,
            "tags": tags,
            "count": len(tags)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auto-tagging failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/suggest")
async def suggest_tags(
    content_type: str,
    content_id: str,
    limit: int = Query(10, description="Max suggestions"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tag suggestions for content"""
    try:
        tagging_service = TaggingService(db)

        # Get content text for AI suggestions
        content_text = await _get_content_text(db, content_type, content_id)

        suggestions = tagging_service.suggest_tags(
            content_type=content_type,
            content_id=content_id,
            text=content_text,
            limit=limit
        )

        return {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions)
        }

    except Exception as e:
        logger.error(f"Tag suggestion failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags")
async def get_all_tags(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, description="Max results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all tags"""
    try:
        tagging_service = TaggingService(db)

        tags = tagging_service.get_all_tags(category=category, limit=limit)

        return {
            "success": True,
            "tags": tags,
            "count": len(tags)
        }

    except Exception as e:
        logger.error(f"Get tags failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/popular")
async def get_popular_tags(
    limit: int = Query(20, description="Max results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get most popular tags"""
    try:
        tagging_service = TaggingService(db)

        tags = tagging_service.get_popular_tags(limit=limit)

        return {
            "success": True,
            "tags": tags,
            "count": len(tags)
        }

    except Exception as e:
        logger.error(f"Get popular tags failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/{content_type}/{content_id}/tags")
async def get_content_tags(
    content_type: str,
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tags for specific content"""
    try:
        tagging_service = TaggingService(db)

        tags = tagging_service.get_content_tags(content_type, content_id)

        return {
            "success": True,
            "tags": tags,
            "count": len(tags)
        }

    except Exception as e:
        logger.error(f"Get content tags failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Similarity ====================

@router.get("/similarity/find")
async def find_similar_content(
    content_type: str,
    content_id: str,
    threshold: float = Query(0.7, description="Similarity threshold (0-1)"),
    limit: int = Query(10, description="Max results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Find similar content"""
    try:
        similarity_service = SimilarityService(db)

        similar = similarity_service.find_similar_content(
            content_type=content_type,
            content_id=content_id,
            similarity_threshold=threshold,
            limit=limit
        )

        return {
            "success": True,
            "similar_content": similar,
            "count": len(similar)
        }

    except Exception as e:
        logger.error(f"Find similar failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similarity/duplicates")
async def detect_duplicates(
    content_type: str,
    strict: bool = Query(True, description="Strict matching"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detect duplicate content"""
    try:
        similarity_service = SimilarityService(db)

        duplicates = similarity_service.detect_duplicates(
            content_type=content_type,
            strict=strict
        )

        return {
            "success": True,
            "duplicates": duplicates,
            "count": len(duplicates)
        }

    except Exception as e:
        logger.error(f"Duplicate detection failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Suggestions ====================

@router.get("/suggestions/related")
async def get_related_content(
    content_type: str,
    content_id: str,
    limit: int = Query(10, description="Max results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get related content suggestions"""
    try:
        suggestion_service = SuggestionService(db)

        related = suggestion_service.get_related_content(
            content_type=content_type,
            content_id=content_id,
            suggestion_types=['similar', 'tags', 'citations'],
            limit=limit
        )

        return {
            "success": True,
            "related_content": related
        }

    except Exception as e:
        logger.error(f"Related content failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/next-reading")
async def suggest_next_reading(
    current_type: Optional[str] = Query(None, description="Current content type"),
    current_id: Optional[str] = Query(None, description="Current content ID"),
    limit: int = Query(5, description="Max suggestions"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Suggest what to read next"""
    try:
        suggestion_service = SuggestionService(db)

        suggestions = suggestion_service.suggest_next_reading(
            user_id=str(current_user.id),
            current_content_type=current_type,
            current_content_id=current_id,
            limit=limit
        )

        return {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions)
        }

    except Exception as e:
        logger.error(f"Next reading suggestion failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Summaries ====================

@router.post("/summaries/generate")
async def generate_summary(
    request: SummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate AI summary for content"""
    try:
        summary_service = SummaryService(db)

        # Get content text
        content_text = await _get_content_text(db, request.content_type, request.content_id)
        content_title = await _get_content_title(db, request.content_type, request.content_id)

        if not content_text:
            raise HTTPException(status_code=404, detail="Content not found")

        summary = summary_service.generate_summary(
            content_type=request.content_type,
            content_id=request.content_id,
            content_text=content_text,
            content_title=content_title,
            summary_type=request.summary_type,
            force_regenerate=request.force_regenerate
        )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries/{content_type}/{content_id}")
async def get_content_summaries(
    content_type: str,
    content_id: str,
    summary_type: Optional[str] = Query(None, description="Filter by type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get existing summaries for content"""
    try:
        summary_service = SummaryService(db)

        if summary_type:
            summary = summary_service.get_summary(content_type, content_id, summary_type)
            return {"success": True, "summary": summary}
        else:
            summaries = summary_service.get_all_summaries(content_type, content_id)
            return {"success": True, "summaries": summaries, "count": len(summaries)}

    except Exception as e:
        logger.error(f"Get summaries failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Q&A ====================

@router.post("/qa/ask")
async def ask_question(
    request: QuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ask a question about the knowledge base

    Uses RAG (Retrieval-Augmented Generation) to answer questions
    """
    try:
        qa_service = QuestionAnsweringService(db)

        result = qa_service.ask_question(
            user_id=str(current_user.id),
            question=request.question,
            session_id=request.session_id
        )

        return result

    except Exception as e:
        logger.error(f"Q&A failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qa/history")
async def get_qa_history(
    session_id: Optional[str] = Query(None, description="Filter by session"),
    limit: int = Query(10, description="Max results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get Q&A conversation history"""
    try:
        qa_service = QuestionAnsweringService(db)

        history = qa_service.get_conversation_history(
            user_id=str(current_user.id),
            session_id=session_id,
            limit=limit
        )

        return {
            "success": True,
            "history": history,
            "count": len(history)
        }

    except Exception as e:
        logger.error(f"Get history failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qa/{qa_id}/feedback")
async def submit_qa_feedback(
    qa_id: str,
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback on Q&A answer"""
    try:
        qa_service = QuestionAnsweringService(db)

        success = qa_service.submit_feedback(
            qa_id=qa_id,
            user_id=str(current_user.id),
            was_helpful=request.was_helpful,
            feedback_text=request.feedback_text
        )

        return {"success": success}

    except Exception as e:
        logger.error(f"Feedback submission failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qa/statistics")
async def get_qa_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get Q&A usage statistics"""
    try:
        qa_service = QuestionAnsweringService(db)

        stats = qa_service.get_qa_statistics(user_id=str(current_user.id))

        return {
            "success": True,
            "statistics": stats
        }

    except Exception as e:
        logger.error(f"Get statistics failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Helper Functions ====================

async def _get_content_text(db: Session, content_type: str, content_id: str) -> Optional[str]:
    """Get content text for AI processing"""
    from sqlalchemy import text

    try:
        if content_type == 'chapter':
            query = text("SELECT content FROM chapters WHERE id = :id")
        elif content_type == 'pdf':
            query = text("SELECT extracted_text FROM pdfs WHERE id = :id")
        else:
            return None

        result = db.execute(query, {'id': content_id})
        row = result.fetchone()

        return row[0] if row else None

    except Exception as e:
        logger.error(f"Failed to get content text: {str(e)}", exc_info=True)
        return None


async def _get_content_title(db: Session, content_type: str, content_id: str) -> Optional[str]:
    """Get content title"""
    from sqlalchemy import text

    try:
        if content_type == 'chapter':
            query = text("SELECT title FROM chapters WHERE id = :id")
        elif content_type == 'pdf':
            query = text("SELECT title FROM pdfs WHERE id = :id")
        else:
            return None

        result = db.execute(query, {'id': content_id})
        row = result.fetchone()

        return row[0] if row else None

    except Exception as e:
        logger.error(f"Failed to get content title: {str(e)}", exc_info=True)
        return None


# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """AI features service health check"""
    return {
        "status": "healthy",
        "service": "ai_features",
        "features": [
            "recommendations",
            "auto_tagging",
            "similarity_detection",
            "content_suggestions",
            "ai_summaries",
            "question_answering"
        ]
    }
