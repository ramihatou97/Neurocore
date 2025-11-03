"""
Image Recommendation Service
Provides similar image recommendations based on embedding similarity
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import func, and_, cast, Numeric
from sqlalchemy.orm import Session
import numpy as np

from backend.database.models import Image
from backend.services.ai_provider_service import AIProviderService
from backend.utils import get_logger

logger = get_logger(__name__)


class ImageRecommendationService:
    """
    Service for recommending similar images based on vector embeddings

    Features:
    - Find similar images by image ID
    - Find similar images by query text
    - Content-based filtering (image type, quality, anatomical region)
    - Diversity boosting (avoid recommending too many similar images)
    - Explainability (why this image was recommended)
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.ai_service = AIProviderService()

    async def recommend_similar_images(
        self,
        image_id: str,
        max_results: int = 10,
        min_similarity: float = 0.7,
        filter_image_type: Optional[str] = None,
        min_quality: float = 0.5,
        diversity_threshold: float = 0.95
    ) -> List[Dict[str, Any]]:
        """
        Recommend similar images based on a reference image

        Args:
            image_id: Reference image ID
            max_results: Maximum recommendations to return
            min_similarity: Minimum similarity threshold (0.0-1.0)
            filter_image_type: Filter by image type (e.g., 'MRI', 'CT')
            min_quality: Minimum quality score (0.0-1.0)
            diversity_threshold: Similarity threshold for diversity boosting

        Returns:
            List of recommended images with metadata and similarity scores
        """
        # Get reference image
        ref_image = self.db.query(Image).filter(Image.id == image_id).first()

        if not ref_image:
            raise ValueError(f"Image {image_id} not found")

        if ref_image.embedding is None:
            raise ValueError(f"Image {image_id} has no embedding")

        logger.info(f"Finding similar images to {image_id} (type: {ref_image.image_type})")

        # Build query with vector similarity
        query = self.db.query(
            Image,
            func.round(
                cast(1 - Image.embedding.cosine_distance(ref_image.embedding), Numeric),
                4
            ).label('similarity')
        ).filter(
            and_(
                Image.id != image_id,  # Exclude reference image
                Image.embedding.isnot(None),
                Image.embedding.cosine_distance(ref_image.embedding) <= (1 - min_similarity)
            )
        )

        # Apply filters
        if filter_image_type:
            query = query.filter(Image.image_type == filter_image_type)

        if min_quality > 0:
            query = query.filter(
                Image.quality_score >= min_quality
            )

        # Order by similarity
        query = query.order_by(
            Image.embedding.cosine_distance(ref_image.embedding)
        )

        # Get initial results (more than needed for diversity boosting)
        results = query.limit(max_results * 3).all()

        if not results:
            logger.warning(f"No similar images found for {image_id}")
            return []

        # Apply diversity boosting
        diverse_results = self._apply_diversity_boosting(
            results,
            max_results,
            diversity_threshold
        )

        # Format recommendations with explanations
        recommendations = []
        for image, similarity in diverse_results:
            # Generate explanation
            explanation = self._generate_recommendation_explanation(
                ref_image,
                image,
                float(similarity)
            )

            recommendations.append({
                'image_id': str(image.id),
                'file_path': image.file_path,
                'thumbnail_path': image.thumbnail_path,
                'image_type': image.image_type,
                'anatomical_structures': image.anatomical_structures or [],
                'page_number': image.page_number,
                'quality_score': float(image.quality_score) if image.quality_score else None,
                'similarity': float(similarity),
                'explanation': explanation,
                'dimensions': {
                    'width': image.width,
                    'height': image.height
                }
            })

        logger.info(f"Returning {len(recommendations)} recommendations for {image_id}")
        return recommendations

    async def recommend_by_query(
        self,
        query: str,
        max_results: int = 10,
        min_similarity: float = 0.7,
        filter_image_type: Optional[str] = None,
        min_quality: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Recommend images based on a text query

        Args:
            query: Text description of desired images
            max_results: Maximum recommendations to return
            min_similarity: Minimum similarity threshold
            filter_image_type: Filter by image type
            min_quality: Minimum quality score

        Returns:
            List of recommended images
        """
        logger.info(f"Finding images matching query: '{query}'")

        # Generate embedding for query
        embedding_result = await self.ai_service.generate_embedding(query)
        query_embedding = embedding_result['embedding']

        # Build query with vector similarity
        query_db = self.db.query(
            Image,
            func.round(
                cast(1 - Image.embedding.cosine_distance(query_embedding), Numeric),
                4
            ).label('similarity')
        ).filter(
            and_(
                Image.embedding.isnot(None),
                Image.embedding.cosine_distance(query_embedding) <= (1 - min_similarity)
            )
        )

        # Apply filters
        if filter_image_type:
            query_db = query_db.filter(Image.image_type == filter_image_type)

        if min_quality > 0:
            query_db = query_db.filter(
                Image.quality_score >= min_quality
            )

        # Order by similarity
        results = query_db.order_by(
            Image.embedding.cosine_distance(query_embedding)
        ).limit(max_results).all()

        # Format results
        recommendations = []
        for image, similarity in results:
            recommendations.append({
                'image_id': str(image.id),
                'file_path': image.file_path,
                'thumbnail_path': image.thumbnail_path,
                'image_type': image.image_type,
                'anatomical_structures': image.anatomical_structures or [],
                'page_number': image.page_number,
                'quality_score': float(image.quality_score) if image.quality_score else None,
                'similarity': float(similarity),
                'description_snippet': image.ai_description[:200] + '...' if image.ai_description and len(image.ai_description) > 200 else image.ai_description
            })

        logger.info(f"Found {len(recommendations)} images matching query")
        return recommendations

    def _apply_diversity_boosting(
        self,
        results: List[Tuple[Image, float]],
        max_results: int,
        diversity_threshold: float
    ) -> List[Tuple[Image, float]]:
        """
        Apply diversity boosting to avoid too many nearly-identical images

        Uses greedy selection: pick most similar, then only add images
        that are sufficiently different from already selected images
        """
        if not results:
            return []

        selected = []
        selected_embeddings = []

        for image, similarity in results:
            if len(selected) >= max_results:
                break

            # First image is always added
            if len(selected) == 0:
                selected.append((image, similarity))
                selected_embeddings.append(image.embedding)
                continue

            # Check if this image is diverse enough from already selected
            is_diverse = True
            for selected_emb in selected_embeddings:
                # Calculate cosine similarity using numpy
                dot_product = np.dot(image.embedding, selected_emb)
                norm_a = np.linalg.norm(image.embedding)
                norm_b = np.linalg.norm(selected_emb)
                sim_to_selected = dot_product / (norm_a * norm_b)

                if sim_to_selected > diversity_threshold:
                    is_diverse = False
                    break

            if is_diverse:
                selected.append((image, similarity))
                selected_embeddings.append(image.embedding)

        return selected

    def _generate_recommendation_explanation(
        self,
        ref_image: Image,
        recommended_image: Image,
        similarity: float
    ) -> str:
        """
        Generate human-readable explanation for why image was recommended
        """
        explanations = []

        # Similarity explanation
        if similarity > 0.9:
            explanations.append("Very similar content")
        elif similarity > 0.8:
            explanations.append("Similar content")
        elif similarity > 0.7:
            explanations.append("Somewhat similar content")

        # Type match
        if ref_image.image_type and recommended_image.image_type:
            if ref_image.image_type == recommended_image.image_type:
                explanations.append(f"Same type: {ref_image.image_type}")

        # Anatomical structure overlap
        if ref_image.anatomical_structures and recommended_image.anatomical_structures:
            common = set(ref_image.anatomical_structures) & set(recommended_image.anatomical_structures)
            if common:
                explanations.append(f"Shared structures: {', '.join(list(common)[:2])}")

        # Quality
        if recommended_image.quality_score and recommended_image.quality_score > 0.7:
            explanations.append("High quality")

        return " • ".join(explanations) if explanations else "Similar visual features"

    async def get_recommendation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about recommendation system readiness

        Returns:
            Statistics about images available for recommendations
        """
        total_images = self.db.query(func.count(Image.id)).scalar()

        images_with_embeddings = self.db.query(func.count(Image.id)).filter(
            Image.embedding.isnot(None)
        ).scalar()

        images_by_type = self.db.query(
            Image.image_type,
            func.count(Image.id)
        ).filter(
            Image.embedding.isnot(None)
        ).group_by(Image.image_type).all()

        avg_quality = self.db.query(
            func.avg(Image.quality_score)
        ).filter(
            Image.embedding.isnot(None)
        ).scalar()

        return {
            'total_images': total_images,
            'images_with_embeddings': images_with_embeddings,
            'recommendation_coverage': round(images_with_embeddings / total_images * 100, 1) if total_images > 0 else 0,
            'images_by_type': [
                {'type': img_type, 'count': count}
                for img_type, count in images_by_type
            ],
            'average_quality': round(float(avg_quality), 2) if avg_quality else None,
            'status': 'ready' if images_with_embeddings > 0 else 'not_ready'
        }
