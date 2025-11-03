"""
Image Duplicate Detection Service
Detects duplicate and near-duplicate images using embedding similarity
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from datetime import datetime
import numpy as np

from backend.database.models import Image
from backend.utils import get_logger

logger = get_logger(__name__)


class ImageDuplicateDetectionService:
    """
    Service for detecting duplicate and near-duplicate images using vector embeddings

    Features:
    - Exact duplicates (similarity > 0.98)
    - Near duplicates (similarity > 0.95)
    - Batch duplicate detection across entire dataset
    - Smart deduplication strategies (keep best quality)
    - Duplicate reporting and statistics
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    async def detect_duplicates(
        self,
        pdf_id: Optional[str] = None,
        similarity_threshold: float = 0.95,
        mark_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Detect duplicate images across dataset

        Args:
            pdf_id: Optional PDF ID to limit scope
            similarity_threshold: Similarity threshold for duplicates (0.95 = 95%)
            mark_duplicates: Whether to mark duplicates in database

        Returns:
            Detection results with duplicate groups and statistics
        """
        logger.info(f"Starting duplicate detection (threshold: {similarity_threshold})")

        # Get images with embeddings
        query = self.db.query(Image).filter(
            Image.embedding.isnot(None)
        )

        if pdf_id:
            query = query.filter(Image.pdf_id == pdf_id)

        images = query.all()

        if len(images) < 2:
            logger.warning("Not enough images for duplicate detection")
            return {
                'total_images': len(images),
                'duplicate_groups': [],
                'total_duplicates': 0,
                'status': 'insufficient_data'
            }

        logger.info(f"Analyzing {len(images)} images for duplicates...")

        # Find duplicate groups
        duplicate_groups = self._find_duplicate_groups(
            images,
            similarity_threshold
        )

        # Statistics
        total_duplicates = sum(len(group) - 1 for group in duplicate_groups)
        space_saved = self._calculate_space_saved(duplicate_groups)

        # Mark duplicates if requested
        if mark_duplicates and duplicate_groups:
            marked_count = self._mark_duplicates(duplicate_groups)
            logger.info(f"Marked {marked_count} images as duplicates")

        result = {
            'total_images': len(images),
            'duplicate_groups': len(duplicate_groups),
            'total_duplicates': total_duplicates,
            'duplicate_rate_pct': round(total_duplicates / len(images) * 100, 1),
            'space_potentially_saved_mb': space_saved,
            'similarity_threshold': similarity_threshold,
            'groups': [
                self._format_duplicate_group(group)
                for group in duplicate_groups[:10]  # Limit to first 10 groups
            ],
            'status': 'complete'
        }

        logger.info(
            f"Duplicate detection complete: {len(duplicate_groups)} groups, "
            f"{total_duplicates} duplicates ({result['duplicate_rate_pct']}%)"
        )

        return result

    def _find_duplicate_groups(
        self,
        images: List[Image],
        similarity_threshold: float
    ) -> List[List[Image]]:
        """
        Find groups of duplicate images using embedding similarity

        Uses greedy clustering: for each unprocessed image, find all similar images
        """
        processed = set()
        duplicate_groups = []

        for i, image1 in enumerate(images):
            if image1.id in processed:
                continue

            # Find similar images
            group = [image1]
            processed.add(image1.id)

            for j in range(i + 1, len(images)):
                image2 = images[j]

                if image2.id in processed:
                    continue

                # Calculate similarity
                similarity = self._calculate_similarity(image1, image2)

                if similarity >= similarity_threshold:
                    group.append(image2)
                    processed.add(image2.id)

            # Only keep groups with 2+ images
            if len(group) >= 2:
                # Sort by quality (best first)
                group.sort(
                    key=lambda img: (
                        img.quality_score or 0,
                        img.confidence_score or 0,
                        -img.file_size_bytes  # Larger file (less compressed) is better
                    ),
                    reverse=True
                )
                duplicate_groups.append(group)

        return duplicate_groups

    def _calculate_similarity(self, image1: Image, image2: Image) -> float:
        """
        Calculate cosine similarity between two images

        Returns similarity score 0.0-1.0
        """
        if image1.embedding is None or image2.embedding is None:
            return 0.0

        # Calculate cosine similarity using numpy
        dot_product = np.dot(image1.embedding, image2.embedding)
        norm_a = np.linalg.norm(image1.embedding)
        norm_b = np.linalg.norm(image2.embedding)
        similarity = dot_product / (norm_a * norm_b)

        return float(max(0.0, min(1.0, similarity)))

    def _calculate_space_saved(self, duplicate_groups: List[List[Image]]) -> float:
        """
        Calculate potential space savings from removing duplicates

        Returns size in MB
        """
        total_bytes = 0

        for group in duplicate_groups:
            # Keep the first image (best quality), remove others
            for duplicate in group[1:]:
                total_bytes += duplicate.file_size_bytes or 0

        return round(total_bytes / (1024 * 1024), 2)

    def _mark_duplicates(self, duplicate_groups: List[List[Image]]) -> int:
        """
        Mark duplicate images in database

        First image in each group is kept as original, others marked as duplicates
        """
        marked_count = 0

        for group in duplicate_groups:
            original = group[0]  # Best quality image

            for duplicate in group[1:]:
                duplicate.is_duplicate = True
                duplicate.duplicate_of_id = original.id
                marked_count += 1

        self.db.commit()
        return marked_count

    def _format_duplicate_group(self, group: List[Image]) -> Dict[str, Any]:
        """
        Format duplicate group for API response
        """
        return {
            'group_size': len(group),
            'original': {
                'id': str(group[0].id),
                'file_path': group[0].file_path,
                'quality_score': float(group[0].quality_score) if group[0].quality_score else None,
                'file_size_mb': round((group[0].file_size_bytes or 0) / (1024 * 1024), 2),
                'page_number': group[0].page_number
            },
            'duplicates': [
                {
                    'id': str(img.id),
                    'file_path': img.file_path,
                    'quality_score': float(img.quality_score) if img.quality_score else None,
                    'file_size_mb': round((img.file_size_bytes or 0) / (1024 * 1024), 2),
                    'page_number': img.page_number,
                    'similarity': round(self._calculate_similarity(group[0], img), 4)
                }
                for img in group[1:]
            ]
        }

    async def get_duplicate_stats(self, pdf_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get duplicate detection statistics

        Args:
            pdf_id: Optional PDF ID to limit scope

        Returns:
            Statistics about duplicates in the dataset
        """
        query = self.db.query(Image)

        if pdf_id:
            query = query.filter(Image.pdf_id == pdf_id)

        total = query.count()
        duplicates = query.filter(Image.is_duplicate == True).count()
        with_embeddings = query.filter(Image.embedding.isnot(None)).count()

        return {
            'total_images': total,
            'marked_as_duplicates': duplicates,
            'duplicate_rate_pct': round(duplicates / total * 100, 1) if total > 0 else 0,
            'images_with_embeddings': with_embeddings,
            'ready_for_detection': with_embeddings >= 2,
            'status': 'ready' if with_embeddings >= 2 else 'not_ready'
        }

    async def clear_duplicate_marks(self, pdf_id: Optional[str] = None) -> int:
        """
        Clear all duplicate marks (for re-detection)

        Args:
            pdf_id: Optional PDF ID to limit scope

        Returns:
            Number of images unmarked
        """
        query = self.db.query(Image).filter(Image.is_duplicate == True)

        if pdf_id:
            query = query.filter(Image.pdf_id == pdf_id)

        images = query.all()

        for image in images:
            image.is_duplicate = False
            image.duplicate_of_id = None

        self.db.commit()

        logger.info(f"Cleared duplicate marks from {len(images)} images")
        return len(images)

    async def get_duplicate_clusters(
        self,
        pdf_id: Optional[str] = None,
        min_cluster_size: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get all duplicate clusters (for review/visualization)

        Args:
            pdf_id: Optional PDF ID to limit scope
            min_cluster_size: Minimum number of images in cluster

        Returns:
            List of duplicate clusters with details
        """
        # Get images marked as duplicates
        query = self.db.query(Image).filter(
            Image.is_duplicate == True,
            Image.duplicate_of_id.isnot(None)
        )

        if pdf_id:
            query = query.filter(Image.pdf_id == pdf_id)

        duplicates = query.all()

        # Group by original
        clusters = {}
        for dup in duplicates:
            original_id = dup.duplicate_of_id
            if original_id not in clusters:
                # Get original image
                original = self.db.query(Image).filter(Image.id == original_id).first()
                if original:
                    clusters[original_id] = {
                        'original': original,
                        'duplicates': []
                    }

            if original_id in clusters:
                clusters[original_id]['duplicates'].append(dup)

        # Filter by cluster size and format
        result = []
        for cluster_data in clusters.values():
            if len(cluster_data['duplicates']) >= (min_cluster_size - 1):
                result.append(
                    self._format_duplicate_group(
                        [cluster_data['original']] + cluster_data['duplicates']
                    )
                )

        return result
