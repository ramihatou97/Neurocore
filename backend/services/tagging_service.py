"""
Tagging Service
Handles auto-tagging with AI, manual tagging, and tag management
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_, desc
from uuid import UUID
import json
from openai import OpenAI  # Fixed: Migrated to openai>=1.0.0 client pattern
import re

from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class TaggingService:
    """
    Service for content tagging

    Handles:
    - AI-powered auto-tagging
    - Manual tag management
    - Tag suggestions
    - Tag statistics and analytics
    - Bulk tagging operations
    """

    def __init__(self, db: Session):
        self.db = db
        # Fixed: Initialize OpenAI client (openai>=1.0.0 pattern)
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # ==================== Auto-Tagging Methods ====================

    def auto_tag_content(
        self,
        content_type: str,
        content_id: str,
        content_text: str,
        content_title: Optional[str] = None,
        max_tags: int = 5,
        min_confidence: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Automatically tag content using AI

        Args:
            content_type: Type of content (chapter, pdf)
            content_id: Content ID
            content_text: Full text content to analyze
            content_title: Optional title for context
            max_tags: Maximum number of tags to generate
            min_confidence: Minimum confidence threshold

        Returns:
            List of generated tags with confidence scores
        """
        try:
            # Generate tags using AI
            suggested_tags = self._generate_tags_with_ai(
                text=content_text,
                title=content_title,
                max_tags=max_tags
            )

            # Filter by confidence
            filtered_tags = [
                tag for tag in suggested_tags
                if tag['confidence'] >= min_confidence
            ]

            # Create or get existing tags
            created_tags = []
            for tag_info in filtered_tags:
                tag = self._get_or_create_tag(
                    name=tag_info['name'],
                    category=tag_info.get('category', 'general'),
                    is_auto_generated=True
                )

                if tag:
                    # Associate tag with content
                    association = self.add_tag_to_content(
                        content_type=content_type,
                        content_id=content_id,
                        tag_id=tag['id'],
                        confidence_score=tag_info['confidence'],
                        is_auto_tagged=True
                    )

                    if association:
                        created_tags.append({
                            'tag_id': tag['id'],
                            'tag_name': tag['name'],
                            'confidence': tag_info['confidence'],
                            'category': tag.get('category')
                        })

            logger.info(f"Auto-tagged {content_type} {content_id} with {len(created_tags)} tags")
            return created_tags

        except Exception as e:
            logger.error(f"Auto-tagging failed: {str(e)}", exc_info=True)
            return []

    def _generate_tags_with_ai(
        self,
        text: str,
        title: Optional[str] = None,
        max_tags: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Use OpenAI to generate relevant tags from content

        Args:
            text: Content text to analyze
            title: Optional title for context
            max_tags: Maximum number of tags

        Returns:
            List of tag dictionaries with name, confidence, and category
        """
        try:
            # Truncate text if too long (GPT context limit)
            max_chars = 4000
            if len(text) > max_chars:
                text = text[:max_chars] + "..."

            # Build prompt
            prompt = f"""Analyze the following medical/neurosurgery content and generate relevant tags.

Title: {title or 'N/A'}

Content:
{text}

Generate {max_tags} relevant tags that best describe this content. For each tag:
1. Provide a concise tag name (1-3 words)
2. Assign a confidence score (0.0 to 1.0)
3. Categorize it as: medical, anatomical, procedure, research, or general

Format your response as a JSON array:
[
  {{"name": "Tag Name", "confidence": 0.95, "category": "medical"}},
  ...
]

Focus on:
- Medical conditions and diagnoses
- Anatomical structures
- Surgical procedures
- Research topics
- Clinical concepts

Return ONLY the JSON array, no additional text."""

            # Fixed: Use new client.chat.completions.create() API (openai>=1.0.0)
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a medical content tagging expert specializing in neurosurgery."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            # Fixed: Response is now an object, not dict
            response_text = response.choices[0].message.content.strip()

            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                tags_data = json.loads(json_match.group(0))
            else:
                tags_data = json.loads(response_text)

            # Validate and normalize tags
            validated_tags = []
            for tag in tags_data[:max_tags]:
                if 'name' in tag and 'confidence' in tag:
                    validated_tags.append({
                        'name': tag['name'].strip().title(),
                        'confidence': min(1.0, max(0.0, float(tag['confidence']))),
                        'category': tag.get('category', 'general')
                    })

            return validated_tags

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"AI tag generation failed: {str(e)}", exc_info=True)
            return []

    def suggest_tags(
        self,
        content_type: str,
        content_id: str,
        text: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Suggest tags for content without applying them

        Uses both AI and existing tag patterns
        """
        try:
            suggestions = []

            # Get AI suggestions if text provided
            if text:
                ai_tags = self._generate_tags_with_ai(text, max_tags=limit)
                for tag in ai_tags:
                    # Check if tag already exists
                    existing = self._find_tag_by_name(tag['name'])
                    suggestions.append({
                        'name': tag['name'],
                        'confidence': tag['confidence'],
                        'category': tag.get('category'),
                        'exists': existing is not None,
                        'tag_id': existing['id'] if existing else None,
                        'usage_count': existing['usage_count'] if existing else 0
                    })

            # Get popular tags as additional suggestions
            popular_tags = self.get_popular_tags(limit=limit)
            for tag in popular_tags:
                # Don't duplicate AI suggestions
                if not any(s['name'].lower() == tag['name'].lower() for s in suggestions):
                    suggestions.append({
                        'name': tag['name'],
                        'confidence': min(1.0, tag['usage_count'] / 100.0),
                        'category': tag.get('category'),
                        'exists': True,
                        'tag_id': tag['id'],
                        'usage_count': tag['usage_count']
                    })

            # Sort by confidence
            suggestions.sort(key=lambda x: x['confidence'], reverse=True)

            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Failed to suggest tags: {str(e)}", exc_info=True)
            return []

    # ==================== Tag Management ====================

    def create_tag(
        self,
        name: str,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        category: str = 'general',
        color: str = '#1976d2'
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new tag
        """
        try:
            # Generate slug if not provided
            if not slug:
                slug = self._generate_slug(name)

            query = text("""
                INSERT INTO tags (name, slug, description, category, color, is_auto_generated)
                VALUES (:name, :slug, :description, :category, :color, FALSE)
                RETURNING id, name, slug, category, color, usage_count, created_at
            """)

            result = self.db.execute(query, {
                'name': name,
                'slug': slug,
                'description': description,
                'category': category,
                'color': color
            })

            self.db.commit()

            row = result.fetchone()
            return {
                'id': str(row[0]),
                'name': row[1],
                'slug': row[2],
                'category': row[3],
                'color': row[4],
                'usage_count': row[5],
                'created_at': row[6].isoformat() if row[6] else None
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create tag: {str(e)}", exc_info=True)
            return None

    def _get_or_create_tag(
        self,
        name: str,
        category: str = 'general',
        is_auto_generated: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing tag or create new one
        """
        # Try to find existing tag
        existing = self._find_tag_by_name(name)
        if existing:
            return existing

        # Create new tag
        slug = self._generate_slug(name)

        try:
            query = text("""
                INSERT INTO tags (name, slug, category, is_auto_generated)
                VALUES (:name, :slug, :category, :is_auto_generated)
                ON CONFLICT (name) DO UPDATE SET updated_at = NOW()
                RETURNING id, name, slug, category, is_auto_generated, usage_count
            """)

            result = self.db.execute(query, {
                'name': name,
                'slug': slug,
                'category': category,
                'is_auto_generated': is_auto_generated
            })

            self.db.commit()

            row = result.fetchone()
            return {
                'id': str(row[0]),
                'name': row[1],
                'slug': row[2],
                'category': row[3],
                'is_auto_generated': row[4],
                'usage_count': row[5]
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to get/create tag: {str(e)}", exc_info=True)
            return None

    def _find_tag_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find tag by name (case-insensitive)
        """
        try:
            query = text("""
                SELECT id, name, slug, category, color, is_auto_generated, usage_count
                FROM tags
                WHERE LOWER(name) = LOWER(:name)
            """)

            result = self.db.execute(query, {'name': name})
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'name': row[1],
                    'slug': row[2],
                    'category': row[3],
                    'color': row[4],
                    'is_auto_generated': row[5],
                    'usage_count': row[6]
                }

            return None

        except Exception as e:
            logger.error(f"Failed to find tag: {str(e)}", exc_info=True)
            return None

    def get_tag(self, tag_id: str) -> Optional[Dict[str, Any]]:
        """
        Get tag by ID
        """
        try:
            query = text("""
                SELECT id, name, slug, description, category, color,
                       is_auto_generated, usage_count, created_at, updated_at
                FROM tags
                WHERE id = :tag_id
            """)

            result = self.db.execute(query, {'tag_id': tag_id})
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'name': row[1],
                    'slug': row[2],
                    'description': row[3],
                    'category': row[4],
                    'color': row[5],
                    'is_auto_generated': row[6],
                    'usage_count': row[7],
                    'created_at': row[8].isoformat() if row[8] else None,
                    'updated_at': row[9].isoformat() if row[9] else None
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get tag: {str(e)}", exc_info=True)
            return None

    def get_all_tags(
        self,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all tags with optional filtering
        """
        try:
            conditions = []
            params = {'limit': limit, 'offset': offset}

            if category:
                conditions.append("category = :category")
                params['category'] = category

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = text(f"""
                SELECT id, name, slug, category, color, is_auto_generated, usage_count
                FROM tags
                {where_clause}
                ORDER BY usage_count DESC, name ASC
                LIMIT :limit OFFSET :offset
            """)

            result = self.db.execute(query, params)

            tags = []
            for row in result:
                tags.append({
                    'id': str(row[0]),
                    'name': row[1],
                    'slug': row[2],
                    'category': row[3],
                    'color': row[4],
                    'is_auto_generated': row[5],
                    'usage_count': row[6]
                })

            return tags

        except Exception as e:
            logger.error(f"Failed to get tags: {str(e)}", exc_info=True)
            return []

    def get_popular_tags(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get most popular tags by usage count
        """
        try:
            query = text("""
                SELECT id, name, slug, category, usage_count
                FROM get_popular_tags(:limit)
            """)

            result = self.db.execute(query, {'limit': limit})

            popular = []
            for row in result:
                popular.append({
                    'id': str(row[0]),
                    'name': row[1],
                    'slug': row[2],
                    'category': row[3],
                    'usage_count': row[4]
                })

            return popular

        except Exception as e:
            logger.error(f"Failed to get popular tags: {str(e)}", exc_info=True)
            return []

    # ==================== Tag Association Methods ====================

    def add_tag_to_content(
        self,
        content_type: str,
        content_id: str,
        tag_id: str,
        confidence_score: Optional[float] = None,
        is_auto_tagged: bool = False,
        tagged_by: Optional[str] = None
    ) -> bool:
        """
        Associate a tag with content
        """
        try:
            if content_type == 'chapter':
                table = 'chapter_tags'
                id_column = 'chapter_id'
            elif content_type == 'pdf':
                table = 'pdf_tags'
                id_column = 'pdf_id'
            else:
                logger.error(f"Invalid content type: {content_type}")
                return False

            query = text(f"""
                INSERT INTO {table} (
                    {id_column}, tag_id, confidence_score,
                    is_auto_tagged, tagged_by
                )
                VALUES (
                    :content_id, :tag_id, :confidence_score,
                    :is_auto_tagged, :tagged_by
                )
                ON CONFLICT ({id_column}, tag_id) DO UPDATE SET
                    confidence_score = EXCLUDED.confidence_score,
                    is_auto_tagged = EXCLUDED.is_auto_tagged
            """)

            self.db.execute(query, {
                'content_id': content_id,
                'tag_id': tag_id,
                'confidence_score': confidence_score,
                'is_auto_tagged': is_auto_tagged,
                'tagged_by': tagged_by
            })

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add tag to content: {str(e)}", exc_info=True)
            return False

    def remove_tag_from_content(
        self,
        content_type: str,
        content_id: str,
        tag_id: str
    ) -> bool:
        """
        Remove tag association from content
        """
        try:
            if content_type == 'chapter':
                table = 'chapter_tags'
                id_column = 'chapter_id'
            elif content_type == 'pdf':
                table = 'pdf_tags'
                id_column = 'pdf_id'
            else:
                return False

            query = text(f"""
                DELETE FROM {table}
                WHERE {id_column} = :content_id AND tag_id = :tag_id
            """)

            self.db.execute(query, {
                'content_id': content_id,
                'tag_id': tag_id
            })

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to remove tag: {str(e)}", exc_info=True)
            return False

    def get_content_tags(
        self,
        content_type: str,
        content_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all tags for a specific content item
        """
        try:
            if content_type == 'chapter':
                table = 'chapter_tags'
                id_column = 'chapter_id'
            elif content_type == 'pdf':
                table = 'pdf_tags'
                id_column = 'pdf_id'
            else:
                return []

            query = text(f"""
                SELECT
                    t.id, t.name, t.slug, t.category, t.color,
                    ct.confidence_score, ct.is_auto_tagged, ct.created_at
                FROM tags t
                JOIN {table} ct ON ct.tag_id = t.id
                WHERE ct.{id_column} = :content_id
                ORDER BY ct.confidence_score DESC NULLS LAST, t.name ASC
            """)

            result = self.db.execute(query, {'content_id': content_id})

            tags = []
            for row in result:
                tags.append({
                    'id': str(row[0]),
                    'name': row[1],
                    'slug': row[2],
                    'category': row[3],
                    'color': row[4],
                    'confidence': float(row[5]) if row[5] else None,
                    'is_auto_tagged': row[6],
                    'added_at': row[7].isoformat() if row[7] else None
                })

            return tags

        except Exception as e:
            logger.error(f"Failed to get content tags: {str(e)}", exc_info=True)
            return []

    # ==================== Utility Methods ====================

    def _generate_slug(self, name: str) -> str:
        """
        Generate URL-friendly slug from tag name
        """
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug

    def search_tags(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search tags by name
        """
        try:
            sql_query = text("""
                SELECT id, name, slug, category, color, usage_count
                FROM tags
                WHERE name ILIKE :query OR slug ILIKE :query
                ORDER BY usage_count DESC, name ASC
                LIMIT :limit
            """)

            result = self.db.execute(sql_query, {
                'query': f'%{query}%',
                'limit': limit
            })

            tags = []
            for row in result:
                tags.append({
                    'id': str(row[0]),
                    'name': row[1],
                    'slug': row[2],
                    'category': row[3],
                    'color': row[4],
                    'usage_count': row[5]
                })

            return tags

        except Exception as e:
            logger.error(f"Failed to search tags: {str(e)}", exc_info=True)
            return []

    def get_tag_statistics(self) -> Dict[str, Any]:
        """
        Get overall tag statistics
        """
        try:
            query = text("""
                SELECT
                    COUNT(*) as total_tags,
                    COUNT(CASE WHEN is_auto_generated THEN 1 END) as auto_generated_count,
                    SUM(usage_count) as total_usage,
                    AVG(usage_count) as avg_usage
                FROM tags
            """)

            result = self.db.execute(query)
            row = result.fetchone()

            return {
                'total_tags': row[0],
                'auto_generated_count': row[1],
                'manual_count': row[0] - row[1],
                'total_usage': row[2],
                'avg_usage_per_tag': float(row[3]) if row[3] else 0
            }

        except Exception as e:
            logger.error(f"Failed to get tag statistics: {str(e)}", exc_info=True)
            return {}
