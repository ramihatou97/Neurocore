# Complete Implementation Plan - Phases 2-5 & Additional Enhancements
**Neurocore Image Enhancement System - Extended Documentation**  
**Date:** November 3, 2025  
**Version:** 2.0 - Complete Implementation Specification

---

## 📋 Table of Contents

1. [Phase 2: Structured Annotation Parsing](#phase-2-structured-annotation-parsing)
2. [Phase 3: Multi-View Grouping & 360° Reconstruction](#phase-3-multi-view-grouping--360-reconstruction)
3. [Phase 4: External Image Search Integration](#phase-4-external-image-search-integration)
4. [Phase 5: Coverage Gap Detection](#phase-5-coverage-gap-detection)
5. [Additional Enhancements](#additional-enhancements)
6. [Integration Workflow](#integration-workflow)
7. [Testing Strategy](#testing-strategy)
8. [Deployment Plan](#deployment-plan)

---

## 🏗️ Phase 2: Structured Annotation Parsing

**Duration:** Days 6-10 (5 days)  
**Priority:** ⭐⭐⭐ Critical  
**Dependencies:** Phase 1 complete

### Day 6 Morning: Database Schema for Annotations

#### Task 2.1: Create Annotation Tables

**File:** `backend/database/migrations/015_add_annotation_structures.sql`

```sql
-- Migration 015: Add Structured Annotation Tables
-- Date: 2025-11-03
-- Purpose: Store parsed annotations with spatial relationships

BEGIN;

-- Main annotation table
CREATE TABLE IF NOT EXISTS image_annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    
    -- Label information
    label_text TEXT NOT NULL,
    label_position JSONB,  -- {x, y, width, height}
    
    -- Structure information
    structure_name TEXT,
    structure_type TEXT,  -- 'bone', 'muscle', 'nerve', 'vessel', 'organ'
    confidence FLOAT,
    
    -- Spatial metadata
    has_leader_line BOOLEAN DEFAULT FALSE,
    leader_line_coords JSONB,  -- Array of points [{x, y}, ...]
    points_to_coords JSONB,  -- Where the label points to
    
    -- Relationships
    parent_structure_id UUID REFERENCES image_annotations(id),
    
    -- AI analysis
    parsed_by VARCHAR(50),  -- 'ocr', 'claude_vision', 'hybrid'
    verification_status VARCHAR(20) DEFAULT 'unverified',  -- 'unverified', 'verified', 'corrected'
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Spatial relationships table
CREATE TABLE IF NOT EXISTS anatomical_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    
    -- Relationship between two structures
    structure_a_id UUID NOT NULL REFERENCES image_annotations(id) ON DELETE CASCADE,
    structure_b_id UUID NOT NULL REFERENCES image_annotations(id) ON DELETE CASCADE,
    
    -- Relationship type
    relationship_type VARCHAR(50) NOT NULL,  -- 'superior_to', 'inferior_to', 'medial_to', 'lateral_to', 'anterior_to', 'posterior_to'
    confidence FLOAT,
    
    -- Distance/proximity
    approximate_distance_px INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_relationship UNIQUE (structure_a_id, structure_b_id, relationship_type)
);

-- Annotation groups (for related annotations)
CREATE TABLE IF NOT EXISTS annotation_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    group_name TEXT,  -- e.g., "Lumbar Vertebrae", "Cranial Nerves"
    group_type VARCHAR(50),  -- 'anatomical_system', 'region', 'custom'
    annotations_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Many-to-many relationship
CREATE TABLE IF NOT EXISTS annotation_group_members (
    group_id UUID NOT NULL REFERENCES annotation_groups(id) ON DELETE CASCADE,
    annotation_id UUID NOT NULL REFERENCES image_annotations(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, annotation_id)
);

-- Indexes for performance
CREATE INDEX idx_annotations_image ON image_annotations(image_id);
CREATE INDEX idx_annotations_structure ON image_annotations(structure_name);
CREATE INDEX idx_annotations_type ON image_annotations(structure_type);
CREATE INDEX idx_relationships_image ON anatomical_relationships(image_id);
CREATE INDEX idx_relationships_type ON anatomical_relationships(relationship_type);
CREATE INDEX idx_annotation_groups_image ON annotation_groups(image_id);

-- Full-text search on labels
CREATE INDEX idx_annotations_label_text ON image_annotations USING gin(to_tsvector('english', label_text));
CREATE INDEX idx_annotations_structure_name ON image_annotations USING gin(to_tsvector('english', structure_name));

-- Comments
COMMENT ON TABLE image_annotations IS 'Structured annotations extracted from medical images';
COMMENT ON TABLE anatomical_relationships IS 'Spatial relationships between anatomical structures';
COMMENT ON TABLE annotation_groups IS 'Logical grouping of related annotations';

COMMIT;
```

**Apply Migration:**
```bash
docker-compose exec postgres psql -U postgres -d neurocore -f backend/database/migrations/015_add_annotation_structures.sql

# Verify
docker-compose exec postgres psql -U postgres -d neurocore -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE '%annotation%' OR table_name LIKE '%relationship%';
"
```

---

#### Task 2.2: Create Annotation Models

**File:** `backend/database/models/annotation.py` (NEW)

```python
"""
Annotation models for structured label and relationship data
"""

from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, Dict, Any
import uuid

from backend.database.base import Base, UUIDMixin, TimestampMixin


class ImageAnnotation(Base, UUIDMixin, TimestampMixin):
    """
    Structured annotation extracted from medical image
    
    Represents a single label/annotation with its spatial information
    and connection to anatomical structures
    """
    
    __tablename__ = "image_annotations"
    
    # Source image
    image_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('images.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Label information
    label_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Original text from label"
    )
    
    label_position: Mapped[Optional[Dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Position on image: {x, y, width, height}"
    )
    
    # Structure information
    structure_name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        index=True,
        comment="Standardized anatomical structure name"
    )
    
    structure_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Type: bone, muscle, nerve, vessel, organ, etc."
    )
    
    confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Confidence in structure identification (0.0-1.0)"
    )
    
    # Spatial metadata
    has_leader_line: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether label has a leader line pointing to structure"
    )
    
    leader_line_coords: Mapped[Optional[Dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Coordinates of leader line: [{x, y}, ...]"
    )
    
    points_to_coords: Mapped[Optional[Dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Coordinates where label points to: {x, y}"
    )
    
    # Hierarchical relationships
    parent_structure_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('image_annotations.id', ondelete='SET NULL'),
        nullable=True,
        comment="Parent structure for hierarchical anatomy"
    )
    
    # Parsing metadata
    parsed_by: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Method used: ocr, claude_vision, hybrid"
    )
    
    verification_status: Mapped[str] = mapped_column(
        String(20),
        default='unverified',
        comment="Verification status: unverified, verified, corrected"
    )
    
    # Relationships
    image: Mapped["Image"] = relationship(
        "Image",
        back_populates="annotations"
    )
    
    parent_structure: Mapped[Optional["ImageAnnotation"]] = relationship(
        "ImageAnnotation",
        remote_side="ImageAnnotation.id",
        foreign_keys=[parent_structure_id],
        back_populates="child_structures"
    )
    
    child_structures: Mapped[List["ImageAnnotation"]] = relationship(
        "ImageAnnotation",
        back_populates="parent_structure",
        foreign_keys="ImageAnnotation.parent_structure_id"
    )
    
    spatial_relationships_from: Mapped[List["AnatomicalRelationship"]] = relationship(
        "AnatomicalRelationship",
        foreign_keys="AnatomicalRelationship.structure_a_id",
        back_populates="structure_a"
    )
    
    spatial_relationships_to: Mapped[List["AnatomicalRelationship"]] = relationship(
        "AnatomicalRelationship",
        foreign_keys="AnatomicalRelationship.structure_b_id",
        back_populates="structure_b"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "image_id": str(self.image_id),
            "label_text": self.label_text,
            "label_position": self.label_position,
            "structure_name": self.structure_name,
            "structure_type": self.structure_type,
            "confidence": self.confidence,
            "has_leader_line": self.has_leader_line,
            "leader_line_coords": self.leader_line_coords,
            "points_to_coords": self.points_to_coords,
            "parent_structure_id": str(self.parent_structure_id) if self.parent_structure_id else None,
            "parsed_by": self.parsed_by,
            "verification_status": self.verification_status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class AnatomicalRelationship(Base, UUIDMixin):
    """
    Spatial relationship between two anatomical structures
    
    Represents directional relationships like:
    - superior_to / inferior_to (above/below)
    - medial_to / lateral_to (toward/away from midline)
    - anterior_to / posterior_to (front/back)
    """
    
    __tablename__ = "anatomical_relationships"
    
    image_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('images.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    structure_a_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('image_annotations.id', ondelete='CASCADE'),
        nullable=False
    )
    
    structure_b_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('image_annotations.id', ondelete='CASCADE'),
        nullable=False
    )
    
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: superior_to, inferior_to, medial_to, lateral_to, anterior_to, posterior_to"
    )
    
    confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Confidence in relationship (0.0-1.0)"
    )
    
    approximate_distance_px: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Approximate pixel distance between structures"
    )
    
    created_at: Mapped[Any] = mapped_column(
        nullable=False,
        default="NOW()"
    )
    
    # Relationships
    image: Mapped["Image"] = relationship("Image")
    
    structure_a: Mapped["ImageAnnotation"] = relationship(
        "ImageAnnotation",
        foreign_keys=[structure_a_id],
        back_populates="spatial_relationships_from"
    )
    
    structure_b: Mapped["ImageAnnotation"] = relationship(
        "ImageAnnotation",
        foreign_keys=[structure_b_id],
        back_populates="spatial_relationships_to"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "image_id": str(self.image_id),
            "structure_a_id": str(self.structure_a_id),
            "structure_b_id": str(self.structure_b_id),
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "approximate_distance_px": self.approximate_distance_px,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else str(self.created_at)
        }


class AnnotationGroup(Base, UUIDMixin, TimestampMixin):
    """
    Logical grouping of related annotations
    
    Groups annotations by anatomical system, region, or custom criteria
    """
    
    __tablename__ = "annotation_groups"
    
    image_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('images.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    group_name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Name of the group"
    )
    
    group_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Type: anatomical_system, region, custom"
    )
    
    annotations_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of annotations in group"
    )
    
    # Relationships
    image: Mapped["Image"] = relationship("Image")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "image_id": str(self.image_id),
            "group_name": self.group_name,
            "group_type": self.group_type,
            "annotations_count": self.annotations_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
```

**Update Image Model:**

Add to `backend/database/models/image.py`:
```python
# Add to relationships section (around line 210)
annotations: Mapped[List["ImageAnnotation"]] = relationship(
    "ImageAnnotation",
    back_populates="image",
    cascade="all, delete-orphan"
)
```

---

### Day 6 Afternoon - Day 7: Annotation Parser Service

#### Task 2.3: Create Annotation Parser

**File:** `backend/services/annotation_parser.py` (NEW, ~650 lines)

```python
"""
Annotation Parser Service
Extracts and structures anatomical labels from medical images
"""

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
import re
from pathlib import Path

from backend.services.ai_provider_service import AIProviderService, AITask
from backend.database.models import Image, ImageAnnotation, AnatomicalRelationship
from backend.utils import get_logger

logger = get_logger(__name__)


class AnnotationParser:
    """
    Service for parsing and structuring annotations from medical images
    
    Capabilities:
    - Enhanced OCR with position tracking
    - Label-to-structure matching
    - Spatial relationship detection
    - Hierarchical structure building
    """
    
    # Anatomical structure types
    STRUCTURE_TYPES = {
        "bone": ["vertebra", "bone", "skull", "femur", "tibia", "humerus", "radius", "ulna"],
        "muscle": ["muscle", "muscular", "flexor", "extensor", "abductor", "adductor"],
        "nerve": ["nerve", "plexus", "ganglion", "root", "cord"],
        "vessel": ["artery", "vein", "vascular", "aorta", "vena cava"],
        "organ": ["brain", "heart", "liver", "kidney", "lung", "spleen"],
        "ligament": ["ligament", "tendon", "ligamentum"],
        "space": ["space", "cavity", "foramen", "canal", "fossa"]
    }
    
    # Standardized anatomical terms
    ANATOMICAL_TERMS = {
        "l1": "L1 vertebra",
        "l2": "L2 vertebra",
        "l3": "L3 vertebra",
        "l4": "L4 vertebra",
        "l5": "L5 vertebra",
        "c1": "C1 vertebra (Atlas)",
        "c2": "C2 vertebra (Axis)",
        # ... more mappings
    }
    
    def __init__(self, db_session: Session):
        """Initialize parser"""
        self.db = db_session
        self.ai_service = AIProviderService()
    
    async def parse_annotations(
        self,
        image: Image,
        use_ocr: bool = True,
        use_ai: bool = True,
        extract_relationships: bool = True
    ) -> Dict[str, Any]:
        """
        Parse all annotations from an image
        
        Args:
            image: Image object to parse
            use_ocr: Whether to use OCR for text extraction
            use_ai: Whether to use AI for structure matching
            extract_relationships: Whether to extract spatial relationships
        
        Returns:
            Parsing results with annotations and relationships
        """
        logger.info(f"Parsing annotations for image {image.id}")
        
        results = {
            "image_id": str(image.id),
            "annotations": [],
            "relationships": [],
            "parsing_method": []
        }
        
        # Step 1: Extract text with positions using OCR
        if use_ocr:
            ocr_annotations = await self._extract_ocr_annotations(image)
            results["annotations"].extend(ocr_annotations)
            results["parsing_method"].append("ocr")
            logger.info(f"OCR extracted {len(ocr_annotations)} annotations")
        
        # Step 2: Use AI to enhance and match structures
        if use_ai:
            ai_annotations = await self._ai_enhance_annotations(
                image,
                existing_annotations=results["annotations"]
            )
            results["annotations"] = ai_annotations
            results["parsing_method"].append("ai_enhanced")
            logger.info(f"AI enhanced to {len(ai_annotations)} annotations")
        
        # Step 3: Extract spatial relationships
        if extract_relationships and results["annotations"]:
            relationships = await self._extract_relationships(
                image,
                annotations=results["annotations"]
            )
            results["relationships"] = relationships
            logger.info(f"Extracted {len(relationships)} spatial relationships")
        
        # Step 4: Save to database
        if results["annotations"]:
            saved = await self._save_annotations(image, results)
            logger.info(f"Saved {saved['annotations_saved']} annotations and {saved['relationships_saved']} relationships")
        
        return results
    
    async def _extract_ocr_annotations(self, image: Image) -> List[Dict[str, Any]]:
        """
        Extract text annotations using enhanced OCR with positions
        
        Uses EasyOCR for position tracking
        """
        annotations = []
        
        try:
            import easyocr
            
            # Initialize reader
            reader = easyocr.Reader(['en'])
            
            # Perform OCR with position detection
            ocr_results = reader.readtext(image.file_path, detail=1)
            
            for idx, (bbox, text, confidence) in enumerate(ocr_results):
                # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                # Convert to x, y, width, height
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                
                x = min(x_coords)
                y = min(y_coords)
                width = max(x_coords) - x
                height = max(y_coords) - y
                
                # Clean text
                text_clean = text.strip()
                
                if len(text_clean) > 1:  # Skip single characters
                    annotation = {
                        "label_text": text_clean,
                        "label_position": {
                            "x": float(x),
                            "y": float(y),
                            "width": float(width),
                            "height": float(height)
                        },
                        "confidence": float(confidence),
                        "parsed_by": "ocr"
                    }
                    annotations.append(annotation)
        
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            # Fallback to existing OCR text if available
            if image.ocr_text:
                # Split by lines and create annotations without positions
                lines = image.ocr_text.split('\n')
                for line in lines:
                    if line.strip():
                        annotations.append({
                            "label_text": line.strip(),
                            "label_position": None,
                            "confidence": 0.5,
                            "parsed_by": "ocr_fallback"
                        })
        
        return annotations
    
    async def _ai_enhance_annotations(
        self,
        image: Image,
        existing_annotations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use AI to enhance annotations with structure matching
        
        Uses Claude Vision to:
        1. Identify anatomical structures
        2. Match labels to structures
        3. Detect leader lines
        4. Standardize terminology
        """
        prompt = self._build_enhancement_prompt(image, existing_annotations)
        
        try:
            response = await self.ai_service.analyze_image_with_vision(
                image_path=image.file_path,
                prompt=prompt,
                task=AITask.IMAGE_ANALYSIS
            )
            
            # Parse AI response
            enhanced_annotations = self._parse_ai_enhancement(
                response,
                existing_annotations
            )
            
            return enhanced_annotations
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            return existing_annotations
    
    def _build_enhancement_prompt(
        self,
        image: Image,
        annotations: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for AI enhancement"""
        
        labels_text = "\n".join([f"- {a['label_text']}" for a in annotations])
        
        prompt = f"""Analyze this medical image and enhance the extracted annotations.

Image Type: {image.image_type or 'Unknown'}
Anatomical Region: {image.anatomical_region or 'Unknown'}
View: {image.anatomical_view or 'Unknown'}

Extracted Labels (from OCR):
{labels_text}

Your task:
1. **Identify all anatomical structures** visible in the image
2. **Match each label** to its corresponding structure
3. **Standardize terminology** (e.g., "L1" → "L1 vertebra")
4. **Detect leader lines** - which labels have lines pointing to structures?
5. **Classify structure types** (bone, muscle, nerve, vessel, organ, etc.)
6. **Identify hierarchical relationships** (e.g., "L3 vertebra" is part of "Lumbar spine")

Return a JSON array with this structure:
[
    {{
        "label_text": "L1",
        "structure_name": "L1 vertebra",
        "structure_type": "bone",
        "confidence": 0.95,
        "has_leader_line": true,
        "points_to_coords": {{"x": 250, "y": 300}},
        "parent_structure": "Lumbar spine"
    }},
    ...
]

Be thorough and precise. Include all visible structures even if not explicitly labeled."""
        
        return prompt
    
    def _parse_ai_enhancement(
        self,
        response: Dict[str, Any],
        existing_annotations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parse AI enhancement response"""
        import json
        
        data = response.get("data", {})
        
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                return existing_annotations
        
        if not isinstance(data, list):
            return existing_annotations
        
        enhanced = []
        for item in data:
            annotation = {
                "label_text": item.get("label_text", ""),
                "structure_name": item.get("structure_name"),
                "structure_type": item.get("structure_type"),
                "confidence": item.get("confidence", 0.5),
                "has_leader_line": item.get("has_leader_line", False),
                "points_to_coords": item.get("points_to_coords"),
                "parent_structure_name": item.get("parent_structure"),
                "parsed_by": "ai_enhanced"
            }
            
            # Try to match with existing annotation for position
            for existing in existing_annotations:
                if existing["label_text"].lower() in annotation["label_text"].lower():
                    annotation["label_position"] = existing.get("label_position")
                    break
            
            enhanced.append(annotation)
        
        return enhanced
    
    async def _extract_relationships(
        self,
        image: Image,
        annotations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract spatial relationships between structures
        
        Determines directional relationships like:
        - superior_to (above)
        - inferior_to (below)
        - medial_to (toward midline)
        - lateral_to (away from midline)
        """
        relationships = []
        
        # Group annotations by having positions
        positioned = [a for a in annotations if a.get("label_position") or a.get("points_to_coords")]
        
        if len(positioned) < 2:
            return relationships
        
        # Compare each pair
        for i, ann_a in enumerate(positioned):
            for ann_b in positioned[i+1:]:
                rel = self._determine_relationship(ann_a, ann_b, image)
                if rel:
                    relationships.append(rel)
        
        return relationships
    
    def _determine_relationship(
        self,
        ann_a: Dict[str, Any],
        ann_b: Dict[str, Any],
        image: Image
    ) -> Optional[Dict[str, Any]]:
        """Determine spatial relationship between two annotations"""
        
        # Get positions
        pos_a = ann_a.get("points_to_coords") or ann_a.get("label_position")
        pos_b = ann_b.get("points_to_coords") or ann_b.get("label_position")
        
        if not pos_a or not pos_b:
            return None
        
        # Extract coordinates
        y_a = pos_a.get("y", 0)
        y_b = pos_b.get("y", 0)
        x_a = pos_a.get("x", 0)
        x_b = pos_b.get("x", 0)
        
        # Calculate differences
        y_diff = y_b - y_a
        x_diff = x_b - x_a
        
        # Threshold for significant difference
        threshold = 20  # pixels
        
        relationships = []
        
        # Vertical relationships (superior/inferior)
        if abs(y_diff) > threshold:
            if y_diff > 0:
                # B is below A
                relationships.append({
                    "structure_a": ann_a.get("structure_name") or ann_a["label_text"],
                    "structure_b": ann_b.get("structure_name") or ann_b["label_text"],
                    "relationship_type": "superior_to",
                    "confidence": 0.8,
                    "approximate_distance_px": int(abs(y_diff))
                })
            else:
                # B is above A
                relationships.append({
                    "structure_a": ann_a.get("structure_name") or ann_a["label_text"],
                    "structure_b": ann_b.get("structure_name") or ann_b["label_text"],
                    "relationship_type": "inferior_to",
                    "confidence": 0.8,
                    "approximate_distance_px": int(abs(y_diff))
                })
        
        # Horizontal relationships (medial/lateral)
        if abs(x_diff) > threshold:
            if x_diff > 0:
                relationships.append({
                    "structure_a": ann_a.get("structure_name") or ann_a["label_text"],
                    "structure_b": ann_b.get("structure_name") or ann_b["label_text"],
                    "relationship_type": "lateral_to",  # Simplified, would need view context
                    "confidence": 0.7,
                    "approximate_distance_px": int(abs(x_diff))
                })
        
        return relationships[0] if relationships else None
    
    async def _save_annotations(
        self,
        image: Image,
        results: Dict[str, Any]
    ) -> Dict[str, int]:
        """Save annotations and relationships to database"""
        
        saved_annotations = 0
        saved_relationships = 0
        annotation_map = {}  # Map label_text to database ID
        
        try:
            # Save annotations
            for ann_data in results["annotations"]:
                annotation = ImageAnnotation(
                    image_id=image.id,
                    label_text=ann_data["label_text"],
                    label_position=ann_data.get("label_position"),
                    structure_name=ann_data.get("structure_name"),
                    structure_type=ann_data.get("structure_type"),
                    confidence=ann_data.get("confidence"),
                    has_leader_line=ann_data.get("has_leader_line", False),
                    points_to_coords=ann_data.get("points_to_coords"),
                    parsed_by=ann_data.get("parsed_by", "unknown"),
                    verification_status='unverified'
                )
                
                self.db.add(annotation)
                self.db.flush()  # Get ID without committing
                
                # Store mapping
                key = ann_data.get("structure_name") or ann_data["label_text"]
                annotation_map[key] = annotation.id
                
                saved_annotations += 1
            
            # Save relationships
            for rel_data in results["relationships"]:
                struct_a = rel_data["structure_a"]
                struct_b = rel_data["structure_b"]
                
                if struct_a in annotation_map and struct_b in annotation_map:
                    relationship = AnatomicalRelationship(
                        image_id=image.id,
                        structure_a_id=annotation_map[struct_a],
                        structure_b_id=annotation_map[struct_b],
                        relationship_type=rel_data["relationship_type"],
                        confidence=rel_data.get("confidence"),
                        approximate_distance_px=rel_data.get("approximate_distance_px")
                    )
                    
                    self.db.add(relationship)
                    saved_relationships += 1
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save annotations: {e}")
        
        return {
            "annotations_saved": saved_annotations,
            "relationships_saved": saved_relationships
        }
    
    def get_annotation_stats(self, image_ids: List[str] = None) -> Dict[str, Any]:
        """Get statistics on annotations"""
        query = self.db.query(ImageAnnotation)
        
        if image_ids:
            query = query.filter(ImageAnnotation.image_id.in_(image_ids))
        
        total = query.count()
        verified = query.filter(ImageAnnotation.verification_status == 'verified').count()
        
        # Structure type distribution
        structure_types = self.db.query(
            ImageAnnotation.structure_type,
            func.count(ImageAnnotation.id)
        ).filter(
            ImageAnnotation.structure_type.isnot(None)
        ).group_by(ImageAnnotation.structure_type).all()
        
        return {
            "total_annotations": total,
            "verified": verified,
            "verification_rate": verified / total if total > 0 else 0,
            "structure_types": dict(structure_types),
            "avg_confidence": self.db.query(func.avg(ImageAnnotation.confidence)).scalar() or 0
        }
```

---

### Day 8-9: API Routes & Testing

#### Task 2.4: Annotation API Routes

**File:** `backend/api/annotation_routes.py` (NEW, ~350 lines)

```python
"""
Annotation API Routes
Endpoints for annotation parsing and retrieval
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.database.connection import get_db
from backend.database.models import Image, ImageAnnotation, AnatomicalRelationship
from backend.services.annotation_parser import AnnotationParser
from backend.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/annotations", tags=["annotations"])


# ==================== REQUEST/RESPONSE MODELS ====================

class ParseAnnotationsRequest(BaseModel):
    """Request model for annotation parsing"""
    use_ocr: bool = Field(default=True, description="Use OCR for text extraction")
    use_ai: bool = Field(default=True, description="Use AI for structure matching")
    extract_relationships: bool = Field(default=True, description="Extract spatial relationships")


# ==================== ENDPOINTS ====================

@router.post("/images/{image_id}/parse")
async def parse_image_annotations(
    image_id: str,
    request: ParseAnnotationsRequest,
    db: Session = Depends(get_db)
):
    """
    Parse annotations from an image
    
    Extracts labels, matches to structures, and determines spatial relationships.
    """
    # Get image
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail=f"Image {image_id} not found")
    
    # Parse annotations
    parser = AnnotationParser(db)
    results = await parser.parse_annotations(
        image=image,
        use_ocr=request.use_ocr,
        use_ai=request.use_ai,
        extract_relationships=request.extract_relationships
    )
    
    return {
        "image_id": image_id,
        "parsing_complete": True,
        **results
    }


@router.get("/images/{image_id}/annotations")
async def get_image_annotations(
    image_id: str,
    include_relationships: bool = Query(default=False),
    db: Session = Depends(get_db)
):
    """Get all annotations for an image"""
    # Verify image exists
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail=f"Image {image_id} not found")
    
    # Get annotations
    annotations = db.query(ImageAnnotation).filter(
        ImageAnnotation.image_id == image_id
    ).all()
    
    result = {
        "image_id": image_id,
        "annotations": [ann.to_dict() for ann in annotations],
        "count": len(annotations)
    }
    
    if include_relationships:
        relationships = db.query(AnatomicalRelationship).filter(
            AnatomicalRelationship.image_id == image_id
        ).all()
        result["relationships"] = [rel.to_dict() for rel in relationships]
        result["relationships_count"] = len(relationships)
    
    return result


@router.get("/search")
async def search_annotations(
    query: str = Query(..., min_length=1),
    structure_type: Optional[str] = None,
    min_confidence: float = Query(default=0.5, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Search annotations by label or structure name
    
    Supports full-text search across labels and structure names.
    """
    from sqlalchemy import or_, func
    
    # Build query
    query_obj = db.query(ImageAnnotation).filter(
        or_(
            func.lower(ImageAnnotation.label_text).contains(query.lower()),
            func.lower(ImageAnnotation.structure_name).contains(query.lower())
        )
    )
    
    # Apply filters
    if structure_type:
        query_obj = query_obj.filter(ImageAnnotation.structure_type == structure_type)
    
    query_obj = query_obj.filter(
        ImageAnnotation.confidence >= min_confidence
    )
    
    # Execute
    results = query_obj.limit(limit).all()
    
    return {
        "query": query,
        "filters": {
            "structure_type": structure_type,
            "min_confidence": min_confidence
        },
        "results": [ann.to_dict() for ann in results],
        "count": len(results)
    }


@router.get("/stats")
async def get_annotation_stats(
    image_ids: Optional[List[str]] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Get annotation statistics"""
    parser = AnnotationParser(db)
    stats = parser.get_annotation_stats(image_ids=image_ids)
    
    return {
        "stats": stats
    }
```

Register in `backend/main.py`:
```python
from backend.api import annotation_routes
app.include_router(annotation_routes.router)
```

---

#### Task 2.5: Unit Tests

**File:** `backend/tests/unit/test_annotation_parser.py` (NEW, ~300 lines)

```python
"""
Unit tests for Annotation Parser
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from backend.services.annotation_parser import AnnotationParser
from backend.database.models import Image, ImageAnnotation


class TestAnnotationParser:
    """Test suite for annotation parsing"""
    
    @pytest.fixture
    def parser(self, mock_db):
        """Create parser instance"""
        return AnnotationParser(db_session=mock_db)
    
    @pytest.fixture
    def test_image(self):
        """Mock image with annotations"""
        image = Mock(spec=Image)
        image.id = "test_001"
        image.file_path = "/test/lumbar_annotated.png"
        image.image_type = "anatomical_diagram"
        image.anatomical_region = "lumbar_spine"
        image.anatomical_view = "lateral"
        image.ocr_text = "L1\nL2\nL3\nL4\nL5\nSpinal cord"
        return image
    
    @pytest.mark.asyncio
    async def test_parse_annotations_ocr_only(self, parser, test_image):
        """Test parsing with OCR only"""
        result = await parser.parse_annotations(
            image=test_image,
            use_ocr=True,
            use_ai=False,
            extract_relationships=False
        )
        
        assert result["image_id"] == "test_001"
        assert len(result["annotations"]) > 0
        assert "ocr" in result["parsing_method"]
        assert len(result["relationships"]) == 0
    
    @pytest.mark.asyncio
    @patch('backend.services.annotation_parser.AIProviderService')
    async def test_ai_enhancement(self, mock_ai, parser, test_image):
        """Test AI enhancement of annotations"""
        # Mock AI response
        mock_response = {
            "data": [
                {
                    "label_text": "L1",
                    "structure_name": "L1 vertebra",
                    "structure_type": "bone",
                    "confidence": 0.95,
                    "has_leader_line": True,
                    "points_to_coords": {"x": 250, "y": 100}
                },
                {
                    "label_text": "L2",
                    "structure_name": "L2 vertebra",
                    "structure_type": "bone",
                    "confidence": 0.93,
                    "has_leader_line": True,
                    "points_to_coords": {"x": 250, "y": 150}
                }
            ]
        }
        
        parser.ai_service.analyze_image_with_vision = AsyncMock(return_value=mock_response)
        
        result = await parser.parse_annotations(
            image=test_image,
            use_ocr=False,
            use_ai=True,
            extract_relationships=True
        )
        
        assert len(result["annotations"]) == 2
        assert result["annotations"][0]["structure_name"] == "L1 vertebra"
        assert result["annotations"][0]["structure_type"] == "bone"
        assert result["annotations"][0]["has_leader_line"] is True
    
    def test_determine_relationship(self, parser, test_image):
        """Test spatial relationship determination"""
        ann_a = {
            "label_text": "L1",
            "structure_name": "L1 vertebra",
            "points_to_coords": {"x": 250, "y": 100}
        }
        
        ann_b = {
            "label_text": "L2",
            "structure_name": "L2 vertebra",
            "points_to_coords": {"x": 250, "y": 150}
        }
        
        rel = parser._determine_relationship(ann_a, ann_b, test_image)
        
        assert rel is not None
        assert rel["relationship_type"] == "superior_to"
        assert rel["structure_a"] == "L1 vertebra"
        assert rel["structure_b"] == "L2 vertebra"
        assert rel["approximate_distance_px"] == 50
    
    def test_get_annotation_stats(self, parser, mock_db):
        """Test annotation statistics"""
        # Mock database queries
        mock_db.query.return_value.count.return_value = 100
        mock_db.query.return_value.filter.return_value.count.return_value = 80
        
        stats = parser.get_annotation_stats()
        
        assert "total_annotations" in stats
        assert "verified" in stats
        assert "verification_rate" in stats
```

Run tests:
```bash
pytest backend/tests/unit/test_annotation_parser.py -v
```

---

### Day 10: Integration & Documentation

#### Task 2.6: Integration Script

**File:** `backend/scripts/parse_all_annotations.py` (NEW)

```python
"""
Script to parse annotations from all images
Run after Phase 2 implementation
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config.settings import settings
from backend.database.models import Image
from backend.services.annotation_parser import AnnotationParser
from backend.utils import get_logger

logger = get_logger(__name__)


async def parse_all_images(
    use_ocr: bool = True,
    use_ai: bool = True,
    batch_size: int = 10,
    limit: int = None
):
    """Parse annotations from all images"""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Get images
        query = db.query(Image)
        
        if limit:
            query = query.limit(limit)
        
        images = query.all()
        logger.info(f"Found {len(images)} images to parse")
        
        parser = AnnotationParser(db_session=db)
        
        total_processed = 0
        total_annotations = 0
        total_relationships = 0
        
        for i in range(0, len(images), batch_size):
            batch = images[i:i+batch_size]
            logger.info(f"\nProcessing batch {i//batch_size + 1}")
            
            for image in batch:
                logger.info(f"Parsing image {image.id}")
                
                result = await parser.parse_annotations(
                    image=image,
                    use_ocr=use_ocr,
                    use_ai=use_ai,
                    extract_relationships=True
                )
                
                total_processed += 1
                total_annotations += len(result["annotations"])
                total_relationships += len(result["relationships"])
        
        # Final stats
        stats = parser.get_annotation_stats()
        
        logger.info("\n" + "="*60)
        logger.info("ANNOTATION PARSING COMPLETE")
        logger.info("="*60)
        logger.info(f"Images processed: {total_processed}")
        logger.info(f"Annotations extracted: {total_annotations}")
        logger.info(f"Relationships found: {total_relationships}")
        logger.info(f"\nFinal Statistics:")
        logger.info(f"  Total annotations in DB: {stats['total_annotations']}")
        logger.info(f"  Verified: {stats['verified']}")
        logger.info(f"  Average confidence: {stats['avg_confidence']:.2f}")
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument("--no-ai", action="store_true")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--limit", type=int, default=None)
    
    args = parser.parse_args()
    
    asyncio.run(parse_all_images(
        use_ocr=not args.no_ocr,
        use_ai=not args.no_ai,
        batch_size=args.batch_size,
        limit=args.limit
    ))
```

**Run:**
```bash
# Test with small batch
python3 backend/scripts/parse_all_annotations.py --limit 5

# Full run
python3 backend/scripts/parse_all_annotations.py --batch-size 20
```

---

**Phase 2 Deliverables:**
- ✅ Database migration with 4 new tables
- ✅ 3 new models (ImageAnnotation, AnatomicalRelationship, AnnotationGroup)
- ✅ AnnotationParser service (~650 lines)
- ✅ API routes for annotations (~350 lines)
- ✅ Unit tests (~300 lines)
- ✅ Integration script
- ✅ Documentation

**Phase 2 Success Criteria:**
- >70% label extraction accuracy
- >60% structure-label matching
- Spatial relationships correctly identified
- API endpoints functional
- Tests passing

---

[Content continues with Phases 3, 4, and 5 in similar detail...]

Due to space constraints, I've provided the complete Phase 2 implementation. The document continues with equally detailed specifications for Phases 3-5 and additional enhancements. Would you like me to continue with the remaining phases?
