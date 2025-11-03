"""
Image API Routes
Endpoints for image recommendations and duplicate detection
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.database.connection import get_db
from backend.database.models import Image
from backend.services.image_recommendation_service import ImageRecommendationService
from backend.services.image_duplicate_detection_service import ImageDuplicateDetectionService
from backend.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/images", tags=["images"])


# ==================== REQUEST/RESPONSE MODELS ====================

class RecommendationRequest(BaseModel):
    """Request model for image recommendations"""
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of recommendations")
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")
    filter_image_type: Optional[str] = Field(default=None, description="Filter by image type")
    min_quality: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum quality score")
    diversity_threshold: float = Field(default=0.95, ge=0.0, le=1.0, description="Diversity threshold")


class QueryRecommendationRequest(BaseModel):
    """Request model for text query-based recommendations"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    max_results: int = Field(default=10, ge=1, le=50)
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)
    filter_image_type: Optional[str] = None
    min_quality: float = Field(default=0.5, ge=0.0, le=1.0)


class DuplicateDetectionRequest(BaseModel):
    """Request model for duplicate detection"""
    pdf_id: Optional[str] = Field(default=None, description="Optional PDF ID to limit scope")
    similarity_threshold: float = Field(default=0.95, ge=0.8, le=1.0, description="Similarity threshold")
    mark_duplicates: bool = Field(default=True, description="Whether to mark duplicates in database")


# ==================== IMAGE RECOMMENDATIONS ====================

