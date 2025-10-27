"""
Search API Routes
Advanced search with hybrid ranking and semantic similarity
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.database.connection import get_db
from backend.database.models import User
from backend.services.search_service import SearchService
from backend.services.embedding_service import EmbeddingService
from backend.utils.dependencies import get_current_user
from backend.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    search_type: str = Field(default="hybrid", description="Search type: keyword, semantic, or hybrid")
    filters: Optional[dict] = Field(default=None, description="Optional filters")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    search_type: str
    total: int
    results: List[dict]
    filters_applied: dict


class SuggestionsRequest(BaseModel):
    """Search suggestions request"""
    partial_query: str = Field(..., min_length=1, max_length=100)
    max_suggestions: int = Field(default=10, ge=1, le=20)


class RelatedContentRequest(BaseModel):
    """Related content request"""
    content_id: str
    content_type: str = Field(..., pattern="^(chapter|pdf)$")
    max_results: int = Field(default=5, ge=1, le=20)


class GenerateEmbeddingsRequest(BaseModel):
    """Generate embeddings request"""
    entity_type: str = Field(..., pattern="^(pdf|chapter|image)$")
    entity_id: str
    force_regenerate: bool = Field(default=False)


# ==================== Search Endpoints ====================

@router.post("/search", response_model=SearchResponse)
async def unified_search(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unified search across all content

    Supports three search strategies:
    - **keyword**: Traditional keyword matching
    - **semantic**: Vector similarity search using embeddings
    - **hybrid**: Weighted combination of keyword + semantic + recency

    The hybrid search uses the following weights:
    - Keyword score: 30%
    - Semantic similarity: 50%
    - Recency: 20%
    """
    try:
        logger.info(f"User {current_user.id} searching: '{request.query}' ({request.search_type})")

        search_service = SearchService(db)

        results = await search_service.search_all(
            query=request.query,
            search_type=request.search_type,
            filters=request.filters or {},
            max_results=request.max_results,
            offset=request.offset
        )

        return results

    except Exception as e:
        logger.error(f"Search failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=1, max_length=100, description="Partial search query"),
    max_suggestions: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get search suggestions/autocomplete

    Returns relevant title suggestions based on partial query
    """
    try:
        search_service = SearchService(db)

        suggestions = await search_service.get_search_suggestions(
            partial_query=q,
            max_suggestions=max_suggestions
        )

        return {
            "query": q,
            "suggestions": suggestions,
            "count": len(suggestions)
        }

    except Exception as e:
        logger.error(f"Suggestions failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Suggestions failed: {str(e)}")


@router.post("/search/related")
async def find_related_content(
    request: RelatedContentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Find related content using vector similarity

    Returns content similar to the specified item
    """
    try:
        search_service = SearchService(db)

        related = await search_service.find_related_content(
            content_id=request.content_id,
            content_type=request.content_type,
            max_results=request.max_results
        )

        return {
            "source_id": request.content_id,
            "source_type": request.content_type,
            "related": related,
            "count": len(related)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Related content search failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Related content search failed: {str(e)}")


# ==================== Semantic Search Endpoints ====================

@router.get("/search/semantic/pdfs")
async def search_pdfs_semantic(
    q: str = Query(..., min_length=1, description="Search query"),
    max_results: int = Query(default=10, ge=1, le=50),
    min_similarity: float = Query(default=0.7, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Semantic search for PDFs only

    Uses vector embeddings for semantic similarity matching
    """
    try:
        embedding_service = EmbeddingService(db)

        similar_pdfs = await embedding_service.find_similar_pdfs(
            query=q,
            max_results=max_results,
            min_similarity=min_similarity
        )

        return {
            "query": q,
            "results": similar_pdfs,
            "count": len(similar_pdfs),
            "min_similarity": min_similarity
        }

    except Exception as e:
        logger.error(f"PDF semantic search failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


@router.get("/search/semantic/images")
async def search_images_semantic(
    q: str = Query(..., min_length=1, description="Search query"),
    max_results: int = Query(default=10, ge=1, le=50),
    min_similarity: float = Query(default=0.7, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Semantic search for images only

    Searches image descriptions using vector embeddings
    """
    try:
        embedding_service = EmbeddingService(db)

        similar_images = await embedding_service.find_similar_images(
            query=q,
            max_results=max_results,
            min_similarity=min_similarity
        )

        return {
            "query": q,
            "results": similar_images,
            "count": len(similar_images),
            "min_similarity": min_similarity
        }

    except Exception as e:
        logger.error(f"Image semantic search failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


# ==================== Embedding Management ====================

@router.post("/embeddings/generate")
async def generate_embeddings(
    request: GenerateEmbeddingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate or regenerate embeddings for content

    Supports:
    - PDFs: Generate embeddings for PDF text
    - Chapters: Generate embeddings for chapter content
    - Images: Generate embeddings for image descriptions
    """
    try:
        embedding_service = EmbeddingService(db)

        # Check if embeddings already exist
        if request.entity_type == "pdf":
            from backend.database.models import PDF
            entity = db.query(PDF).filter(PDF.id == request.entity_id).first()
            if not entity:
                raise HTTPException(status_code=404, detail="PDF not found")

            if entity.embedding and not request.force_regenerate:
                return {
                    "entity_id": request.entity_id,
                    "entity_type": request.entity_type,
                    "status": "already_exists",
                    "message": "Embeddings already exist. Use force_regenerate=true to regenerate."
                }

            result = await embedding_service.generate_pdf_embeddings(request.entity_id)

        elif request.entity_type == "chapter":
            from backend.database.models import Chapter
            entity = db.query(Chapter).filter(Chapter.id == request.entity_id).first()
            if not entity:
                raise HTTPException(status_code=404, detail="Chapter not found")

            if entity.embedding and not request.force_regenerate:
                return {
                    "entity_id": request.entity_id,
                    "entity_type": request.entity_type,
                    "status": "already_exists",
                    "message": "Embeddings already exist. Use force_regenerate=true to regenerate."
                }

            result = await embedding_service.generate_chapter_embeddings(request.entity_id)

        elif request.entity_type == "image":
            from backend.database.models import Image
            entity = db.query(Image).filter(Image.id == request.entity_id).first()
            if not entity:
                raise HTTPException(status_code=404, detail="Image not found")

            if not entity.description:
                raise HTTPException(status_code=400, detail="Image has no description")

            if entity.embedding and not request.force_regenerate:
                return {
                    "entity_id": request.entity_id,
                    "entity_type": request.entity_type,
                    "status": "already_exists",
                    "message": "Embeddings already exist. Use force_regenerate=true to regenerate."
                }

            result = await embedding_service.generate_image_embeddings(
                request.entity_id,
                entity.description
            )

        return {
            "entity_id": request.entity_id,
            "entity_type": request.entity_type,
            "status": "generated",
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")


@router.post("/embeddings/batch/pdfs")
async def batch_generate_pdf_embeddings(
    batch_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Batch generate embeddings for all PDFs without embeddings

    Processes PDFs in batches to avoid memory issues
    """
    try:
        embedding_service = EmbeddingService(db)

        result = await embedding_service.update_all_pdf_embeddings(batch_size=batch_size)

        return {
            "status": "completed",
            "total_processed": result["total_processed"],
            "success": result["success"],
            "errors": result["errors"],
            "batch_size": batch_size
        }

    except Exception as e:
        logger.error(f"Batch embedding generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch generation failed: {str(e)}")


# ==================== Search Analytics ====================

@router.get("/search/stats")
async def search_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get search system statistics

    Returns counts of indexed content with embeddings
    """
    try:
        from backend.database.models import PDF, Chapter, Image
        from sqlalchemy import func

        pdfs_total = db.query(func.count(PDF.id)).scalar()
        pdfs_with_embeddings = db.query(func.count(PDF.id)).filter(
            PDF.embedding.isnot(None)
        ).scalar()

        chapters_total = db.query(func.count(Chapter.id)).scalar()
        chapters_with_embeddings = db.query(func.count(Chapter.id)).filter(
            Chapter.embedding.isnot(None)
        ).scalar()

        images_total = db.query(func.count(Image.id)).scalar()
        images_with_embeddings = db.query(func.count(Image.id)).filter(
            Image.embedding.isnot(None)
        ).scalar()

        return {
            "pdfs": {
                "total": pdfs_total,
                "with_embeddings": pdfs_with_embeddings,
                "coverage": round(pdfs_with_embeddings / pdfs_total * 100, 2) if pdfs_total > 0 else 0
            },
            "chapters": {
                "total": chapters_total,
                "with_embeddings": chapters_with_embeddings,
                "coverage": round(chapters_with_embeddings / chapters_total * 100, 2) if chapters_total > 0 else 0
            },
            "images": {
                "total": images_total,
                "with_embeddings": images_with_embeddings,
                "coverage": round(images_with_embeddings / images_total * 100, 2) if images_total > 0 else 0
            }
        }

    except Exception as e:
        logger.error(f"Failed to get search stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """Search service health check"""
    return {
        "status": "healthy",
        "service": "search",
        "features": [
            "unified_search",
            "semantic_search",
            "hybrid_ranking",
            "autocomplete",
            "related_content"
        ]
    }
