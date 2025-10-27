"""
Image Analysis Service with Claude Vision
Analyzes medical images extracted from PDFs using Claude's vision capabilities
"""

from typing import List, Dict, Any, Optional
import base64
from pathlib import Path
from PIL import Image
import io

from backend.services.ai_provider_service import AIProviderService, AITask
from backend.utils import get_logger

logger = get_logger(__name__)


class ImageAnalysisService:
    """
    Service for analyzing medical images using Claude Vision

    Capabilities:
    - Anatomical structure identification
    - Image type classification (MRI, CT, diagram, surgical photo)
    - Clinical significance assessment
    - Quality evaluation
    - Text extraction (OCR for labels)
    - Duplicate detection
    """

    def __init__(self):
        self.ai_service = AIProviderService()

    def _encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 for API transmission

        Args:
            image_path: Path to image file

        Returns:
            Base64 encoded image string
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {str(e)}")
            raise

    def _get_image_info(self, image_path: str) -> Dict[str, Any]:
        """
        Get basic image information (dimensions, format, size)

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with image metadata
        """
        try:
            with Image.open(image_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "size_bytes": Path(image_path).stat().st_size
                }
        except Exception as e:
            logger.error(f"Failed to get image info for {image_path}: {str(e)}")
            return {}

    async def analyze_image(
        self,
        image_path: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single medical image using Claude Vision

        Args:
            image_path: Path to image file
            context: Optional context (PDF title, page number, etc.)

        Returns:
            Comprehensive image analysis
        """
        logger.info(f"Analyzing image: {image_path}")

        # Get basic image info
        image_info = self._get_image_info(image_path)

        # Build analysis prompt
        prompt = self._build_analysis_prompt(context)

        try:
            # Encode image
            image_base64 = self._encode_image(image_path)

            # Call Claude Vision
            result = await self.ai_service.generate_vision_analysis(
                image_base64=image_base64,
                prompt=prompt,
                task=AITask.IMAGE_ANALYSIS
            )

            analysis = self._parse_analysis_result(result["text"])

            # Combine with image info
            return {
                "image_path": image_path,
                "image_info": image_info,
                "analysis": analysis,
                "confidence_score": analysis.get("confidence", 0.0),
                "provider": result["provider"],
                "cost_usd": result["cost_usd"],
                "tokens_used": result["tokens_used"]
            }

        except Exception as e:
            logger.error(f"Image analysis failed for {image_path}: {str(e)}", exc_info=True)
            return {
                "image_path": image_path,
                "image_info": image_info,
                "analysis": None,
                "error": str(e),
                "confidence_score": 0.0
            }

    def _build_analysis_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Build comprehensive analysis prompt for Claude Vision

        Args:
            context: Optional context about the image source

        Returns:
            Structured analysis prompt
        """
        prompt = """You are an expert neurosurgical image analyst. Analyze this medical image and provide a comprehensive assessment.

**Analysis Requirements:**

1. **Image Type Classification:**
   - Determine if this is: MRI, CT, X-ray, angiogram, surgical photograph, anatomical diagram, histology, or other
   - Specify modality details (e.g., T1-weighted MRI, contrast-enhanced CT)

2. **Anatomical Structures:**
   - Identify all visible neuroanatomical structures
   - Note any pathological findings (tumors, hemorrhage, edema, fractures, etc.)
   - Describe anatomical orientation (axial, sagittal, coronal)

3. **Clinical Significance:**
   - Rate clinical relevance (1-10 scale)
   - Describe key findings that would be important for a neurosurgeon
   - Note any emergency/critical findings

4. **Image Quality:**
   - Rate overall quality (1-10 scale)
   - Note: resolution, clarity, contrast, artifacts, labeling quality
   - Assess suitability for educational/reference use

5. **Text Extraction:**
   - Extract any visible text labels, annotations, measurements
   - Extract patient data if visible (de-identify in output)
   - Note figure numbers or captions

6. **Educational Value:**
   - Rate educational value (1-10 scale)
   - Suggest appropriate use cases (teaching, reference, case study)
   - Identify key learning points

**Output Format (JSON):**
```json
{
  "image_type": "string",
  "modality": "string",
  "anatomical_structures": ["structure1", "structure2"],
  "pathology": "string or null",
  "orientation": "string",
  "clinical_significance": {
    "score": 0-10,
    "description": "string",
    "critical_findings": ["finding1", "finding2"] or []
  },
  "quality": {
    "score": 0-10,
    "resolution": "string",
    "clarity": "string",
    "artifacts": ["artifact1"] or [],
    "suitable_for_reference": true/false
  },
  "extracted_text": ["text1", "text2"] or [],
  "educational_value": {
    "score": 0-10,
    "use_cases": ["use1", "use2"],
    "learning_points": ["point1", "point2"]
  },
  "confidence": 0.0-1.0,
  "tags": ["tag1", "tag2", "tag3"]
}
```
"""

        # Add context if provided
        if context:
            prompt += f"\n**Image Context:**\n"
            if "pdf_title" in context:
                prompt += f"- Source PDF: {context['pdf_title']}\n"
            if "page_number" in context:
                prompt += f"- Page: {context['page_number']}\n"
            if "section" in context:
                prompt += f"- Section: {context['section']}\n"

        prompt += "\nProvide your analysis in valid JSON format."

        return prompt

    def _parse_analysis_result(self, result_text: str) -> Dict[str, Any]:
        """
        Parse AI response into structured analysis

        Args:
            result_text: Raw AI response

        Returns:
            Parsed analysis dictionary
        """
        import json

        try:
            # Try to parse as JSON
            if "```json" in result_text:
                # Extract JSON from markdown code block
                start = result_text.find("```json") + 7
                end = result_text.find("```", start)
                json_str = result_text[start:end].strip()
            else:
                json_str = result_text.strip()

            analysis = json.loads(json_str)
            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON analysis: {str(e)}")
            # Return minimal structure
            return {
                "image_type": "unknown",
                "anatomical_structures": [],
                "clinical_significance": {"score": 0, "description": "Parse error"},
                "quality": {"score": 0, "suitable_for_reference": False},
                "educational_value": {"score": 0},
                "confidence": 0.0,
                "tags": [],
                "raw_response": result_text
            }

    async def analyze_images_batch(
        self,
        image_paths: List[str],
        context: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple images concurrently

        Args:
            image_paths: List of image file paths
            context: Optional shared context
            max_concurrent: Maximum concurrent analysis tasks

        Returns:
            List of analysis results
        """
        import asyncio

        logger.info(f"Analyzing {len(image_paths)} images in batch")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_semaphore(path: str):
            async with semaphore:
                return await self.analyze_image(path, context)

        # Run analyses concurrently
        tasks = [analyze_with_semaphore(path) for path in image_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Image analysis failed for {image_paths[i]}: {str(result)}")
                valid_results.append({
                    "image_path": image_paths[i],
                    "analysis": None,
                    "error": str(result),
                    "confidence_score": 0.0
                })
            else:
                valid_results.append(result)

        logger.info(f"Batch analysis complete: {len(valid_results)} results")
        return valid_results

    def detect_duplicates(
        self,
        analyses: List[Dict[str, Any]],
        similarity_threshold: float = 0.9
    ) -> List[List[str]]:
        """
        Detect duplicate or near-duplicate images based on analysis

        Args:
            analyses: List of image analyses
            similarity_threshold: Threshold for duplicate detection (0.0-1.0)

        Returns:
            List of duplicate groups (each group is list of image paths)
        """
        from difflib import SequenceMatcher

        duplicate_groups = []
        processed = set()

        for i, analysis1 in enumerate(analyses):
            if analysis1["image_path"] in processed:
                continue

            group = [analysis1["image_path"]]

            for j, analysis2 in enumerate(analyses[i + 1:], start=i + 1):
                if analysis2["image_path"] in processed:
                    continue

                # Compare anatomical structures
                structures1 = set(analysis1.get("analysis", {}).get("anatomical_structures", []))
                structures2 = set(analysis2.get("analysis", {}).get("anatomical_structures", []))

                if structures1 and structures2:
                    similarity = len(structures1 & structures2) / max(len(structures1), len(structures2))

                    if similarity >= similarity_threshold:
                        group.append(analysis2["image_path"])
                        processed.add(analysis2["image_path"])

            if len(group) > 1:
                duplicate_groups.append(group)
                processed.add(analysis1["image_path"])

        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        return duplicate_groups

    def filter_low_quality(
        self,
        analyses: List[Dict[str, Any]],
        min_quality_score: float = 5.0,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Filter out low-quality images

        Args:
            analyses: List of image analyses
            min_quality_score: Minimum quality score (1-10)
            min_confidence: Minimum confidence score (0.0-1.0)

        Returns:
            Filtered list of high-quality analyses
        """
        filtered = []

        for analysis in analyses:
            if analysis.get("analysis") is None:
                continue

            quality_score = analysis["analysis"].get("quality", {}).get("score", 0)
            confidence = analysis.get("confidence_score", 0.0)

            if quality_score >= min_quality_score and confidence >= min_confidence:
                filtered.append(analysis)

        logger.info(f"Filtered {len(filtered)}/{len(analyses)} high-quality images")
        return filtered
