"""
Similarity Service
Handles content similarity detection, duplicate finding, and plagiarism checking
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import numpy as np
from difflib import SequenceMatcher
import re

from backend.utils import get_logger

logger = get_logger(__name__)


class SimilarityService:
    """
    Service for content similarity analysis

    Handles:
    - Vector-based similarity (embeddings)
    - Text-based similarity (Levenshtein, Jaccard)
    - Duplicate detection
    - Near-duplicate finding
    - Plagiarism checking
    - Content clustering
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== Main Similarity Methods ====================

    def find_similar_content(
        self,
        content_type: str,
        content_id: str,
        similarity_threshold: float = 0.7,
        limit: int = 10,
        methods: List[str] = ['vector', 'text']
    ) -> List[Dict[str, Any]]:
        """
        Find similar content using multiple methods

        Args:
            content_type: Type of content (chapter, pdf)
            content_id: Content ID to find similar items for
            similarity_threshold: Minimum similarity score (0-1)
            limit: Maximum number of results
            methods: Similarity methods to use (vector, text, hybrid)

        Returns:
            List of similar content items with similarity scores
        """
        try:
            similar_items = []

            if 'vector' in methods:
                vector_similar = self._find_similar_by_vector(
                    content_type, content_id, similarity_threshold, limit
                )
                similar_items.extend(vector_similar)

            if 'text' in methods:
                text_similar = self._find_similar_by_text(
                    content_type, content_id, similarity_threshold, limit
                )
                similar_items.extend(text_similar)

            # Merge results and remove duplicates
            merged = self._merge_similarity_results(similar_items, limit)

            return merged

        except Exception as e:
            logger.error(f"Failed to find similar content: {str(e)}", exc_info=True)
            return []

    def detect_duplicates(
        self,
        content_type: str,
        strict: bool = True,
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Detect duplicate or near-duplicate content

        Args:
            content_type: Type of content to check (chapter, pdf)
            strict: If True, use strict matching; if False, find near-duplicates
            batch_size: Number of items to process at once

        Returns:
            List of duplicate groups with similarity scores
        """
        try:
            threshold = 0.95 if strict else 0.80

            # Get all content items
            content_items = self._get_all_content(content_type, batch_size)

            duplicate_groups = []

            # Check each pair for similarity
            for i, item1 in enumerate(content_items):
                for item2 in content_items[i+1:]:
                    similarity = self.calculate_similarity(
                        content_type_a=content_type,
                        content_id_a=item1['id'],
                        content_type_b=content_type,
                        content_id_b=item2['id'],
                        method='hybrid'
                    )

                    if similarity and similarity >= threshold:
                        duplicate_groups.append({
                            'content_a': {
                                'id': item1['id'],
                                'title': item1['title'],
                                'created_at': item1['created_at']
                            },
                            'content_b': {
                                'id': item2['id'],
                                'title': item2['title'],
                                'created_at': item2['created_at']
                            },
                            'similarity_score': similarity,
                            'is_exact_duplicate': similarity >= 0.95
                        })

            logger.info(f"Found {len(duplicate_groups)} duplicate groups for {content_type}")
            return duplicate_groups

        except Exception as e:
            logger.error(f"Duplicate detection failed: {str(e)}", exc_info=True)
            return []

    def calculate_similarity(
        self,
        content_type_a: str,
        content_id_a: str,
        content_type_b: str,
        content_id_b: str,
        method: str = 'hybrid'
    ) -> Optional[float]:
        """
        Calculate similarity between two content items

        Args:
            content_type_a: Type of first content
            content_id_a: ID of first content
            content_type_b: Type of second content
            content_id_b: ID of second content
            method: Similarity method (vector, text, hybrid)

        Returns:
            Similarity score (0-1) or None if calculation fails
        """
        try:
            # Check cache first
            cached = self._get_cached_similarity(
                content_type_a, content_id_a,
                content_type_b, content_id_b
            )
            if cached is not None:
                return cached

            # Calculate similarity based on method
            if method == 'vector':
                similarity = self._calculate_vector_similarity(
                    content_type_a, content_id_a,
                    content_type_b, content_id_b
                )
            elif method == 'text':
                similarity = self._calculate_text_similarity(
                    content_type_a, content_id_a,
                    content_type_b, content_id_b
                )
            elif method == 'hybrid':
                vector_sim = self._calculate_vector_similarity(
                    content_type_a, content_id_a,
                    content_type_b, content_id_b
                )
                text_sim = self._calculate_text_similarity(
                    content_type_a, content_id_a,
                    content_type_b, content_id_b
                )

                # Weighted average: 70% vector, 30% text
                if vector_sim is not None and text_sim is not None:
                    similarity = vector_sim * 0.7 + text_sim * 0.3
                else:
                    similarity = vector_sim or text_sim
            else:
                logger.warning(f"Unknown method: {method}")
                return None

            # Cache result
            if similarity is not None:
                self._cache_similarity(
                    content_type_a, content_id_a,
                    content_type_b, content_id_b,
                    similarity, method
                )

            return similarity

        except Exception as e:
            logger.error(f"Similarity calculation failed: {str(e)}", exc_info=True)
            return None

    # ==================== Vector-Based Similarity ====================

    def _find_similar_by_vector(
        self,
        content_type: str,
        content_id: str,
        threshold: float,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Find similar content using vector embeddings (cosine similarity)
        """
        try:
            # Use PostgreSQL function for efficient vector search
            query = text("""
                SELECT
                    similar_type,
                    similar_id,
                    similarity_score
                FROM get_similar_content(
                    :content_type,
                    :content_id,
                    :limit,
                    :threshold
                )
            """)

            result = self.db.execute(query, {
                'content_type': content_type,
                'content_id': content_id,
                'limit': limit,
                'threshold': threshold
            })

            similar = []
            for row in result:
                details = self._get_content_details(row[0], str(row[1]))
                if details:
                    similar.append({
                        'id': str(row[1]),
                        'type': row[0],
                        'title': details['title'],
                        'similarity_score': float(row[2]),
                        'method': 'vector',
                        'created_at': details.get('created_at')
                    })

            return similar

        except Exception as e:
            logger.error(f"Vector similarity search failed: {str(e)}", exc_info=True)
            return []

    def _calculate_vector_similarity(
        self,
        content_type_a: str,
        content_id_a: str,
        content_type_b: str,
        content_id_b: str
    ) -> Optional[float]:
        """
        Calculate cosine similarity between vector embeddings
        """
        try:
            # Get embeddings for both content items
            embedding_a = self._get_content_embedding(content_type_a, content_id_a)
            embedding_b = self._get_content_embedding(content_type_b, content_id_b)

            if embedding_a is None or embedding_b is None:
                return None

            # Calculate cosine similarity using PostgreSQL vector operations
            query = text("""
                SELECT 1 - (:embedding_a::vector <=> :embedding_b::vector) as similarity
            """)

            result = self.db.execute(query, {
                'embedding_a': str(embedding_a),
                'embedding_b': str(embedding_b)
            })

            row = result.fetchone()
            return float(row[0]) if row else None

        except Exception as e:
            logger.error(f"Vector similarity calculation failed: {str(e)}", exc_info=True)
            return None

    def _get_content_embedding(
        self,
        content_type: str,
        content_id: str
    ) -> Optional[List[float]]:
        """
        Get vector embedding for content
        """
        try:
            if content_type == 'chapter':
                query = text("""
                    SELECT embedding
                    FROM chapter_embeddings
                    WHERE chapter_id = :content_id
                    LIMIT 1
                """)
            elif content_type == 'pdf':
                query = text("""
                    SELECT embedding
                    FROM pdf_embeddings
                    WHERE pdf_id = :content_id
                    LIMIT 1
                """)
            else:
                return None

            result = self.db.execute(query, {'content_id': content_id})
            row = result.fetchone()

            if row and row[0]:
                # Parse vector from PostgreSQL format
                # Format: [0.1, 0.2, 0.3, ...]
                return row[0]

            return None

        except Exception as e:
            logger.error(f"Failed to get embedding: {str(e)}", exc_info=True)
            return None

    # ==================== Text-Based Similarity ====================

    def _find_similar_by_text(
        self,
        content_type: str,
        content_id: str,
        threshold: float,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Find similar content using text comparison (Levenshtein, n-grams)
        """
        try:
            # Get source content text
            source_text = self._get_content_text(content_type, content_id)
            if not source_text:
                return []

            # Get all other content for comparison
            all_content = self._get_all_content(content_type, limit * 3)

            similar = []
            for content in all_content:
                if content['id'] == content_id:
                    continue

                target_text = content.get('text', '')
                if not target_text:
                    continue

                # Calculate text similarity
                similarity = self._text_similarity_score(source_text, target_text)

                if similarity >= threshold:
                    similar.append({
                        'id': content['id'],
                        'type': content_type,
                        'title': content['title'],
                        'similarity_score': similarity,
                        'method': 'text',
                        'created_at': content.get('created_at')
                    })

            # Sort by similarity and limit
            similar.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar[:limit]

        except Exception as e:
            logger.error(f"Text similarity search failed: {str(e)}", exc_info=True)
            return []

    def _calculate_text_similarity(
        self,
        content_type_a: str,
        content_id_a: str,
        content_type_b: str,
        content_id_b: str
    ) -> Optional[float]:
        """
        Calculate text similarity using multiple methods
        """
        try:
            text_a = self._get_content_text(content_type_a, content_id_a)
            text_b = self._get_content_text(content_type_b, content_id_b)

            if not text_a or not text_b:
                return None

            return self._text_similarity_score(text_a, text_b)

        except Exception as e:
            logger.error(f"Text similarity calculation failed: {str(e)}", exc_info=True)
            return None

    def _text_similarity_score(
        self,
        text1: str,
        text2: str
    ) -> float:
        """
        Calculate text similarity using multiple algorithms

        Combines:
        - SequenceMatcher (ratio)
        - Jaccard similarity (word overlap)
        - Character n-gram similarity
        """
        try:
            # Clean and normalize texts
            text1_clean = self._clean_text(text1)
            text2_clean = self._clean_text(text2)

            # Method 1: SequenceMatcher (0.4 weight)
            sequence_ratio = SequenceMatcher(None, text1_clean, text2_clean).ratio()

            # Method 2: Jaccard similarity on words (0.3 weight)
            words1 = set(text1_clean.lower().split())
            words2 = set(text2_clean.lower().split())

            if words1 or words2:
                jaccard = len(words1 & words2) / len(words1 | words2)
            else:
                jaccard = 0.0

            # Method 3: Character trigram similarity (0.3 weight)
            trigram_sim = self._ngram_similarity(text1_clean, text2_clean, n=3)

            # Weighted combination
            combined = (
                sequence_ratio * 0.4 +
                jaccard * 0.3 +
                trigram_sim * 0.3
            )

            return combined

        except Exception as e:
            logger.error(f"Text similarity scoring failed: {str(e)}", exc_info=True)
            return 0.0

    def _ngram_similarity(
        self,
        text1: str,
        text2: str,
        n: int = 3
    ) -> float:
        """
        Calculate n-gram similarity
        """
        try:
            ngrams1 = set(self._get_ngrams(text1, n))
            ngrams2 = set(self._get_ngrams(text2, n))

            if not ngrams1 or not ngrams2:
                return 0.0

            intersection = len(ngrams1 & ngrams2)
            union = len(ngrams1 | ngrams2)

            return intersection / union if union > 0 else 0.0

        except Exception as e:
            logger.error(f"N-gram similarity failed: {str(e)}", exc_info=True)
            return 0.0

    def _get_ngrams(self, text: str, n: int) -> List[str]:
        """
        Get character n-grams from text
        """
        text = text.lower()
        return [text[i:i+n] for i in range(len(text) - n + 1)]

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text for comparison
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep alphanumeric and spaces
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()

    # ==================== Helper Methods ====================

    def _get_content_text(
        self,
        content_type: str,
        content_id: str
    ) -> Optional[str]:
        """
        Get full text content for similarity comparison
        """
        try:
            if content_type == 'chapter':
                query = text("""
                    SELECT content
                    FROM chapters
                    WHERE id = :content_id
                """)
            elif content_type == 'pdf':
                query = text("""
                    SELECT extracted_text
                    FROM pdfs
                    WHERE id = :content_id
                """)
            else:
                return None

            result = self.db.execute(query, {'content_id': content_id})
            row = result.fetchone()

            return row[0] if row else None

        except Exception as e:
            logger.error(f"Failed to get content text: {str(e)}", exc_info=True)
            return None

    def _get_content_details(
        self,
        content_type: str,
        content_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get content metadata
        """
        try:
            if content_type == 'chapter':
                query = text("""
                    SELECT id, title, created_at
                    FROM chapters
                    WHERE id = :content_id
                """)
            elif content_type == 'pdf':
                query = text("""
                    SELECT id, title, upload_date as created_at
                    FROM pdfs
                    WHERE id = :content_id
                """)
            else:
                return None

            result = self.db.execute(query, {'content_id': content_id})
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'title': row[1],
                    'created_at': row[2].isoformat() if row[2] else None
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get content details: {str(e)}", exc_info=True)
            return None

    def _get_all_content(
        self,
        content_type: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all content items for batch processing
        """
        try:
            if content_type == 'chapter':
                query = text("""
                    SELECT id, title, content as text, created_at
                    FROM chapters
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
            elif content_type == 'pdf':
                query = text("""
                    SELECT id, title, extracted_text as text, upload_date as created_at
                    FROM pdfs
                    ORDER BY upload_date DESC
                    LIMIT :limit
                """)
            else:
                return []

            result = self.db.execute(query, {'limit': limit})

            content_list = []
            for row in result:
                content_list.append({
                    'id': str(row[0]),
                    'title': row[1],
                    'text': row[2],
                    'created_at': row[3].isoformat() if row[3] else None
                })

            return content_list

        except Exception as e:
            logger.error(f"Failed to get all content: {str(e)}", exc_info=True)
            return []

    def _merge_similarity_results(
        self,
        results: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Merge results from multiple similarity methods
        """
        # Group by content ID
        merged_dict = {}

        for result in results:
            key = (result['type'], result['id'])

            if key in merged_dict:
                # Combine scores from different methods
                existing = merged_dict[key]
                existing['similarity_score'] = max(
                    existing['similarity_score'],
                    result['similarity_score']
                )
                if 'methods' not in existing:
                    existing['methods'] = [existing.get('method', 'unknown')]
                existing['methods'].append(result.get('method', 'unknown'))
            else:
                merged_dict[key] = result

        # Convert back to list and sort
        merged_list = list(merged_dict.values())
        merged_list.sort(key=lambda x: x['similarity_score'], reverse=True)

        return merged_list[:limit]

    # ==================== Caching Methods ====================

    def _get_cached_similarity(
        self,
        content_type_a: str,
        content_id_a: str,
        content_type_b: str,
        content_id_b: str
    ) -> Optional[float]:
        """
        Get cached similarity score
        """
        try:
            query = text("""
                SELECT similarity_score
                FROM similarity_cache
                WHERE (
                    (content_type_a = :type_a AND content_id_a = :id_a
                     AND content_type_b = :type_b AND content_id_b = :id_b)
                    OR
                    (content_type_a = :type_b AND content_id_a = :id_b
                     AND content_type_b = :type_a AND content_id_b = :id_a)
                )
                AND (expires_at IS NULL OR expires_at > NOW())
                LIMIT 1
            """)

            result = self.db.execute(query, {
                'type_a': content_type_a,
                'id_a': content_id_a,
                'type_b': content_type_b,
                'id_b': content_id_b
            })

            row = result.fetchone()
            return float(row[0]) if row else None

        except Exception as e:
            logger.error(f"Failed to get cached similarity: {str(e)}", exc_info=True)
            return None

    def _cache_similarity(
        self,
        content_type_a: str,
        content_id_a: str,
        content_type_b: str,
        content_id_b: str,
        similarity_score: float,
        method: str
    ) -> None:
        """
        Cache similarity calculation result
        """
        try:
            expires_at = datetime.now() + timedelta(days=7)

            query = text("""
                INSERT INTO similarity_cache (
                    content_type_a, content_id_a,
                    content_type_b, content_id_b,
                    similarity_score, similarity_method, expires_at
                )
                VALUES (
                    :type_a, :id_a, :type_b, :id_b,
                    :score, :method, :expires_at
                )
                ON CONFLICT (content_type_a, content_id_a, content_type_b, content_id_b)
                DO UPDATE SET
                    similarity_score = EXCLUDED.similarity_score,
                    calculated_at = NOW(),
                    expires_at = EXCLUDED.expires_at
            """)

            self.db.execute(query, {
                'type_a': content_type_a,
                'id_a': content_id_a,
                'type_b': content_type_b,
                'id_b': content_id_b,
                'score': similarity_score,
                'method': method,
                'expires_at': expires_at
            })

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cache similarity: {str(e)}", exc_info=True)

    # ==================== Plagiarism Detection ====================

    def check_plagiarism(
        self,
        content_type: str,
        content_text: str,
        threshold: float = 0.85
    ) -> Dict[str, Any]:
        """
        Check if content is plagiarized from existing content

        Args:
            content_type: Type of content to check against
            content_text: Text to check for plagiarism
            threshold: Similarity threshold for plagiarism (default 0.85)

        Returns:
            Dict with plagiarism results
        """
        try:
            # Get all existing content
            existing_content = self._get_all_content(content_type, limit=500)

            potential_plagiarism = []

            for content in existing_content:
                similarity = self._text_similarity_score(
                    content_text,
                    content.get('text', '')
                )

                if similarity >= threshold:
                    potential_plagiarism.append({
                        'content_id': content['id'],
                        'content_title': content['title'],
                        'similarity_score': similarity,
                        'is_likely_plagiarism': similarity >= 0.90,
                        'created_at': content.get('created_at')
                    })

            # Sort by similarity
            potential_plagiarism.sort(key=lambda x: x['similarity_score'], reverse=True)

            return {
                'is_plagiarized': len(potential_plagiarism) > 0,
                'matches_found': len(potential_plagiarism),
                'highest_similarity': potential_plagiarism[0]['similarity_score'] if potential_plagiarism else 0.0,
                'potential_sources': potential_plagiarism[:10],  # Top 10 matches
                'checked_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Plagiarism check failed: {str(e)}", exc_info=True)
            return {
                'is_plagiarized': False,
                'error': str(e)
            }
