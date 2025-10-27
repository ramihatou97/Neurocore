"""
Content Template Service for Phase 18: Advanced Content Features
Manages reusable content templates for chapter generation
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from backend.utils import get_logger

logger = get_logger(__name__)


class ContentTemplateService:
    """
    Content template management service

    Features:
    - Create and manage reusable templates
    - System and user templates
    - Template sections with validation
    - Usage tracking and statistics
    - Template sharing
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== Template Management ====================

    def create_template(
        self,
        user_id: str,
        name: str,
        template_type: str,
        structure: Dict[str, Any],
        description: Optional[str] = None,
        is_public: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Create new content template

        Args:
            user_id: Creator user ID
            name: Template name
            template_type: Type (surgical_disease, anatomy, technique, case_study, custom)
            structure: Template structure with sections
            description: Template description
            is_public: Make template publicly available

        Returns:
            Created template dict
        """
        try:
            query = text("""
                INSERT INTO content_templates (
                    name, description, template_type, structure,
                    is_public, created_by
                )
                VALUES (
                    :name, :description, :template_type, :structure::jsonb,
                    :is_public, :created_by
                )
                RETURNING id, name, template_type, created_at
            """)

            result = self.db.execute(query, {
                'name': name,
                'description': description,
                'template_type': template_type,
                'structure': json.dumps(structure),
                'is_public': is_public,
                'created_by': user_id
            })

            self.db.commit()
            row = result.fetchone()

            if row:
                # Create template sections
                if 'sections' in structure:
                    for section in structure['sections']:
                        self._create_template_section(
                            template_id=str(row[0]),
                            section_name=section.get('name'),
                            section_order=section.get('order', 0),
                            is_required=section.get('required', True),
                            placeholder_text=section.get('placeholder'),
                            validation_rules=section.get('validation')
                        )

                return {
                    'id': str(row[0]),
                    'name': row[1],
                    'template_type': row[2],
                    'structure': structure,
                    'created_at': row[3].isoformat()
                }

            return None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create template: {str(e)}")
            return None

    def _create_template_section(
        self,
        template_id: str,
        section_name: str,
        section_order: int,
        is_required: bool = True,
        placeholder_text: Optional[str] = None,
        validation_rules: Optional[Dict] = None
    ):
        """Create template section"""
        try:
            query = text("""
                INSERT INTO template_sections (
                    template_id, section_name, section_order,
                    is_required, placeholder_text, validation_rules
                )
                VALUES (
                    :template_id, :section_name, :section_order,
                    :is_required, :placeholder_text, :validation_rules::jsonb
                )
            """)

            self.db.execute(query, {
                'template_id': template_id,
                'section_name': section_name,
                'section_order': section_order,
                'is_required': is_required,
                'placeholder_text': placeholder_text,
                'validation_rules': json.dumps(validation_rules) if validation_rules else None
            })

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create template section: {str(e)}")

    def get_template(self, template_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get template by ID"""
        try:
            query = text("""
                SELECT
                    t.id, t.name, t.description, t.template_type,
                    t.structure, t.is_public, t.is_system,
                    t.usage_count, t.created_by, t.created_at
                FROM content_templates t
                WHERE t.id = :template_id
                    AND (t.is_public = TRUE OR t.is_system = TRUE OR t.created_by = :user_id)
            """)

            result = self.db.execute(query, {
                'template_id': template_id,
                'user_id': user_id
            })

            row = result.fetchone()
            if not row:
                return None

            # Get sections
            sections = self._get_template_sections(template_id)

            return {
                'id': str(row[0]),
                'name': row[1],
                'description': row[2],
                'template_type': row[3],
                'structure': row[4],
                'is_public': row[5],
                'is_system': row[6],
                'usage_count': row[7],
                'created_by': str(row[8]) if row[8] else None,
                'created_at': row[9].isoformat() if row[9] else None,
                'sections': sections
            }

        except Exception as e:
            logger.error(f"Failed to get template: {str(e)}")
            return None

    def _get_template_sections(self, template_id: str) -> List[Dict[str, Any]]:
        """Get template sections"""
        try:
            query = text("""
                SELECT
                    id, section_name, section_order, is_required,
                    placeholder_text, validation_rules
                FROM template_sections
                WHERE template_id = :template_id
                ORDER BY section_order
            """)

            result = self.db.execute(query, {'template_id': template_id})

            return [
                {
                    'id': str(row[0]),
                    'name': row[1],
                    'order': row[2],
                    'required': row[3],
                    'placeholder': row[4],
                    'validation': row[5]
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get template sections: {str(e)}")
            return []

    def list_templates(
        self,
        user_id: Optional[str] = None,
        template_type: Optional[str] = None,
        include_public: bool = True,
        include_system: bool = True
    ) -> List[Dict[str, Any]]:
        """List available templates"""
        try:
            conditions = []
            params = {}

            if user_id:
                conditions.append("(t.created_by = :user_id OR t.is_public = TRUE OR t.is_system = TRUE)")
                params['user_id'] = user_id
            else:
                if include_public:
                    conditions.append("t.is_public = TRUE")
                if include_system:
                    conditions.append("t.is_system = TRUE")

            if template_type:
                conditions.append("t.template_type = :template_type")
                params['template_type'] = template_type

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = text(f"""
                SELECT
                    t.id, t.name, t.description, t.template_type,
                    t.is_public, t.is_system, t.usage_count,
                    t.created_by, t.created_at
                FROM content_templates t
                WHERE {where_clause}
                ORDER BY t.is_system DESC, t.usage_count DESC, t.created_at DESC
            """)

            result = self.db.execute(query, params)

            return [
                {
                    'id': str(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'template_type': row[3],
                    'is_public': row[4],
                    'is_system': row[5],
                    'usage_count': row[6],
                    'created_by': str(row[7]) if row[7] else None,
                    'created_at': row[8].isoformat() if row[8] else None
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to list templates: {str(e)}")
            return []

    def apply_template(
        self,
        user_id: str,
        template_id: str,
        chapter_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply template to create or update content

        Args:
            user_id: User applying template
            template_id: Template to apply
            chapter_id: Optional existing chapter to update

        Returns:
            Template content structure
        """
        try:
            # Get template
            template = self.get_template(template_id, user_id)
            if not template:
                return {'error': 'Template not found'}

            # Track usage
            self._track_template_usage(user_id, template_id, chapter_id)

            # Return template structure for application
            return {
                'template_id': template_id,
                'template_name': template['name'],
                'structure': template['structure'],
                'sections': template['sections']
            }

        except Exception as e:
            logger.error(f"Failed to apply template: {str(e)}")
            return {'error': str(e)}

    def _track_template_usage(
        self,
        user_id: str,
        template_id: str,
        chapter_id: Optional[str] = None
    ):
        """Track template usage"""
        try:
            query = text("""
                INSERT INTO template_usage (template_id, user_id, chapter_id)
                VALUES (:template_id, :user_id, :chapter_id)
            """)

            self.db.execute(query, {
                'template_id': template_id,
                'user_id': user_id,
                'chapter_id': chapter_id
            })

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to track template usage: {str(e)}")

    def update_template(
        self,
        template_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update template"""
        try:
            # Check permissions
            template = self.get_template(template_id, user_id)
            if not template or (template['created_by'] != user_id and not template['is_system']):
                return False

            update_fields = []
            params = {'template_id': template_id}

            if 'name' in updates:
                update_fields.append("name = :name")
                params['name'] = updates['name']

            if 'description' in updates:
                update_fields.append("description = :description")
                params['description'] = updates['description']

            if 'structure' in updates:
                update_fields.append("structure = :structure::jsonb")
                params['structure'] = json.dumps(updates['structure'])

            if 'is_public' in updates:
                update_fields.append("is_public = :is_public")
                params['is_public'] = updates['is_public']

            if not update_fields:
                return True

            query = text(f"""
                UPDATE content_templates
                SET {', '.join(update_fields)}, updated_at = NOW()
                WHERE id = :template_id
            """)

            self.db.execute(query, params)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update template: {str(e)}")
            return False

    def delete_template(self, template_id: str, user_id: str) -> bool:
        """Delete template (only creator can delete)"""
        try:
            query = text("""
                DELETE FROM content_templates
                WHERE id = :template_id AND created_by = :user_id AND is_system = FALSE
            """)

            result = self.db.execute(query, {
                'template_id': template_id,
                'user_id': user_id
            })

            self.db.commit()

            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete template: {str(e)}")
            return False

    def get_template_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get template usage statistics"""
        try:
            conditions = []
            params = {}

            if user_id:
                conditions.append("t.created_by = :user_id")
                params['user_id'] = user_id

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = text(f"""
                SELECT
                    COUNT(*) as total_templates,
                    COUNT(*) FILTER (WHERE t.is_public = TRUE) as public_templates,
                    SUM(t.usage_count) as total_usage,
                    AVG(t.usage_count) as avg_usage_per_template,
                    MAX(t.usage_count) as max_usage
                FROM content_templates t
                {where_clause}
            """)

            result = self.db.execute(query, params)
            row = result.fetchone()

            return {
                'total_templates': row[0] or 0,
                'public_templates': row[1] or 0,
                'total_usage': row[2] or 0,
                'avg_usage_per_template': float(row[3]) if row[3] else 0.0,
                'max_usage': row[4] or 0
            }

        except Exception as e:
            logger.error(f"Failed to get template statistics: {str(e)}")
            return {}
