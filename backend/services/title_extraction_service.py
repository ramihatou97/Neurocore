"""
Title Extraction Service
Automatically extract book titles from PDF cover pages using GPT-4 Vision
Part of Enhancement #2: AI Title Extraction
"""

import fitz  # PyMuPDF
import base64
import re
import json
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
from pathlib import Path
import uuid as uuid_module

from openai import OpenAI
from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class TitleExtractionService:
    """
    Service for extracting book titles from PDF cover pages using GPT-4 Vision

    Features:
    - Renders PDF first page to high-quality PNG image
    - Uses GPT-4 Vision to extract title with confidence scoring
    - Auto-applies titles with confidence ≥ 0.8
    - Suggests titles for manual review when 0.5 ≤ confidence < 0.8
    - Cleans and validates extracted titles
    - Handles errors gracefully with detailed logging
    """

    # GPT-4 Vision specialized prompt for medical textbook titles
    SYSTEM_PROMPT = """You are a specialized assistant for extracting book titles from medical textbook cover pages.

TASK: Analyze the cover page image and extract the MAIN TITLE of the book.

RULES:
1. Extract ONLY the main title (ignore subtitles, authors, publishers, edition numbers)
2. Preserve capitalization as shown on cover
3. Include volume/edition numbers ONLY if part of main title
4. Remove generic prefixes like "Handbook of", "Atlas of" if followed by clear title
5. If multiple titles visible, extract the LARGEST/MOST PROMINENT one
6. For neurosurgical texts, prefer clinical/anatomical titles over generic descriptions
7. Remove publisher names, author names, and edition statements

EXAMPLES:
✓ "Neurological Surgery" (not "Handbook of Neurological Surgery")
✓ "Youmans Vol. 1" (volume is part of title)
✓ "Spinal Disorders" (not "Comprehensive Textbook of Spinal Disorders")
✓ "Brain Tumors" (not "Brain Tumors, Second Edition")
✗ "Fifth Edition" (not a title)
✗ "John Doe, MD" (not a title)
✗ "Elsevier" (publisher, not title)

CONFIDENCE SCORING:
- 1.0: Clear, large, unambiguous title text
- 0.9: Clear title with minor formatting variations
- 0.8: Title visible but requires interpretation
- 0.7: Title partially obscured or ambiguous
- 0.5: Multiple possible titles, unclear which is main
- 0.3: Very unclear or heavily stylized
- 0.0: No title visible

OUTPUT FORMAT (JSON):
{
  "title": "Extracted Title Here",
  "confidence": 0.95,
  "reasoning": "Title is clearly visible in large font at top of page",
  "alternative_titles": ["Alt 1", "Alt 2"],
  "detected_language": "English",
  "has_subtitle": true,
  "subtitle": "Principles and Practice"
}

If no clear title visible, return:
{
  "title": null,
  "confidence": 0.0,
  "reasoning": "No clear title text found on cover"
}
"""

    USER_PROMPT = "Extract the main title from this medical textbook cover page."

    def __init__(self):
        """Initialize title extraction service"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"  # GPT-4 Omni with vision capabilities (2x faster, half price vs deprecated gpt-4-vision-preview)

    def extract_title_from_pdf(
        self,
        pdf_path: str,
        page_num: int = 0
    ) -> Tuple[Optional[str], float, Dict[str, Any]]:
        """
        Extract title from PDF cover page using GPT-4 Vision

        Args:
            pdf_path: Path to PDF file
            page_num: Page number to extract from (default 0 = first page)

        Returns:
            Tuple of (title, confidence, metadata):
            - title: Extracted title string or None if extraction failed
            - confidence: Confidence score 0.0-1.0
            - metadata: Dict with reasoning, alternatives, language, etc.

        Examples:
            >>> service = TitleExtractionService()
            >>> title, conf, meta = service.extract_title_from_pdf("book.pdf")
            >>> print(f"Title: {title}, Confidence: {conf}")
            Title: Youmans Neurological Surgery Vol. 1, Confidence: 0.95
        """
        try:
            # Validate PDF exists
            if not Path(pdf_path).exists():
                logger.error(f"PDF file not found: {pdf_path}")
                return None, 0.0, {"error": "PDF file not found"}

            # Open PDF and render page to image
            logger.info(f"Extracting title from {pdf_path}, page {page_num}")
            doc = fitz.open(pdf_path)

            if page_num >= len(doc):
                logger.error(f"Page {page_num} does not exist (PDF has {len(doc)} pages)")
                doc.close()
                return None, 0.0, {"error": f"Page {page_num} out of range"}

            # Render page to PNG image
            image_bytes = self._render_page_to_image(doc, page_num)
            doc.close()

            # Convert image to base64
            image_base64 = self._encode_image_to_base64(image_bytes)

            # Call GPT-4 Vision API
            logger.info(f"Calling GPT-4 Vision API for title extraction")
            vision_response = self._call_gpt4_vision(image_base64)

            # Extract results
            title = vision_response.get("title")
            confidence = vision_response.get("confidence", 0.0)
            reasoning = vision_response.get("reasoning", "")
            alternatives = vision_response.get("alternative_titles", [])
            language = vision_response.get("detected_language", "Unknown")
            subtitle = vision_response.get("subtitle")

            # Clean title if extracted
            if title:
                title = self._clean_title(title)

            # Build metadata
            metadata = {
                "reasoning": reasoning,
                "alternatives": alternatives,
                "language": language,
                "subtitle": subtitle,
                "extraction_method": "gpt4_vision",
                "page_number": page_num,
                "timestamp": datetime.utcnow().isoformat(),
                "model": self.model
            }

            logger.info(
                f"Title extraction complete: title='{title}', "
                f"confidence={confidence:.2f}, language={language}"
            )

            return title, confidence, metadata

        except Exception as e:
            logger.error(f"Title extraction failed: {str(e)}", exc_info=True)
            return None, 0.0, {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def _render_page_to_image(self, doc: fitz.Document, page_num: int) -> bytes:
        """
        Render PDF page to PNG image

        Args:
            doc: PyMuPDF document
            page_num: Page number to render

        Returns:
            PNG image as bytes

        Quality settings:
        - DPI: 150 (balance between quality and size)
        - Format: PNG (lossless)
        - Max dimension: 2048px (GPT-4 Vision limit)
        """
        page = doc[page_num]

        # Create pixmap (image representation) at 150 DPI
        # Matrix(2.0, 2.0) = 150 DPI (default is 72 DPI)
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)

        # Ensure dimensions don't exceed GPT-4 Vision limits
        if pix.width > 2048 or pix.height > 2048:
            # Scale down proportionally
            scale = min(2048 / pix.width, 2048 / pix.height)
            mat = fitz.Matrix(2.0 * scale, 2.0 * scale)
            pix = page.get_pixmap(matrix=mat)

        # Convert to PNG bytes
        img_bytes = pix.tobytes("png")

        logger.debug(f"Rendered page {page_num}: {pix.width}x{pix.height} pixels, {len(img_bytes)} bytes")

        return img_bytes

    def _encode_image_to_base64(self, image_bytes: bytes) -> str:
        """
        Encode image bytes to base64 string for API transmission

        Args:
            image_bytes: PNG image bytes

        Returns:
            Base64-encoded string
        """
        return base64.b64encode(image_bytes).decode('utf-8')

    def _call_gpt4_vision(self, image_base64: str) -> dict:
        """
        Call GPT-4 Vision API to extract title from image

        Args:
            image_base64: Base64-encoded PNG image

        Returns:
            Dict with title, confidence, reasoning, etc.

        Raises:
            Exception: If API call fails
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self.USER_PROMPT
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"  # Use high detail for better accuracy
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},  # Force JSON response
                max_tokens=500,
                temperature=0.3  # Low temperature for consistency
            )

            # Parse JSON response
            content = response.choices[0].message.content
            result = json.loads(content)

            logger.debug(f"GPT-4 Vision response: {json.dumps(result, indent=2)}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-4 Vision JSON response: {str(e)}")
            raise Exception(f"Invalid JSON response from GPT-4 Vision: {str(e)}")

        except Exception as e:
            logger.error(f"GPT-4 Vision API call failed: {str(e)}", exc_info=True)
            raise

    def _clean_title(self, title: str) -> str:
        """
        Clean and normalize extracted title

        Removes common noise patterns:
        - Articles at start (The, A, An)
        - Edition information at end
        - Parenthetical notes at end
        - Extra whitespace

        Args:
            title: Raw extracted title

        Returns:
            Cleaned title string

        Examples:
            >>> service._clean_title("The Neurosurgical Atlas")
            "Neurosurgical Atlas"
            >>> service._clean_title("Spine Surgery First Edition")
            "Spine Surgery"
            >>> service._clean_title("Brain   Tumors  (Updated)")
            "Brain Tumors"
        """
        if not title:
            return title

        # Remove extra whitespace (collapse multiple spaces)
        title = re.sub(r'\s+', ' ', title).strip()

        # Remove common noise patterns
        noise_patterns = [
            r'^(The|A|An)\s+',  # Articles at start
            r'\s+(First|Second|Third|Fourth|Fifth|Sixth|1st|2nd|3rd|4th|5th|6th)\s+Edition$',
            r'\s+Edition$',  # Standalone "Edition"
            r'\s+\(.*?\)$',  # Parenthetical at end
            r'\s+Vol\.\s*$',  # Trailing "Vol." without number
            r'\s+-\s*$',  # Trailing dash
        ]

        for pattern in noise_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)

        # Remove leading/trailing punctuation
        title = title.strip(' .,;:-')

        # Limit length (preserve meaningful content)
        if len(title) > 200:
            title = title[:197] + "..."

        return title.strip()

    def batch_extract_titles(
        self,
        book_ids: List[uuid_module.UUID],
        auto_apply_threshold: float = 0.8,
        db_session=None
    ) -> Dict[str, Any]:
        """
        Batch process multiple books for title extraction

        Args:
            book_ids: List of book UUIDs to process
            auto_apply_threshold: Confidence threshold for auto-applying (default 0.8)
            db_session: Database session (optional)

        Returns:
            Dict with processing statistics and results:
            {
                "processed": 15,
                "auto_applied": 12,
                "manual_review": 3,
                "failed": 0,
                "results": [...]
            }

        Example:
            >>> service = TitleExtractionService()
            >>> book_ids = [UUID(...), UUID(...)]
            >>> results = service.batch_extract_titles(book_ids, auto_apply_threshold=0.85)
            >>> print(f"Auto-applied: {results['auto_applied']}/{results['processed']}")
        """
        from backend.database import get_db
        from backend.database.models import PDFBook

        results = {
            "processed": 0,
            "auto_applied": 0,
            "manual_review": 0,
            "failed": 0,
            "total_books": len(book_ids),
            "results": []
        }

        # Use provided session or create new one
        if db_session:
            db = db_session
            close_session = False
        else:
            db = next(get_db())
            close_session = True

        try:
            for book_id in book_ids:
                try:
                    # Get book from database
                    book = db.query(PDFBook).filter(PDFBook.id == book_id).first()

                    if not book:
                        results["failed"] += 1
                        results["results"].append({
                            "book_id": str(book_id),
                            "status": "error",
                            "message": "Book not found"
                        })
                        continue

                    # Extract title
                    title, confidence, metadata = self.extract_title_from_pdf(
                        book.file_path,
                        page_num=0
                    )

                    results["processed"] += 1

                    if title and confidence >= auto_apply_threshold:
                        # Auto-apply high-confidence titles
                        results["auto_applied"] += 1
                        results["results"].append({
                            "book_id": str(book_id),
                            "status": "auto_applied",
                            "title": title,
                            "confidence": confidence,
                            "previous_title": book.title
                        })

                        logger.info(
                            f"Auto-applied title for book {book_id}: "
                            f"'{book.title}' → '{title}' (confidence {confidence:.2f})"
                        )

                    elif title and confidence >= 0.5:
                        # Medium confidence - manual review
                        results["manual_review"] += 1
                        results["results"].append({
                            "book_id": str(book_id),
                            "status": "needs_review",
                            "suggested_title": title,
                            "confidence": confidence,
                            "alternatives": metadata.get("alternatives", []),
                            "current_title": book.title
                        })

                        logger.info(
                            f"Title suggestion for book {book_id}: "
                            f"'{title}' (confidence {confidence:.2f})"
                        )

                    else:
                        # Low confidence or extraction failed
                        results["failed"] += 1
                        results["results"].append({
                            "book_id": str(book_id),
                            "status": "failed",
                            "reason": metadata.get("error") or "Low confidence",
                            "confidence": confidence,
                            "current_title": book.title
                        })

                        logger.warning(
                            f"Title extraction failed for book {book_id}: "
                            f"{metadata.get('error', 'Low confidence')} "
                            f"(confidence {confidence:.2f})"
                        )

                except Exception as e:
                    results["failed"] += 1
                    results["results"].append({
                        "book_id": str(book_id),
                        "status": "error",
                        "message": str(e)
                    })
                    logger.error(f"Error processing book {book_id}: {str(e)}", exc_info=True)

        finally:
            if close_session:
                db.close()

        logger.info(
            f"Batch title extraction complete: "
            f"{results['processed']}/{results['total_books']} processed, "
            f"{results['auto_applied']} auto-applied, "
            f"{results['manual_review']} need review, "
            f"{results['failed']} failed"
        )

        return results