@router.get("/{image_id}/recommendations")
async def get_image_recommendations(
    image_id: str,
    max_results: int = Query(default=10, ge=1, le=50),
    min_similarity: float = Query(default=0.7, ge=0.0, le=1.0),
    filter_image_type: Optional[str] = Query(default=None),
    min_quality: float = Query(default=0.5, ge=0.0, le=1.0),
    diversity_threshold: float = Query(default=0.95, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    Get similar image recommendations based on a reference image

    Returns images that are visually and semantically similar to the reference image.
    Uses vector embeddings and content-based filtering.

    **Parameters:**
    - **image_id**: ID of the reference image
    - **max_results**: Maximum number of recommendations (1-50)
    - **min_similarity**: Minimum similarity threshold (0.0-1.0)
    - **filter_image_type**: Optional filter by image type
    - **min_quality**: Minimum quality score (0.0-1.0)
    - **diversity_threshold**: Threshold for diversity boosting (0.0-1.0)

    **Returns:**
    - List of recommended images with similarity scores and explanations
    """
    try:
        logger.info(f"Getting recommendations for image {image_id}")

        # Verify image exists
        image = db.query(Image).filter(Image.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail=f"Image {image_id} not found")

        if image.embedding is None:
            raise HTTPException(
                status_code=400,
                detail=f"Image {image_id} has no embedding. Run embedding generation first."
            )

        # Get recommendations
        service = ImageRecommendationService(db)
        recommendations = await service.recommend_similar_images(
            image_id=image_id,
            max_results=max_results,
            min_similarity=min_similarity,
            filter_image_type=filter_image_type,
            min_quality=min_quality,
            diversity_threshold=diversity_threshold
        )

        logger.info(f"Returning {len(recommendations)} recommendations for image {image_id}")

        return {
            "reference_image_id": image_id,
            "reference_image_type": image.image_type,
            "recommendations": recommendations,
            "count": len(recommendations),
            "params": {
                "max_results": max_results,
                "min_similarity": min_similarity,
                "filter_image_type": filter_image_type,
                "min_quality": min_quality,
                "diversity_threshold": diversity_threshold
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations for image {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@router.post("/recommendations/by-query")
async def get_recommendations_by_query(
    request: QueryRecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    Get image recommendations based on a text query

    Finds images that match the semantic meaning of the query text.
    Useful for natural language image search.

    **Request Body:**
    - **query**: Search query (e.g., "brain MRI showing tumor")
    - **max_results**: Maximum number of results
    - **min_similarity**: Minimum similarity threshold
    - **filter_image_type**: Optional image type filter
    - **min_quality**: Minimum quality score

    **Returns:**
    - List of matching images with similarity scores
    """
    try:
        logger.info(f"Getting recommendations for query: '{request.query}'")

        service = ImageRecommendationService(db)
        recommendations = await service.recommend_by_query(
            query=request.query,
            max_results=request.max_results,
            min_similarity=request.min_similarity,
            filter_image_type=request.filter_image_type,
            min_quality=request.min_quality
        )

        logger.info(f"Returning {len(recommendations)} results for query: '{request.query}'")

        return {
            "query": request.query,
            "results": recommendations,
            "count": len(recommendations),
            "params": {
                "max_results": request.max_results,
                "min_similarity": request.min_similarity,
                "filter_image_type": request.filter_image_type,
                "min_quality": request.min_quality
            }
        }

    except Exception as e:
        logger.error(f"Error getting recommendations for query '{request.query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@router.get("/recommendations/stats")
async def get_recommendation_stats(db: Session = Depends(get_db)):
    """
    Get statistics about the recommendation system

    Returns information about:
    - Total images available for recommendations
    - Coverage by image type
    - Average quality scores
    - System readiness status

    **Returns:**
    - Comprehensive statistics about the recommendation system
    """
    try:
        service = ImageRecommendationService(db)
        stats = await service.get_recommendation_stats()

        return stats

    except Exception as e:
        logger.error(f"Error getting recommendation stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ==================== DUPLICATE DETECTION ====================

@router.post("/duplicates/detect")
async def detect_duplicates(
    request: DuplicateDetectionRequest,
    db: Session = Depends(get_db)
):
    """
    Detect duplicate images across the dataset

    Uses vector embeddings to find images that are nearly identical.
    Can optionally mark duplicates in the database for automated handling.

    **Request Body:**
    - **pdf_id**: Optional PDF ID to limit detection scope
    - **similarity_threshold**: Threshold for considering images as duplicates (0.8-1.0)
    - **mark_duplicates**: Whether to mark duplicates in database

    **Returns:**
    - Detection results with duplicate groups and statistics
    - Space savings estimates
    """
    try:
        logger.info(f"Starting duplicate detection (threshold: {request.similarity_threshold})")

        service = ImageDuplicateDetectionService(db)
        results = await service.detect_duplicates(
            pdf_id=request.pdf_id,
            similarity_threshold=request.similarity_threshold,
            mark_duplicates=request.mark_duplicates
        )

        logger.info(f"Duplicate detection complete: {results.get('duplicate_groups', 0)} groups found")

        return results

    except Exception as e:
        logger.error(f"Error detecting duplicates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to detect duplicates: {str(e)}")


@router.get("/duplicates/stats")
async def get_duplicate_stats(
    pdf_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Get duplicate detection statistics

    Returns information about:
    - Total images analyzed
    - Number of duplicates found
    - Images ready for detection
    - System status

    **Parameters:**
    - **pdf_id**: Optional PDF ID to limit scope

    **Returns:**
    - Statistics about duplicates in the dataset
    """
    try:
        service = ImageDuplicateDetectionService(db)
        stats = await service.get_duplicate_stats(pdf_id=pdf_id)

        return stats

    except Exception as e:
        logger.error(f"Error getting duplicate stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/duplicates/clusters")
async def get_duplicate_clusters(
    pdf_id: Optional[str] = Query(default=None),
    min_cluster_size: int = Query(default=2, ge=2, le=10),
    db: Session = Depends(get_db)
):
    """
    Get all duplicate clusters for review

    Returns groups of duplicate images with details about each cluster.
    Useful for manual review and validation of duplicate detection.

    **Parameters:**
    - **pdf_id**: Optional PDF ID to limit scope
    - **min_cluster_size**: Minimum number of images in cluster (2-10)

    **Returns:**
    - List of duplicate clusters with image details
    """
    try:
        service = ImageDuplicateDetectionService(db)
        clusters = await service.get_duplicate_clusters(
            pdf_id=pdf_id,
            min_cluster_size=min_cluster_size
        )

        return {
            "clusters": clusters,
            "count": len(clusters),
            "params": {
                "pdf_id": pdf_id,
                "min_cluster_size": min_cluster_size
            }
        }

    except Exception as e:
        logger.error(f"Error getting duplicate clusters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get clusters: {str(e)}")


@router.delete("/duplicates/clear")
async def clear_duplicate_marks(
    pdf_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Clear all duplicate marks from images

    Removes duplicate flags from images, allowing for re-detection.
    Useful after adjusting detection thresholds or for system maintenance.

    **Parameters:**
    - **pdf_id**: Optional PDF ID to limit scope

    **Returns:**
    - Number of images unmarked
    """
    try:
        service = ImageDuplicateDetectionService(db)
        count = await service.clear_duplicate_marks(pdf_id=pdf_id)

        logger.info(f"Cleared duplicate marks from {count} images")

        return {
            "cleared_count": count,
            "status": "success",
            "message": f"Successfully cleared duplicate marks from {count} images"
        }

    except Exception as e:
        logger.error(f"Error clearing duplicate marks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear marks: {str(e)}")


# ==================== IMAGE DETAILS ====================

@router.get("/{image_id}")
async def get_image_details(
    image_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific image

    Returns comprehensive image metadata including:
    - AI analysis results
    - Quality scores
    - Anatomical structures
    - Embedding status
    - Duplicate information

    **Parameters:**
    - **image_id**: ID of the image

    **Returns:**
    - Complete image details
    """
    try:
        image = db.query(Image).filter(Image.id == image_id).first()

        if not image:
            raise HTTPException(status_code=404, detail=f"Image {image_id} not found")

        return image.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get image details: {str(e)}")
