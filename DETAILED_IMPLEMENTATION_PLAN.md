# Meticulous Implementation & Integration Plan
**Neurocore Image Enhancement System**  
**Date:** November 3, 2025  
**Version:** 1.0 - Detailed Implementation Plan  
**Status:** Ready for Implementation

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Pre-Implementation Assessment](#pre-implementation-assessment)
3. [Phase 1: Anatomical View Classification](#phase-1-anatomical-view-classification)
4. [Phase 2: Structured Annotation Parsing](#phase-2-structured-annotation-parsing)
5. [Phase 3: Multi-View Grouping & 360° Reconstruction](#phase-3-multi-view-grouping--360-reconstruction)
6. [Phase 4: External Image Search Integration](#phase-4-external-image-search-integration)
7. [Phase 5: Coverage Gap Detection](#phase-5-coverage-gap-detection)
8. [Phase 6: Integration & Testing](#phase-6-integration--testing)
9. [Phase 7: Production Deployment](#phase-7-production-deployment)
10. [Risk Management & Mitigation](#risk-management--mitigation)
11. [Success Metrics & KPIs](#success-metrics--kpis)
12. [Timeline & Resource Allocation](#timeline--resource-allocation)

---

## 🎯 Executive Summary

### Objective
Enhance the Neurocore image integration system to support comprehensive 360° anatomical reconstruction with intelligent view classification, annotation parsing, external image augmentation, and coverage validation.

### Current State
- **System Health:** 95-98% production-ready
- **Image Processing:** 24-field AI analysis operational
- **Search Accuracy:** 0.90-0.98 similarity
- **Safety:** Verified duplicate protection (mark-only)

### Target State
- **View Classification:** Automatic anatomical perspective detection
- **Annotation Intelligence:** Structured label-to-structure mapping
- **360° Reconstruction:** Automatic multi-view grouping
- **External Augmentation:** Radiopaedia & Open-i integration
- **Coverage Validation:** Automated completeness checking

### Investment
- **Timeline:** 5-6 weeks (30 working days)
- **Cost:** Minimal (~$50-100 for testing, free tier APIs)
- **Team:** 1 senior developer + 1 reviewer
- **ROI:** High - transforms educational value

---

## 🔍 Pre-Implementation Assessment

### Phase 0: Environment Setup & Validation (Days 1-2)

#### Day 1 Morning: Environment Verification

**Task 0.1: Validate Current System State**

```bash
# 1. Check Docker containers
cd /home/runner/work/Neurocore/Neurocore
docker-compose ps

# Expected: 8 services running (7/8 minimum)
# - neurocore-postgres (healthy)
# - neurocore-redis (healthy)
# - neurocore-api (Up)
# - neurocore-frontend (Up)
# - neurocore-celery-worker (Up)
# - neurocore-celery-worker-embeddings (Up)
# - neurocore-celery-worker-images (Up)
# - neurocore-celery-flower (optional)

# 2. Verify database schema
docker-compose exec postgres psql -U postgres -d neurocore -c "\dt"

# Expected: 47 tables including 'images' table

# 3. Check existing image data
docker-compose exec postgres psql -U postgres -d neurocore -c "
    SELECT COUNT(*) as total_images,
           COUNT(embedding) as with_embeddings,
           COUNT(DISTINCT image_type) as image_types,
           AVG(quality_score) as avg_quality,
           AVG(confidence_score) as avg_confidence
    FROM images;
"

# 4. Test AI provider access
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('OpenAI Key:', 'SET' if os.getenv('OPENAI_API_KEY') else 'MISSING')
print('Anthropic Key:', 'SET' if os.getenv('ANTHROPIC_API_KEY') else 'MISSING')
print('Google Key:', 'SET' if os.getenv('GOOGLE_API_KEY') else 'MISSING')
"
```

**Success Criteria:**
- ✅ All critical containers running
- ✅ Database has 47 tables
- ✅ Images table populated with test data
- ✅ AI provider keys configured

**Deliverable:** `PRE_IMPLEMENTATION_CHECKLIST.md`

---

#### Day 1 Afternoon: Code Review & Documentation

**Task 0.2: Deep Code Analysis**

Files to review in detail:

1. **Image Models & Database**
   - `backend/database/models/image.py` (262 lines)
   - Review all 24 fields, understand relationships
   - Document current capabilities

2. **Image Services**
   - `backend/services/image_analysis_service.py` (~400 lines)
   - `backend/services/image_recommendation_service.py` (~300 lines)
   - `backend/services/image_duplicate_detection_service.py` (~250 lines)
   - Understand current algorithms

3. **Chapter Orchestrator - Image Integration**
   - `backend/services/chapter_orchestrator.py` (lines 1221-1336)
   - Study `_stage_7_image_integration()`
   - Study `_match_images_to_content()` (lines 2516-2606)
   - Study `_generate_image_caption()` (lines 2608+)

4. **API Routes**
   - `backend/api/image_routes.py` (385 lines)
   - Document all endpoints
   - Test with Postman/curl

**Action Items:**
```python
# Create comprehensive code map
code_map = {
    "models": ["Image model with 24 fields"],
    "services": [
        "ImageAnalysisService - Claude Vision integration",
        "ImageRecommendationService - Vector similarity search",
        "ImageDuplicateDetectionService - Duplicate marking"
    ],
    "orchestrator": [
        "Stage 7 - Semantic image integration",
        "Image-to-section matching algorithm",
        "Contextual caption generation"
    ],
    "api": [
        "GET /api/images/{id}/recommendations",
        "POST /api/images/recommendations/by-query",
        "POST /api/images/duplicates/detect",
        "GET /api/images/duplicates/stats"
    ]
}
```

**Deliverable:** `CODE_ANALYSIS_REPORT.md`

---

#### Day 2: Test Data Preparation

**Task 0.3: Create Comprehensive Test Dataset**

```python
# backend/tests/fixtures/test_images.py

import pytest
from pathlib import Path

@pytest.fixture
def lumbar_anatomy_test_images():
    """
    Test dataset for lumbar anatomy with multiple views
    
    Structure:
    - 5 anterior views
    - 5 posterior views
    - 4 lateral left views
    - 4 lateral right views
    - 10 axial slices (L1-L5, 2 each)
    - 5 sagittal views
    Total: 33 images
    """
    return {
        "anterior": [
            {
                "id": "test_img_001",
                "file_path": "/test_data/lumbar/anterior_01.png",
                "description": "Anterior view of lumbar spine L1-L5 with labeled vertebrae",
                "anatomical_structures": ["L1 vertebra", "L2 vertebra", "L3 vertebra", "L4 vertebra", "L5 vertebra"],
                "image_type": "anatomical_diagram",
                "quality_score": 0.9,
                "confidence_score": 0.95
            },
            # ... 4 more anterior views
        ],
        "posterior": [
            # ... 5 posterior views
        ],
        "lateral_left": [
            # ... 4 lateral left views
        ],
        "lateral_right": [
            # ... 4 lateral right views
        ],
        "axial": {
            "L1": [
                # ... 2 axial slices at L1 level
            ],
            "L2": [
                # ... 2 axial slices at L2 level
            ],
            # ... L3, L4, L5
        },
        "sagittal": [
            # ... 5 sagittal views
        ]
    }

@pytest.fixture
def brain_anatomy_test_images():
    """Test dataset for brain anatomy"""
    # Similar structure for brain
    pass

@pytest.fixture
def knee_anatomy_test_images():
    """Test dataset for knee anatomy"""
    # Similar structure for knee
    pass
```

**Test Data Sources:**
1. Use existing processed images from database
2. Add synthetic test images (simple diagrams)
3. Download CC-licensed images from Radiopaedia (with attribution)

**Action:**
```bash
# Create test data directory
mkdir -p tests/fixtures/test_images/lumbar_spine/{anterior,posterior,lateral_left,lateral_right,axial,sagittal}
mkdir -p tests/fixtures/test_images/brain/{axial,sagittal,coronal}
mkdir -p tests/fixtures/test_images/knee/{anterior,posterior,lateral,axial}

# Generate simple test diagrams using Python PIL
python3 scripts/generate_test_images.py
```

**Deliverable:** 
- `tests/fixtures/test_images/` directory with 50+ test images
- `tests/fixtures/test_images.py` with fixtures
- `TEST_DATA_DOCUMENTATION.md`

---

## 🎨 Phase 1: Anatomical View Classification

**Duration:** Days 3-5 (3 days)  
**Priority:** ⭐⭐⭐ Critical  
**Dependencies:** Phase 0 complete

### Day 3: Database Schema Enhancement

#### Task 1.1: Database Migration

**File:** `backend/database/migrations/014_add_anatomical_view_classification.sql`

```sql
-- Migration 014: Add Anatomical View Classification
-- Date: 2025-11-03
-- Purpose: Enable automatic classification of anatomical views and perspectives

BEGIN;

-- Add new columns to images table
ALTER TABLE images 
ADD COLUMN IF NOT EXISTS anatomical_view VARCHAR(50),
ADD COLUMN IF NOT EXISTS anatomical_region VARCHAR(100),
ADD COLUMN IF NOT EXISTS anatomical_plane VARCHAR(30),
ADD COLUMN IF NOT EXISTS view_confidence FLOAT,
ADD COLUMN IF NOT EXISTS view_metadata JSONB;

-- Add indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_images_anatomical_view 
    ON images(anatomical_view) WHERE anatomical_view IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_images_anatomical_region 
    ON images(anatomical_region) WHERE anatomical_region IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_images_anatomical_plane 
    ON images(anatomical_plane) WHERE anatomical_plane IS NOT NULL;

-- Create composite index for multi-view queries
CREATE INDEX IF NOT EXISTS idx_images_region_view 
    ON images(anatomical_region, anatomical_view) 
    WHERE anatomical_region IS NOT NULL AND anatomical_view IS NOT NULL;

-- Add comments
COMMENT ON COLUMN images.anatomical_view IS 
    'View perspective: anterior, posterior, lateral_left, lateral_right, superior, inferior, oblique, etc.';

COMMENT ON COLUMN images.anatomical_region IS 
    'Anatomical region: lumbar_spine, cervical_spine, brain, knee, shoulder, etc.';

COMMENT ON COLUMN images.anatomical_plane IS 
    'Imaging plane: axial, sagittal, coronal, oblique';

COMMENT ON COLUMN images.view_confidence IS 
    'AI confidence in view classification (0.0-1.0)';

COMMENT ON COLUMN images.view_metadata IS 
    'Additional view metadata: angle, slice level, landmarks visible, etc.';

-- Create enum-like constraint for common views (advisory, not enforced)
-- This serves as documentation for expected values
CREATE TABLE IF NOT EXISTS anatomical_view_types (
    view_type VARCHAR(50) PRIMARY KEY,
    description TEXT,
    typical_regions TEXT[]
);

INSERT INTO anatomical_view_types (view_type, description, typical_regions) VALUES
    ('anterior', 'Front view of anatomical structure', ARRAY['spine', 'body', 'limbs']),
    ('posterior', 'Back view of anatomical structure', ARRAY['spine', 'body', 'limbs']),
    ('lateral_left', 'Left side view', ARRAY['spine', 'head', 'limbs']),
    ('lateral_right', 'Right side view', ARRAY['spine', 'head', 'limbs']),
    ('superior', 'Top-down view', ARRAY['spine', 'organs']),
    ('inferior', 'Bottom-up view', ARRAY['spine', 'organs']),
    ('medial', 'Toward midline view', ARRAY['limbs', 'organs']),
    ('lateral', 'Away from midline view', ARRAY['limbs', 'organs']),
    ('axial', 'Horizontal cross-section', ARRAY['all']),
    ('sagittal', 'Vertical midline plane', ARRAY['all']),
    ('coronal', 'Vertical frontal plane', ARRAY['all']),
    ('oblique', 'Angled view', ARRAY['all']),
    ('ap', 'Anterior-posterior radiograph', ARRAY['all']),
    ('pa', 'Posterior-anterior radiograph', ARRAY['all']),
    ('3d_reconstruction', '3D rendered view', ARRAY['all'])
ON CONFLICT (view_type) DO NOTHING;

COMMIT;
```

**Apply Migration:**
```bash
# Test migration on development database
docker-compose exec postgres psql -U postgres -d neurocore -f backend/database/migrations/014_add_anatomical_view_classification.sql

# Verify columns added
docker-compose exec postgres psql -U postgres -d neurocore -c "\d images"
```

**Rollback Plan:**
```sql
-- rollback_014.sql
BEGIN;
ALTER TABLE images 
    DROP COLUMN IF EXISTS anatomical_view,
    DROP COLUMN IF EXISTS anatomical_region,
    DROP COLUMN IF EXISTS anatomical_plane,
    DROP COLUMN IF EXISTS view_confidence,
    DROP COLUMN IF EXISTS view_metadata;
DROP INDEX IF EXISTS idx_images_anatomical_view;
DROP INDEX IF EXISTS idx_images_anatomical_region;
DROP INDEX IF EXISTS idx_images_anatomical_plane;
DROP INDEX IF EXISTS idx_images_region_view;
DROP TABLE IF EXISTS anatomical_view_types;
COMMIT;
```

---

#### Task 1.2: Update Image Model

**File:** `backend/database/models/image.py`

**Changes:**
```python
# Add after line 132 (after confidence_score)

# ==================== Anatomical View Classification (NEW) ====================

anatomical_view: Mapped[Optional[str]] = mapped_column(
    String(50),
    nullable=True,
    index=True,
    comment="View perspective: anterior, posterior, lateral_left, lateral_right, superior, inferior, axial, sagittal, coronal, oblique, etc."
)

anatomical_region: Mapped[Optional[str]] = mapped_column(
    String(100),
    nullable=True,
    index=True,
    comment="Anatomical region: lumbar_spine, cervical_spine, thoracic_spine, brain, knee, shoulder, etc."
)

anatomical_plane: Mapped[Optional[str]] = mapped_column(
    String(30),
    nullable=True,
    comment="Imaging plane: axial, sagittal, coronal, oblique"
)

view_confidence: Mapped[Optional[float]] = mapped_column(
    Float,
    nullable=True,
    comment="AI confidence in view classification (0.0-1.0)"
)

view_metadata: Mapped[Optional[dict]] = mapped_column(
    JSON,
    nullable=True,
    comment="Additional view metadata: angle, slice level, landmarks visible, etc."
)
```

**Update `to_dict()` method:**
```python
# Add after "ai_analysis" section in to_dict() method (around line 240)

"anatomical_classification": {
    "view": self.anatomical_view,
    "region": self.anatomical_region,
    "plane": self.anatomical_plane,
    "view_confidence": self.view_confidence,
    "view_metadata": self.view_metadata
},
```

**Add helper methods:**
```python
# Add at end of Image class (after line 262)

def is_view_classified(self) -> bool:
    """Check if image has anatomical view classification"""
    return self.anatomical_view is not None and self.view_confidence is not None

def is_spinal_anatomy(self) -> bool:
    """Check if image shows spinal anatomy"""
    if not self.anatomical_region:
        return False
    return any(term in self.anatomical_region.lower() 
               for term in ['spine', 'vertebra', 'spinal', 'lumbar', 'cervical', 'thoracic', 'sacral'])

def get_view_label(self) -> str:
    """Get human-readable view label"""
    if not self.anatomical_view:
        return "Unclassified"
    
    view_labels = {
        "anterior": "Anterior View",
        "posterior": "Posterior View",
        "lateral_left": "Left Lateral View",
        "lateral_right": "Right Lateral View",
        "superior": "Superior View",
        "inferior": "Inferior View",
        "axial": "Axial (Horizontal) Section",
        "sagittal": "Sagittal (Midline) Section",
        "coronal": "Coronal (Frontal) Section",
        "oblique": "Oblique View",
        "3d_reconstruction": "3D Reconstruction"
    }
    return view_labels.get(self.anatomical_view, self.anatomical_view.replace("_", " ").title())
```

---

### Day 4: View Classification Service

#### Task 1.3: Create View Classification Service

**File:** `backend/services/anatomical_view_classifier.py` (NEW)

```python
"""
Anatomical View Classification Service
Automatically classifies medical images by anatomical view and perspective
"""

from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
import re

from backend.services.ai_provider_service import AIProviderService, AITask
from backend.database.models import Image
from backend.utils import get_logger

logger = get_logger(__name__)


class AnatomicalViewClassifier:
    """
    Service for classifying anatomical views in medical images
    
    Capabilities:
    - Automatic view detection (anterior, posterior, lateral, etc.)
    - Anatomical region identification (lumbar spine, brain, knee, etc.)
    - Imaging plane detection (axial, sagittal, coronal)
    - Confidence scoring
    - Batch processing
    """
    
    # Standard view types by category
    STANDARD_VIEWS = {
        "surface": ["anterior", "posterior", "lateral_left", "lateral_right", "superior", "inferior", "medial"],
        "sectional": ["axial", "sagittal", "coronal", "oblique"],
        "radiographic": ["ap", "pa", "lateral"],
        "special": ["3d_reconstruction", "endoscopic", "microscopic"]
    }
    
    # Standard anatomical regions
    ANATOMICAL_REGIONS = {
        "spine": ["cervical_spine", "thoracic_spine", "lumbar_spine", "sacral_spine", "coccygeal_spine"],
        "head": ["brain", "skull", "face", "orbit", "temporal_bone"],
        "trunk": ["chest", "abdomen", "pelvis", "thorax"],
        "limbs": ["shoulder", "elbow", "wrist", "hand", "hip", "knee", "ankle", "foot"]
    }
    
    def __init__(self, db_session: Session = None):
        """
        Initialize view classifier
        
        Args:
            db_session: Optional database session for batch operations
        """
        self.db = db_session
        self.ai_service = AIProviderService()
    
    async def classify_view(
        self,
        image: Image,
        use_ai: bool = True,
        use_heuristics: bool = True
    ) -> Dict[str, Any]:
        """
        Classify anatomical view of an image
        
        Args:
            image: Image object to classify
            use_ai: Whether to use AI (Claude Vision) for classification
            use_heuristics: Whether to use rule-based heuristics first
        
        Returns:
            Classification results with confidence scores
        """
        logger.info(f"Classifying view for image {image.id}")
        
        # Try heuristics first (fast, no API cost)
        if use_heuristics:
            heuristic_result = self._classify_by_heuristics(image)
            if heuristic_result and heuristic_result.get("confidence", 0) >= 0.8:
                logger.info(f"High-confidence heuristic classification: {heuristic_result['view']}")
                return heuristic_result
        
        # Use AI for more accurate classification
        if use_ai:
            ai_result = await self._classify_by_ai(image)
            
            # Merge with heuristic result if available
            if use_heuristics and heuristic_result:
                # Use AI for view, heuristics for region if more confident
                if heuristic_result.get("region_confidence", 0) > ai_result.get("region_confidence", 0):
                    ai_result["region"] = heuristic_result["region"]
                    ai_result["region_confidence"] = heuristic_result["region_confidence"]
            
            return ai_result
        
        # Fallback to heuristics only
        return heuristic_result or self._default_classification()
    
    def _classify_by_heuristics(self, image: Image) -> Optional[Dict[str, Any]]:
        """
        Classify view using rule-based heuristics
        
        Uses:
        - Image description keywords
        - OCR text
        - Anatomical structures list
        - Existing image metadata
        
        Returns:
            Classification dict or None if uncertain
        """
        result = {
            "view": None,
            "region": None,
            "plane": None,
            "confidence": 0.0,
            "region_confidence": 0.0,
            "method": "heuristic"
        }
        
        # Gather all text sources
        text_sources = []
        if image.ai_description:
            text_sources.append(image.ai_description.lower())
        if image.caption:
            text_sources.append(image.caption.lower())
        if image.ocr_text:
            text_sources.append(image.ocr_text.lower())
        if image.anatomical_structures:
            text_sources.append(" ".join(image.anatomical_structures).lower())
        
        combined_text = " ".join(text_sources)
        
        if not combined_text:
            return None
        
        # View detection patterns
        view_patterns = {
            "anterior": ["anterior", "front", "frontal", "ventral"],
            "posterior": ["posterior", "back", "dorsal"],
            "lateral_left": ["left lateral", "lateral left", "left side"],
            "lateral_right": ["right lateral", "lateral right", "right side"],
            "lateral": ["lateral side", "side view"],
            "superior": ["superior", "top", "cranial", "cephalic"],
            "inferior": ["inferior", "bottom", "caudal"],
            "axial": ["axial", "transverse", "horizontal section", "cross section"],
            "sagittal": ["sagittal", "midline", "median"],
            "coronal": ["coronal", "frontal plane"],
            "oblique": ["oblique", "angled"],
            "ap": ["anteroposterior", "ap view", "ap projection"],
            "pa": ["posteroanterior", "pa view", "pa projection"],
            "3d_reconstruction": ["3d", "three-dimensional", "reconstruction", "rendered"]
        }
        
        # Find best matching view
        best_view = None
        best_score = 0.0
        
        for view, patterns in view_patterns.items():
            score = sum(1 for pattern in patterns if pattern in combined_text)
            if score > best_score:
                best_score = score
                best_view = view
        
        if best_view:
            result["view"] = best_view
            result["confidence"] = min(0.5 + (best_score * 0.1), 0.9)  # Cap at 0.9 for heuristics
        
        # Region detection patterns
        region_patterns = {
            "lumbar_spine": ["lumbar", "l1", "l2", "l3", "l4", "l5", "lumbar vertebra"],
            "cervical_spine": ["cervical", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "cervical vertebra"],
            "thoracic_spine": ["thoracic", "t1", "t2", "t3", "t4", "t5", "thoracic vertebra"],
            "sacral_spine": ["sacral", "sacrum", "s1", "s2"],
            "brain": ["brain", "cerebral", "cerebellum", "brainstem", "cortex"],
            "knee": ["knee", "patella", "femur", "tibia", "meniscus"],
            "shoulder": ["shoulder", "scapula", "clavicle", "humerus", "glenohumeral"],
            "spine": ["spine", "spinal", "vertebra", "vertebral"]
        }
        
        # Find best matching region
        best_region = None
        best_region_score = 0.0
        
        for region, patterns in region_patterns.items():
            score = sum(1 for pattern in patterns if pattern in combined_text)
            if score > best_region_score:
                best_region_score = score
                best_region = region
        
        if best_region:
            result["region"] = best_region
            result["region_confidence"] = min(0.5 + (best_region_score * 0.1), 0.9)
        
        # Determine plane from view
        if result["view"] in ["axial"]:
            result["plane"] = "axial"
        elif result["view"] in ["sagittal"]:
            result["plane"] = "sagittal"
        elif result["view"] in ["coronal"]:
            result["plane"] = "coronal"
        elif result["view"] in ["oblique"]:
            result["plane"] = "oblique"
        
        # Only return if we found something
        if result["view"] or result["region"]:
            return result
        
        return None
    
    async def _classify_by_ai(self, image: Image) -> Dict[str, Any]:
        """
        Classify view using AI (Claude Vision)
        
        Args:
            image: Image to classify
        
        Returns:
            Classification results from AI
        """
        # Build comprehensive prompt
        prompt = self._build_classification_prompt(image)
        
        try:
            # Call AI service
            response = await self.ai_service.analyze_image_with_vision(
                image_path=image.file_path,
                prompt=prompt,
                task=AITask.IMAGE_ANALYSIS
            )
            
            # Parse response
            classification = self._parse_ai_response(response)
            classification["method"] = "ai"
            
            return classification
            
        except Exception as e:
            logger.error(f"AI classification failed for image {image.id}: {e}")
            return self._default_classification()
    
    def _build_classification_prompt(self, image: Image) -> str:
        """Build detailed prompt for AI classification"""
        
        # Get existing analysis if available
        context = ""
        if image.ai_description:
            context += f"\nExisting Description: {image.ai_description}"
        if image.anatomical_structures:
            context += f"\nStructures Visible: {', '.join(image.anatomical_structures)}"
        
        prompt = f"""Analyze this medical image and classify its anatomical view and perspective.

{context}

Provide a detailed classification including:

1. **Anatomical View/Perspective**: Identify the specific view (e.g., anterior, posterior, lateral left, lateral right, superior, inferior, axial, sagittal, coronal, oblique, AP, PA, 3D reconstruction)

2. **Anatomical Region**: Identify the body region shown (e.g., lumbar spine, cervical spine, brain, knee, shoulder, etc.). Be as specific as possible.

3. **Imaging Plane** (if applicable): For cross-sectional imaging, specify the plane (axial, sagittal, coronal, oblique)

4. **Confidence Levels**: Rate your confidence in each classification (0.0-1.0)

5. **Additional Metadata**:
   - For spinal images: Identify vertebral levels visible (e.g., L1-L5)
   - For cross-sections: Identify slice level or landmarks
   - For oblique views: Describe the angle
   - Any laterality (left/right side)

Return your analysis in this exact JSON format:
{{
    "view": "anterior" | "posterior" | "lateral_left" | "lateral_right" | "superior" | "inferior" | "axial" | "sagittal" | "coronal" | "oblique" | "ap" | "pa" | "3d_reconstruction",
    "region": "lumbar_spine" | "cervical_spine" | "brain" | "knee" | etc.,
    "plane": "axial" | "sagittal" | "coronal" | "oblique" | null,
    "confidence": 0.95,
    "region_confidence": 0.90,
    "metadata": {{
        "vertebral_levels": ["L1", "L2", "L3", "L4", "L5"],
        "slice_level": "L3",
        "laterality": "bilateral",
        "angle_description": "30-degree oblique",
        "landmarks": ["spinous process", "transverse process"]
    }}
}}

Be precise and use medical terminology. If uncertain, provide your best assessment with appropriate confidence scores."""
        
        return prompt
    
    def _parse_ai_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse AI response into standardized format
        
        Args:
            response: Raw AI response
        
        Returns:
            Parsed classification dict
        """
        # AI service returns structured data
        data = response.get("data", {})
        
        # Handle both direct JSON and text response
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI response as JSON, using defaults")
                return self._default_classification()
        
        return {
            "view": data.get("view"),
            "region": data.get("region"),
            "plane": data.get("plane"),
            "confidence": float(data.get("confidence", 0.0)),
            "region_confidence": float(data.get("region_confidence", 0.0)),
            "metadata": data.get("metadata", {}),
            "method": "ai"
        }
    
    def _default_classification(self) -> Dict[str, Any]:
        """Return default classification when all methods fail"""
        return {
            "view": None,
            "region": None,
            "plane": None,
            "confidence": 0.0,
            "region_confidence": 0.0,
            "metadata": {},
            "method": "none"
        }
    
    async def classify_batch(
        self,
        images: List[Image],
        use_ai: bool = True,
        use_heuristics: bool = True,
        save_to_db: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple images in batch
        
        Args:
            images: List of images to classify
            use_ai: Whether to use AI for classification
            use_heuristics: Whether to use heuristics first
            save_to_db: Whether to save results to database
        
        Returns:
            List of classification results
        """
        logger.info(f"Classifying {len(images)} images in batch")
        
        results = []
        for i, image in enumerate(images):
            logger.info(f"Processing image {i+1}/{len(images)}: {image.id}")
            
            classification = await self.classify_view(
                image=image,
                use_ai=use_ai,
                use_heuristics=use_heuristics
            )
            
            results.append({
                "image_id": str(image.id),
                **classification
            })
            
            # Save to database if requested
            if save_to_db and self.db:
                image.anatomical_view = classification.get("view")
                image.anatomical_region = classification.get("region")
                image.anatomical_plane = classification.get("plane")
                image.view_confidence = classification.get("confidence")
                image.view_metadata = classification.get("metadata")
                self.db.commit()
                
                logger.info(
                    f"Saved classification for image {image.id}: "
                    f"{classification.get('view')} / {classification.get('region')}"
                )
        
        logger.info(f"Batch classification complete: {len(results)} images processed")
        return results
    
    def get_classification_stats(self, images: List[Image]) -> Dict[str, Any]:
        """
        Get statistics on view classifications
        
        Args:
            images: List of images to analyze
        
        Returns:
            Statistics dict
        """
        stats = {
            "total_images": len(images),
            "classified": 0,
            "unclassified": 0,
            "views": {},
            "regions": {},
            "planes": {},
            "avg_confidence": 0.0,
            "high_confidence": 0,  # >= 0.8
            "medium_confidence": 0,  # 0.5-0.8
            "low_confidence": 0  # < 0.5
        }
        
        confidence_sum = 0.0
        
        for image in images:
            if image.anatomical_view:
                stats["classified"] += 1
                
                # Count views
                view = image.anatomical_view
                stats["views"][view] = stats["views"].get(view, 0) + 1
                
                # Count regions
                if image.anatomical_region:
                    region = image.anatomical_region
                    stats["regions"][region] = stats["regions"].get(region, 0) + 1
                
                # Count planes
                if image.anatomical_plane:
                    plane = image.anatomical_plane
                    stats["planes"][plane] = stats["planes"].get(plane, 0) + 1
                
                # Confidence stats
                if image.view_confidence:
                    confidence_sum += image.view_confidence
                    if image.view_confidence >= 0.8:
                        stats["high_confidence"] += 1
                    elif image.view_confidence >= 0.5:
                        stats["medium_confidence"] += 1
                    else:
                        stats["low_confidence"] += 1
            else:
                stats["unclassified"] += 1
        
        if stats["classified"] > 0:
            stats["avg_confidence"] = confidence_sum / stats["classified"]
        
        return stats
```

---

### Day 5: Testing & Integration

#### Task 1.4: Unit Tests

**File:** `backend/tests/unit/test_anatomical_view_classifier.py` (NEW)

```python
"""
Unit tests for Anatomical View Classifier
"""

import pytest
from unittest.mock import Mock, patch
from backend.services.anatomical_view_classifier import AnatomicalViewClassifier
from backend.database.models import Image


class TestAnatomicalViewClassifier:
    """Test suite for view classification"""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier instance"""
        return AnatomicalViewClassifier(db_session=None)
    
    @pytest.fixture
    def lumbar_anterior_image(self):
        """Mock image with lumbar anterior view"""
        image = Mock(spec=Image)
        image.id = "test_001"
        image.file_path = "/test/lumbar_anterior.png"
        image.ai_description = "Anterior view of lumbar spine showing L1-L5 vertebrae with clear labeling"
        image.caption = "Figure 3.1: Anterior lumbar spine anatomy"
        image.ocr_text = "L1 L2 L3 L4 L5 Anterior View"
        image.anatomical_structures = ["L1 vertebra", "L2 vertebra", "L3 vertebra", "L4 vertebra", "L5 vertebra"]
        return image
    
    def test_heuristic_classification_lumbar_anterior(self, classifier, lumbar_anterior_image):
        """Test heuristic classification of lumbar anterior view"""
        result = classifier._classify_by_heuristics(lumbar_anterior_image)
        
        assert result is not None
        assert result["view"] == "anterior"
        assert result["region"] == "lumbar_spine"
        assert result["confidence"] > 0.5
        assert result["region_confidence"] > 0.5
        assert result["method"] == "heuristic"
    
    def test_heuristic_classification_brain_axial(self, classifier):
        """Test heuristic classification of brain axial section"""
        image = Mock(spec=Image)
        image.id = "test_002"
        image.ai_description = "Axial MRI section of brain at level of lateral ventricles"
        image.caption = "Axial brain MRI"
        image.ocr_text = "Axial section Brain"
        image.anatomical_structures = ["cerebral cortex", "lateral ventricles"]
        
        result = classifier._classify_by_heuristics(image)
        
        assert result is not None
        assert result["view"] == "axial"
        assert result["region"] == "brain"
        assert result["plane"] == "axial"
    
    def test_heuristic_classification_no_data(self, classifier):
        """Test heuristic classification with no data"""
        image = Mock(spec=Image)
        image.id = "test_003"
        image.ai_description = None
        image.caption = None
        image.ocr_text = None
        image.anatomical_structures = None
        
        result = classifier._classify_by_heuristics(image)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_classify_view_with_heuristics_only(self, classifier, lumbar_anterior_image):
        """Test classification using heuristics only"""
        result = await classifier.classify_view(
            image=lumbar_anterior_image,
            use_ai=False,
            use_heuristics=True
        )
        
        assert result["view"] == "anterior"
        assert result["region"] == "lumbar_spine"
        assert result["method"] == "heuristic"
    
    @pytest.mark.asyncio
    @patch('backend.services.anatomical_view_classifier.AIProviderService')
    async def test_classify_view_with_ai(self, mock_ai_service, classifier, lumbar_anterior_image):
        """Test classification using AI"""
        # Mock AI response
        mock_response = {
            "data": {
                "view": "anterior",
                "region": "lumbar_spine",
                "plane": None,
                "confidence": 0.95,
                "region_confidence": 0.92,
                "metadata": {
                    "vertebral_levels": ["L1", "L2", "L3", "L4", "L5"],
                    "laterality": "bilateral"
                }
            }
        }
        
        classifier.ai_service.analyze_image_with_vision = Mock(return_value=mock_response)
        
        result = await classifier.classify_view(
            image=lumbar_anterior_image,
            use_ai=True,
            use_heuristics=False
        )
        
        assert result["view"] == "anterior"
        assert result["region"] == "lumbar_spine"
        assert result["confidence"] == 0.95
        assert result["method"] == "ai"
        assert "vertebral_levels" in result["metadata"]
    
    @pytest.mark.asyncio
    async def test_classify_batch(self, classifier):
        """Test batch classification"""
        images = [
            Mock(spec=Image, id=f"test_{i}", 
                 ai_description=f"Anterior view of lumbar spine",
                 caption="Lumbar anterior",
                 ocr_text="L1 L2 L3 L4 L5",
                 anatomical_structures=["L1 vertebra"])
            for i in range(5)
        ]
        
        results = await classifier.classify_batch(
            images=images,
            use_ai=False,
            use_heuristics=True,
            save_to_db=False
        )
        
        assert len(results) == 5
        for result in results:
            assert "image_id" in result
            assert "view" in result
            assert "region" in result
    
    def test_get_classification_stats(self, classifier):
        """Test classification statistics"""
        images = [
            Mock(spec=Image, anatomical_view="anterior", anatomical_region="lumbar_spine", 
                 anatomical_plane=None, view_confidence=0.9),
            Mock(spec=Image, anatomical_view="posterior", anatomical_region="lumbar_spine",
                 anatomical_plane=None, view_confidence=0.85),
            Mock(spec=Image, anatomical_view="axial", anatomical_region="brain",
                 anatomical_plane="axial", view_confidence=0.75),
            Mock(spec=Image, anatomical_view=None, anatomical_region=None,
                 anatomical_plane=None, view_confidence=None)
        ]
        
        stats = classifier.get_classification_stats(images)
        
        assert stats["total_images"] == 4
        assert stats["classified"] == 3
        assert stats["unclassified"] == 1
        assert stats["views"]["anterior"] == 1
        assert stats["views"]["posterior"] == 1
        assert stats["views"]["axial"] == 1
        assert stats["regions"]["lumbar_spine"] == 2
        assert stats["regions"]["brain"] == 1
        assert stats["high_confidence"] == 2  # 0.9 and 0.85
        assert stats["medium_confidence"] == 1  # 0.75
        assert 0.8 < stats["avg_confidence"] < 0.9
```

**Run Tests:**
```bash
pytest backend/tests/unit/test_anatomical_view_classifier.py -v
```

---

#### Task 1.5: Integration Script

**File:** `backend/scripts/classify_existing_images.py` (NEW)

```python
"""
Script to classify existing images with anatomical views
Run this after Phase 1 implementation to classify all existing images
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config.settings import settings
from backend.database.models import Image
from backend.services.anatomical_view_classifier import AnatomicalViewClassifier
from backend.utils import get_logger

logger = get_logger(__name__)


async def classify_all_images(
    use_ai: bool = True,
    use_heuristics: bool = True,
    batch_size: int = 10,
    limit: int = None
):
    """
    Classify all existing images in database
    
    Args:
        use_ai: Whether to use AI classification
        use_heuristics: Whether to use heuristic classification
        batch_size: Number of images to process at once
        limit: Maximum number of images to process (None = all)
    """
    # Create database session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Get images without classification
        query = db.query(Image).filter(
            Image.anatomical_view.is_(None)
        )
        
        if limit:
            query = query.limit(limit)
        
        images = query.all()
        
        logger.info(f"Found {len(images)} images to classify")
        
        if not images:
            logger.info("No unclassified images found. Exiting.")
            return
        
        # Create classifier
        classifier = AnatomicalViewClassifier(db_session=db)
        
        # Process in batches
        total_processed = 0
        total_classified = 0
        
        for i in range(0, len(images), batch_size):
            batch = images[i:i+batch_size]
            logger.info(f"\nProcessing batch {i//batch_size + 1}: images {i+1} to {min(i+batch_size, len(images))}")
            
            results = await classifier.classify_batch(
                images=batch,
                use_ai=use_ai,
                use_heuristics=use_heuristics,
                save_to_db=True
            )
            
            # Count successful classifications
            for result in results:
                total_processed += 1
                if result.get("view"):
                    total_classified += 1
            
            logger.info(f"Batch complete: {len([r for r in results if r.get('view')])} classified")
        
        # Get final statistics
        stats = classifier.get_classification_stats(images)
        
        logger.info("\n" + "="*60)
        logger.info("CLASSIFICATION COMPLETE")
        logger.info("="*60)
        logger.info(f"Total images processed: {total_processed}")
        logger.info(f"Successfully classified: {total_classified}")
        logger.info(f"Classification rate: {total_classified/total_processed*100:.1f}%")
        logger.info(f"\nViews found:")
        for view, count in stats["views"].items():
            logger.info(f"  {view}: {count}")
        logger.info(f"\nRegions found:")
        for region, count in stats["regions"].items():
            logger.info(f"  {region}: {count}")
        logger.info(f"\nAverage confidence: {stats['avg_confidence']:.2f}")
        logger.info(f"High confidence (>=0.8): {stats['high_confidence']}")
        logger.info(f"Medium confidence (0.5-0.8): {stats['medium_confidence']}")
        logger.info(f"Low confidence (<0.5): {stats['low_confidence']}")
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Classify existing images with anatomical views")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI classification (heuristics only)")
    parser.add_argument("--no-heuristics", action="store_true", help="Disable heuristic classification (AI only)")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for processing")
    parser.add_argument("--limit", type=int, default=None, help="Maximum images to process")
    
    args = parser.parse_args()
    
    asyncio.run(classify_all_images(
        use_ai=not args.no_ai,
        use_heuristics=not args.no_heuristics,
        batch_size=args.batch_size,
        limit=args.limit
    ))
```

**Run Script:**
```bash
# Test with small batch first
python3 backend/scripts/classify_existing_images.py --limit 10

# Run on all images (use heuristics first for speed)
python3 backend/scripts/classify_existing_images.py --batch-size 20

# Run with AI only (more accurate but slower/costlier)
python3 backend/scripts/classify_existing_images.py --no-heuristics --batch-size 5
```

---

**Phase 1 Deliverables:**
- ✅ Database migration applied
- ✅ Image model updated with new fields
- ✅ AnatomicalViewClassifier service created
- ✅ Unit tests written and passing
- ✅ Integration script for existing images
- ✅ Documentation updated

**Phase 1 Success Criteria:**
- All tests passing
- Existing images classified (>80% success rate)
- Average confidence >0.7
- API endpoints working with new fields

---

## 🏗️ Phase 2: Structured Annotation Parsing

**Duration:** Days 6-10 (5 days)  
**Priority:** ⭐⭐⭐ Critical  
**Dependencies:** Phase 1 complete

### Overview
Implement deep annotation parsing to extract and structure anatomical labels, linking them to identified structures with spatial relationships.

### Day 6-7: Enhanced OCR & Label Extraction

[... Detailed implementation plan continues for each phase ...]

---

**Due to length constraints, I'll create this as a comprehensive document.**

Let me complete this implementation plan document with all phases detailed.

