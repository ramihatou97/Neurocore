"""
Summary Service
Handles AI-powered content summarization
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from openai import OpenAI  # Fixed: Migrated to openai>=1.0.0 client pattern
import re

from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class SummaryService:
    """
    Service for AI-powered content summarization

    Handles:
    - Brief summaries
    - Detailed summaries
    - Key points extraction
    - Technical vs. layman summaries
    - Summary caching and management
    """

    def __init__(self, db: Session):
        self.db = db
        # Fixed: Initialize OpenAI client (openai>=1.0.0 pattern)
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # ==================== Summary Generation ====================

    def generate_summary(
        self,
        content_type: str,
        content_id: str,
        content_text: str,
        content_title: Optional[str] = None,
        summary_type: str = 'brief',
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate AI summary for content

        Args:
            content_type: Type of content (chapter, pdf)
            content_id: Content ID
            content_text: Full text to summarize
            content_title: Optional title for context
            summary_type: Type of summary (brief, detailed, technical, layman)
            force_regenerate: Force new generation even if cached

        Returns:
            Dict with summary and metadata
        """
        try:
            # Check for existing summary
            if not force_regenerate:
                existing = self.get_summary(content_type, content_id, summary_type)
                if existing:
                    logger.info(f"Using cached summary for {content_type} {content_id}")
                    return existing

            # Generate new summary
            start_time = datetime.now()

            summary_text, key_points = self._generate_with_ai(
                text=content_text,
                title=content_title,
                summary_type=summary_type
            )

            generation_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Calculate quality score
            quality_score = self._assess_quality(summary_text, content_text)

            # Store summary
            summary_id = self._store_summary(
                content_type=content_type,
                content_id=content_id,
                summary_type=summary_type,
                summary_text=summary_text,
                key_points=key_points,
                generation_time_ms=generation_time,
                quality_score=quality_score
            )

            return {
                'id': summary_id,
                'content_type': content_type,
                'content_id': content_id,
                'summary_type': summary_type,
                'summary': summary_text,
                'key_points': key_points,
                'word_count': len(summary_text.split()),
                'quality_score': quality_score,
                'generation_time_ms': generation_time,
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}", exc_info=True)
            return {'error': str(e)}

    def _generate_with_ai(
        self,
        text: str,
        title: Optional[str],
        summary_type: str
    ) -> tuple[str, List[str]]:
        """
        Generate summary using OpenAI
        """
        # Truncate if too long
        max_chars = 6000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        # Build prompt based on summary type
        if summary_type == 'brief':
            instruction = "Provide a concise 2-3 sentence summary."
            max_length = 150
        elif summary_type == 'detailed':
            instruction = "Provide a comprehensive summary covering all major points."
            max_length = 500
        elif summary_type == 'technical':
            instruction = "Provide a technical summary with medical terminology and clinical details."
            max_length = 300
        elif summary_type == 'layman':
            instruction = "Provide a simple, easy-to-understand summary for non-experts."
            max_length = 200
        else:
            instruction = "Provide a balanced summary."
            max_length = 250

        prompt = f"""Summarize the following neurosurgical content:

Title: {title or 'N/A'}

Content:
{text}

{instruction}

Also extract 3-5 key points as a bulleted list.

Format your response as:

SUMMARY:
[Your summary here]

KEY POINTS:
- Point 1
- Point 2
- Point 3
"""

        try:
            # Fixed: Use new client.chat.completions.create() API (openai>=1.0.0)
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a medical expert specializing in neurosurgery summarization."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=max_length + 100
            )

            # Fixed: Response is now an object, not dict
            content = response.choices[0].message.content.strip()

            # Parse summary and key points
            summary_match = re.search(r'SUMMARY:\s*(.+?)(?=KEY POINTS:|$)', content, re.DOTALL)
            keypoints_match = re.search(r'KEY POINTS:\s*(.+)', content, re.DOTALL)

            summary = summary_match.group(1).strip() if summary_match else content

            key_points = []
            if keypoints_match:
                points_text = keypoints_match.group(1)
                key_points = [
                    line.strip('- ').strip()
                    for line in points_text.split('\n')
                    if line.strip().startswith('-')
                ]

            return summary, key_points

        except Exception as e:
            logger.error(f"AI summary generation failed: {str(e)}", exc_info=True)
            raise

    def _assess_quality(self, summary: str, original_text: str) -> float:
        """
        Assess summary quality score (0-1)
        """
        try:
            # Simple heuristics
            summary_words = len(summary.split())
            original_words = len(original_text.split())

            # Compression ratio (should be between 0.05 and 0.20)
            compression = summary_words / max(original_words, 1)

            if 0.05 <= compression <= 0.20:
                compression_score = 1.0
            else:
                compression_score = 0.7

            # Length appropriateness (50-300 words ideal)
            if 50 <= summary_words <= 300:
                length_score = 1.0
            else:
                length_score = 0.8

            # Coherence (simple check for complete sentences)
            has_period = '.' in summary
            coherence_score = 1.0 if has_period else 0.6

            # Combined score
            quality = (compression_score * 0.4 + length_score * 0.3 + coherence_score * 0.3)

            return round(quality, 2)

        except Exception as e:
            logger.error(f"Quality assessment failed: {str(e)}", exc_info=True)
            return 0.7

    # ==================== Summary Storage & Retrieval ====================

    def _store_summary(
        self,
        content_type: str,
        content_id: str,
        summary_type: str,
        summary_text: str,
        key_points: List[str],
        generation_time_ms: int,
        quality_score: float
    ) -> Optional[str]:
        """
        Store generated summary in database
        """
        try:
            import json

            query = text("""
                INSERT INTO content_summaries (
                    content_type, content_id, summary_type,
                    summary_text, word_count, key_points,
                    generated_by, generation_time_ms, quality_score
                )
                VALUES (
                    :content_type, :content_id, :summary_type,
                    :summary_text, :word_count, :key_points::jsonb,
                    'gpt-4', :generation_time_ms, :quality_score
                )
                ON CONFLICT (content_type, content_id, summary_type)
                DO UPDATE SET
                    summary_text = EXCLUDED.summary_text,
                    word_count = EXCLUDED.word_count,
                    key_points = EXCLUDED.key_points,
                    generation_time_ms = EXCLUDED.generation_time_ms,
                    quality_score = EXCLUDED.quality_score,
                    updated_at = NOW()
                RETURNING id
            """)

            result = self.db.execute(query, {
                'content_type': content_type,
                'content_id': content_id,
                'summary_type': summary_type,
                'summary_text': summary_text,
                'word_count': len(summary_text.split()),
                'key_points': json.dumps(key_points),
                'generation_time_ms': generation_time_ms,
                'quality_score': quality_score
            })

            self.db.commit()

            row = result.fetchone()
            return str(row[0]) if row else None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to store summary: {str(e)}", exc_info=True)
            return None

    def get_summary(
        self,
        content_type: str,
        content_id: str,
        summary_type: str = 'brief'
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing summary from database
        """
        try:
            query = text("""
                SELECT
                    id, summary_text, word_count, key_points,
                    generated_by, generation_time_ms, quality_score,
                    is_approved, created_at
                FROM content_summaries
                WHERE content_type = :content_type
                    AND content_id = :content_id
                    AND summary_type = :summary_type
            """)

            result = self.db.execute(query, {
                'content_type': content_type,
                'content_id': content_id,
                'summary_type': summary_type
            })

            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'content_type': content_type,
                    'content_id': content_id,
                    'summary_type': summary_type,
                    'summary': row[1],
                    'word_count': row[2],
                    'key_points': row[3] if row[3] else [],
                    'generated_by': row[4],
                    'generation_time_ms': row[5],
                    'quality_score': float(row[6]) if row[6] else None,
                    'is_approved': row[7],
                    'generated_at': row[8].isoformat() if row[8] else None
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get summary: {str(e)}", exc_info=True)
            return None

    def get_all_summaries(
        self,
        content_type: str,
        content_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all summary types for content
        """
        try:
            query = text("""
                SELECT
                    id, summary_type, summary_text, word_count,
                    key_points, quality_score, created_at
                FROM content_summaries
                WHERE content_type = :content_type
                    AND content_id = :content_id
                ORDER BY created_at DESC
            """)

            result = self.db.execute(query, {
                'content_type': content_type,
                'content_id': content_id
            })

            summaries = []
            for row in result:
                summaries.append({
                    'id': str(row[0]),
                    'summary_type': row[1],
                    'summary': row[2],
                    'word_count': row[3],
                    'key_points': row[4] if row[4] else [],
                    'quality_score': float(row[5]) if row[5] else None,
                    'generated_at': row[6].isoformat() if row[6] else None
                })

            return summaries

        except Exception as e:
            logger.error(f"Failed to get summaries: {str(e)}", exc_info=True)
            return []

    def approve_summary(
        self,
        summary_id: str,
        approved_by: str
    ) -> bool:
        """
        Approve a summary for publication
        """
        try:
            query = text("""
                UPDATE content_summaries
                SET is_approved = TRUE, approved_by = :approved_by
                WHERE id = :summary_id
            """)

            self.db.execute(query, {
                'summary_id': summary_id,
                'approved_by': approved_by
            })

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to approve summary: {str(e)}", exc_info=True)
            return False

    def delete_summary(self, summary_id: str) -> bool:
        """
        Delete a summary
        """
        try:
            query = text("DELETE FROM content_summaries WHERE id = :summary_id")
            self.db.execute(query, {'summary_id': summary_id})
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete summary: {str(e)}", exc_info=True)
            return False
