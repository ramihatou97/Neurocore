"""
Textbook Processor Service
Handles classification, chapter detection, and extraction for PDF textbooks
Part of Chapter-Level Vector Search (Phase 2)
"""

import fitz  # PyMuPDF
import re
import hashlib
import base64
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
import uuid

from openai import OpenAI
from backend.database.models import PDFBook, PDFChapter
from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


@dataclass
class ChapterDetection:
    """Data class for detected chapter information"""
    chapter_number: Optional[int]
    chapter_title: str
    start_page: int
    end_page: int
    confidence: float  # 0.0-1.0
    detection_method: str  # 'toc', 'pattern', 'heading'


class TextbookProcessorService:
    """
    Service for processing textbooks and extracting chapters

    Three-tier chapter detection strategy:
    1. TOC Parsing (90% confidence) - PyMuPDF table of contents
    2. Pattern Matching (80% confidence) - Regex for "Chapter X", "CHAPTER I"
    3. Heading Detection (60% confidence) - Font size analysis

    Classification:
    - textbook: >500 pages, TOC present, >10 TOC entries
    - standalone_chapter: 20-100 pages, "chapter" in text OR TOC present
    - research_paper: <50 pages, "abstract" present
    """

    def __init__(self, db_session: Session):
        """
        Initialize textbook processor

        Args:
            db_session: Database session
        """
        self.db = db_session

        # Initialize OpenAI client for OCR fallback
        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.ocr_enabled = True
            logger.info("OCR fallback enabled (GPT-4 Vision)")
        else:
            self.openai_client = None
            self.ocr_enabled = False
            logger.warning("OCR fallback disabled (no OpenAI API key)")

    def classify_pdf(self, file_path: str) -> str:
        """
        Classify PDF as textbook, standalone_chapter, or research_paper

        Args:
            file_path: Path to PDF file

        Returns:
            str: "textbook", "standalone_chapter", or "research_paper"
        """
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)

            # Extract table of contents
            toc = doc.get_toc()
            toc_present = len(toc) > 0
            toc_entries = len(toc)

            # Extract first 10 pages text for analysis
            sample_text = ""
            for page_num in range(min(10, page_count)):
                page = doc[page_num]
                sample_text += page.get_text().lower()

            doc.close()

            # Classification logic
            # Textbook: >500 pages, TOC present, >10 TOC entries
            if page_count > 500 and toc_present and toc_entries >= 10:
                logger.info(f"Classified as textbook: {page_count} pages, {toc_entries} TOC entries")
                return "textbook"

            # Research paper: <50 pages, "abstract" present
            if page_count < 50 and "abstract" in sample_text:
                logger.info(f"Classified as research_paper: {page_count} pages, abstract found")
                return "research_paper"

            # Standalone chapter: 20-100 pages, "chapter" in text OR TOC present
            if 20 <= page_count <= 100:
                if "chapter" in sample_text or toc_present:
                    logger.info(f"Classified as standalone_chapter: {page_count} pages")
                    return "standalone_chapter"

            # Default: If has TOC with multiple entries, likely textbook
            if toc_present and toc_entries >= 5:
                logger.info(f"Classified as textbook (default): {toc_entries} TOC entries")
                return "textbook"

            # Final fallback: Use page count
            if page_count > 200:
                return "textbook"
            elif page_count < 50:
                return "research_paper"
            else:
                return "standalone_chapter"

        except Exception as e:
            logger.error(f"Error classifying PDF: {str(e)}", exc_info=True)
            # Default to standalone_chapter on error
            return "standalone_chapter"

    def detect_chapters(self, pdf_path: str) -> List[ChapterDetection]:
        """
        Detect chapters using 3-tier strategy:
        1. TOC parsing (90% confidence)
        2. Pattern matching (80% confidence)
        3. Heading detection (60% confidence)

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of detected chapters with metadata
        """
        chapters = []

        # Strategy 1: TOC parsing (highest confidence)
        toc_chapters = self._detect_chapters_from_toc(pdf_path)
        if toc_chapters:
            logger.info(f"Detected {len(toc_chapters)} chapters via TOC parsing (90% confidence)")
            return toc_chapters

        # Strategy 2: Pattern matching (medium confidence)
        pattern_chapters = self._detect_chapters_from_patterns(pdf_path)
        if pattern_chapters:
            logger.info(f"Detected {len(pattern_chapters)} chapters via pattern matching (80% confidence)")
            return pattern_chapters

        # Strategy 3: Heading detection (lowest confidence)
        heading_chapters = self._detect_chapters_from_headings(pdf_path)
        if heading_chapters:
            logger.info(f"Detected {len(heading_chapters)} chapters via heading detection (60% confidence)")
            return heading_chapters

        # Fallback: Treat entire PDF as single chapter
        logger.warning("No chapters detected, treating entire PDF as single chapter")
        return self._create_single_chapter_fallback(pdf_path)

    def _detect_chapters_from_toc(self, pdf_path: str) -> List[ChapterDetection]:
        """
        Strategy 1: Extract chapters from PDF table of contents
        Confidence: 90%
        """
        chapters = []

        try:
            doc = fitz.open(pdf_path)
            toc = doc.get_toc()
            total_pages = len(doc)

            if not toc:
                doc.close()
                return chapters

            # Filter TOC entries to find chapter-level entries
            # Level 1 entries are typically chapters
            chapter_entries = [entry for entry in toc if entry[0] == 1]

            if not chapter_entries:
                # If no level 1 entries, try level 2
                chapter_entries = [entry for entry in toc if entry[0] == 2]

            for i, entry in enumerate(chapter_entries):
                level, title, page_num = entry

                # Determine end page (next chapter's start - 1, or last page)
                if i + 1 < len(chapter_entries):
                    end_page = chapter_entries[i + 1][2] - 1
                else:
                    end_page = total_pages

                # Extract chapter number from title if present
                chapter_number = self._extract_chapter_number(title)

                chapters.append(ChapterDetection(
                    chapter_number=chapter_number,
                    chapter_title=title.strip(),
                    start_page=page_num,
                    end_page=end_page,
                    confidence=0.9,
                    detection_method='toc'
                ))

            doc.close()

        except Exception as e:
            logger.error(f"Error detecting chapters from TOC: {str(e)}", exc_info=True)

        return chapters

    def _detect_chapters_from_patterns(self, pdf_path: str) -> List[ChapterDetection]:
        """
        Strategy 2: Detect chapters using regex patterns
        Confidence: 80%

        Patterns:
        - "Chapter 1", "Chapter 2", etc.
        - "CHAPTER I", "CHAPTER II", etc. (Roman numerals)
        - "Ch. 1", "Ch. 2", etc.
        """
        chapters = []

        # Common chapter patterns
        patterns = [
            r'^\s*Chapter\s+(\d+)[:\s]+(.+)$',  # Chapter 1: Title
            r'^\s*CHAPTER\s+([IVXLCDM]+)[:\s]+(.+)$',  # CHAPTER I: Title
            r'^\s*Ch\.\s+(\d+)[:\s]+(.+)$',  # Ch. 1: Title
            r'^\s*(\d+)\.\s+([A-Z][^.]+)$',  # 1. Title (numbered section)
        ]

        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            detected_positions = []

            # Scan first 5 lines of each page
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text()
                lines = text.split('\n')[:5]  # Check first 5 lines only

                for line in lines:
                    for pattern in patterns:
                        match = re.match(pattern, line.strip(), re.IGNORECASE)
                        if match:
                            chapter_num_str = match.group(1)
                            title = match.group(2) if len(match.groups()) > 1 else f"Chapter {chapter_num_str}"

                            # Convert Roman numerals to integers if needed
                            if chapter_num_str.upper() in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']:
                                chapter_num = self._roman_to_int(chapter_num_str.upper())
                            else:
                                chapter_num = int(chapter_num_str)

                            detected_positions.append({
                                'number': chapter_num,
                                'title': title.strip(),
                                'page': page_num + 1  # 1-indexed
                            })
                            break  # Found match, move to next page

            doc.close()

            # Convert detections to ChapterDetection objects
            detected_positions.sort(key=lambda x: x['page'])

            for i, detection in enumerate(detected_positions):
                end_page = detected_positions[i + 1]['page'] - 1 if i + 1 < len(detected_positions) else total_pages

                chapters.append(ChapterDetection(
                    chapter_number=detection['number'],
                    chapter_title=detection['title'],
                    start_page=detection['page'],
                    end_page=end_page,
                    confidence=0.8,
                    detection_method='pattern'
                ))

        except Exception as e:
            logger.error(f"Error detecting chapters from patterns: {str(e)}", exc_info=True)

        return chapters

    def _detect_chapters_from_headings(self, pdf_path: str) -> List[ChapterDetection]:
        """
        Strategy 3: Detect chapters using font size analysis
        Confidence: 60%

        Assumes chapter titles have larger font size than body text
        """
        # Note: This is a simplified implementation
        # Production version would analyze font sizes across the document
        # For now, return empty to fall back to single chapter
        logger.info("Heading detection not fully implemented, using fallback")
        return []

    def _create_single_chapter_fallback(self, pdf_path: str) -> List[ChapterDetection]:
        """
        Fallback: Treat entire PDF as single chapter
        """
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            # Try to extract title from metadata
            metadata = doc.metadata
            title = metadata.get('title', '') or Path(pdf_path).stem

            doc.close()

            return [ChapterDetection(
                chapter_number=None,
                chapter_title=title,
                start_page=1,
                end_page=total_pages,
                confidence=0.5,
                detection_method='fallback'
            )]
        except Exception as e:
            logger.error(f"Error creating fallback chapter: {str(e)}", exc_info=True)
            return []

    def _has_encoding_issues(self, text: str, threshold: float = 0.05) -> bool:
        """
        Detect if extracted text has encoding issues (too many replacement characters)

        Args:
            text: Extracted text to check
            threshold: Maximum acceptable ratio of replacement chars (default 5%)

        Returns:
            True if text has encoding issues, False otherwise
        """
        if not text or len(text) == 0:
            return False

        # Count UTF-8 replacement characters (�)
        replacement_count = text.count('\ufffd')  # U+FFFD

        # Calculate ratio
        ratio = replacement_count / len(text)

        return ratio > threshold

    def _extract_text_with_flags(self, page: fitz.Page) -> str:
        """
        Extract text using PyMuPDF with enhanced flags for better encoding

        Args:
            page: PyMuPDF Page object

        Returns:
            Extracted text with better encoding handling
        """
        try:
            # Use flags to preserve whitespace and ligatures
            text = page.get_text(
                "text",
                flags=fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_PRESERVE_LIGATURES
            )
            return text
        except Exception as e:
            logger.warning(f"Flag-based extraction failed: {str(e)}")
            return page.get_text()  # Fallback to default

    def _extract_text_with_blocks(self, page: fitz.Page) -> str:
        """
        Extract text using block-level extraction (more robust for complex PDFs)

        Args:
            page: PyMuPDF Page object

        Returns:
            Extracted text from blocks
        """
        try:
            blocks = page.get_text("blocks")
            text_parts = []

            for block in blocks:
                # block is (x0, y0, x1, y1, "text", block_no, block_type)
                if len(block) >= 5:
                    block_text = block[4]
                    if isinstance(block_text, str) and block_text.strip():
                        text_parts.append(block_text)

            return "\n".join(text_parts)
        except Exception as e:
            logger.warning(f"Block extraction failed: {str(e)}")
            return ""

    def _extract_text_with_dict(self, page: fitz.Page) -> str:
        """
        Extract text using dictionary method (most robust, extracts character-by-character)

        Args:
            page: PyMuPDF Page object

        Returns:
            Extracted text from raw dictionary
        """
        try:
            text_dict = page.get_text("dict")
            text_parts = []

            # Navigate through blocks
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            if span_text:
                                line_text += span_text
                        if line_text.strip():
                            text_parts.append(line_text)

            return "\n".join(text_parts)
        except Exception as e:
            logger.warning(f"Dict extraction failed: {str(e)}")
            return ""

    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean extracted text by removing/fixing encoding artifacts

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        if not text:
            return text

        # Remove excessive whitespace while preserving paragraph breaks
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Clean each line but preserve structure
            cleaned_line = ' '.join(line.split())
            if cleaned_line:  # Only keep non-empty lines
                cleaned_lines.append(cleaned_line)

        # Join with single newlines
        cleaned_text = '\n'.join(cleaned_lines)

        # Remove NULL bytes if any
        cleaned_text = cleaned_text.replace('\x00', '')

        # Replace common problematic characters with safer alternatives
        replacements = {
            '\u2018': "'",  # Left single quotation mark
            '\u2019': "'",  # Right single quotation mark
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash
            '\u2026': '...', # Ellipsis
        }

        for old_char, new_char in replacements.items():
            cleaned_text = cleaned_text.replace(old_char, new_char)

        return cleaned_text

    def _extract_text_with_ocr(self, page: fitz.Page, page_num: int) -> str:
        """
        Extract text from PDF page using GPT-4 Vision OCR (fallback for severe encoding issues)

        This method is only used when all other extraction methods fail to produce readable text.
        It renders the page to an image and uses GPT-4 Vision to extract the text via OCR.

        Args:
            page: PyMuPDF Page object
            page_num: Page number for logging

        Returns:
            OCR-extracted text

        Cost: ~$0.01-0.02 per page (GPT-4 Vision high detail)
        """
        if not self.ocr_enabled:
            logger.warning(f"Page {page_num}: OCR requested but not enabled (no OpenAI API key)")
            return ""

        try:
            logger.info(f"Page {page_num}: Using GPT-4 Vision OCR (fallback extraction)")

            # Render page to PNG image at 150 DPI
            mat = fitz.Matrix(2.0, 2.0)  # 2x scale = 150 DPI (default is 72)
            pix = page.get_pixmap(matrix=mat)

            # Ensure dimensions don't exceed GPT-4 Vision limits (2048px)
            if pix.width > 2048 or pix.height > 2048:
                scale = min(2048 / pix.width, 2048 / pix.height)
                mat = fitz.Matrix(2.0 * scale, 2.0 * scale)
                pix = page.get_pixmap(matrix=mat)

            # Convert to PNG bytes
            img_bytes = pix.tobytes("png")
            logger.debug(f"Page {page_num}: Rendered {pix.width}x{pix.height} image ({len(img_bytes)} bytes)")

            # Encode to base64 for API
            image_base64 = base64.b64encode(img_bytes).decode('utf-8')

            # Prepare OCR prompt
            ocr_prompt = """Extract ALL text from this page of a medical/neurosurgical textbook.

RULES:
1. Extract text in reading order (left to right, top to bottom)
2. Preserve paragraph structure with blank lines
3. Include ALL visible text (body text, headings, captions, footnotes)
4. Preserve medical terminology and technical terms exactly as shown
5. Skip page numbers, headers, footers
6. Use standard ASCII quotes and punctuation
7. For tables, extract text row by row
8. For multi-column layouts, extract left column first, then right column

OUTPUT FORMAT: Plain text only (no markdown, no formatting markers)"""

            # Call GPT-4 Vision API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # GPT-4 Omni with vision
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": ocr_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"  # High detail for better OCR accuracy
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,  # Allow up to 4K tokens for dense pages
                temperature=0.0  # Deterministic for consistency
            )

            # Extract text from response
            extracted_text = response.choices[0].message.content.strip()

            logger.info(
                f"Page {page_num}: OCR extracted {len(extracted_text)} characters "
                f"(tokens used: ~{response.usage.total_tokens})"
            )

            return extracted_text

        except Exception as e:
            logger.error(f"Page {page_num}: OCR extraction failed: {str(e)}", exc_info=True)
            return ""

    def _extract_page_text_robust(self, page: fitz.Page, page_num: int) -> str:
        """
        Robustly extract text from a PDF page using multi-strategy approach

        Strategy Priority:
        1. Standard extraction with flags
        2. If encoding issues detected (>5% replacement chars), try blocks method
        3. If still bad, try dictionary method
        4. If still bad (>5% replacement chars) and OCR enabled, try GPT-4 Vision OCR
        5. Clean the final result

        Args:
            page: PyMuPDF Page object
            page_num: Page number (for logging)

        Returns:
            Extracted text with best possible quality
        """
        # Strategy 1: Try standard extraction with flags
        text = self._extract_text_with_flags(page)

        # Check for encoding issues
        if self._has_encoding_issues(text, threshold=0.05):
            replacement_char = chr(0xfffd)
            logger.warning(
                f"Page {page_num}: Encoding issues detected "
                f"({text.count(replacement_char)} replacement chars), trying blocks method"
            )

            # Strategy 2: Try block extraction
            text_blocks = self._extract_text_with_blocks(page)

            if text_blocks and not self._has_encoding_issues(text_blocks, threshold=0.05):
                logger.info(f"Page {page_num}: Blocks method successful")
                text = text_blocks
            else:
                logger.warning(
                    f"Page {page_num}: Blocks method also has issues, "
                    f"trying dictionary method"
                )

                # Strategy 3: Try dictionary extraction
                text_dict = self._extract_text_with_dict(page)

                if text_dict and not self._has_encoding_issues(text_dict, threshold=0.05):
                    logger.info(f"Page {page_num}: Dictionary method successful")
                    text = text_dict
                else:
                    # Keep whichever has fewer replacement characters
                    options = [(text, text.count('\ufffd')),
                              (text_blocks, text_blocks.count('\ufffd') if text_blocks else float('inf')),
                              (text_dict, text_dict.count('\ufffd') if text_dict else float('inf'))]
                    text = min(options, key=lambda x: x[1])[0]

                    # Strategy 4: Try OCR if still has encoding issues
                    if self._has_encoding_issues(text, threshold=0.05) and self.ocr_enabled:
                        logger.warning(
                            f"Page {page_num}: All PyMuPDF methods failed, "
                            f"falling back to GPT-4 Vision OCR"
                        )
                        text_ocr = self._extract_text_with_ocr(page, page_num)

                        if text_ocr and len(text_ocr) > 100:  # Reasonable amount of text extracted
                            logger.info(f"Page {page_num}: OCR extraction successful")
                            text = text_ocr
                        else:
                            logger.error(
                                f"Page {page_num}: OCR extraction failed, "
                                f"keeping best PyMuPDF result"
                            )

        # Strategy 5: Clean the final text
        text = self._clean_extracted_text(text)

        return text

    def extract_chapter(
        self,
        pdf_path: str,
        start_page: int,
        end_page: int,
        title: str
    ) -> Dict[str, Any]:
        """
        Extract chapter content from PDF page range with robust encoding handling

        Uses multi-strategy text extraction to handle complex PDFs with:
        - CID-keyed fonts
        - Custom encodings
        - Embedded fonts
        - Ligatures and special characters

        Args:
            pdf_path: Path to PDF file
            start_page: Starting page (1-indexed)
            end_page: Ending page (1-indexed)
            title: Chapter title

        Returns:
            Dict with extracted content and metadata
        """
        try:
            doc = fitz.open(pdf_path)

            # Extract text from page range (convert to 0-indexed)
            extracted_text = ""
            image_count = 0
            pages_with_encoding_issues = 0

            for page_num in range(start_page - 1, end_page):
                if page_num >= len(doc):
                    break

                page = doc[page_num]

                # Use robust multi-strategy extraction
                page_text = self._extract_page_text_robust(page, page_num + 1)

                # Track encoding issues for logging
                if self._has_encoding_issues(page_text):
                    pages_with_encoding_issues += 1

                extracted_text += page_text + "\n"

                # Count images on page
                image_list = page.get_images()
                image_count += len(image_list)

            doc.close()

            # Log extraction quality metrics
            total_pages_extracted = end_page - start_page + 1
            if pages_with_encoding_issues > 0:
                logger.warning(
                    f"Chapter '{title}': {pages_with_encoding_issues}/{total_pages_extracted} "
                    f"pages still have encoding issues after robust extraction"
                )
            else:
                logger.info(
                    f"Chapter '{title}': Clean extraction for all {total_pages_extracted} pages"
                )

            # Calculate word count
            word_count = len(extracted_text.split())

            # Calculate content hash (SHA-256 of normalized text)
            normalized_text = self._normalize_text(extracted_text)

            # If normalized text is empty or very short, include chapter metadata to ensure uniqueness
            # This prevents duplicate constraint violations for chapters with failed text extraction
            if len(normalized_text.strip()) < 10:
                # Include title and page range in hash for uniqueness
                hash_input = f"{title}_{start_page}_{end_page}_{normalized_text}"
                content_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
                logger.warning(f"Chapter '{title}' has minimal text ({len(normalized_text)} chars), using metadata-enhanced hash")
            else:
                content_hash = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()

            # Calculate page count
            page_count = end_page - start_page + 1

            return {
                'title': title,
                'start_page': start_page,
                'end_page': end_page,
                'page_count': page_count,
                'extracted_text': extracted_text,
                'word_count': word_count,
                'has_images': image_count > 0,
                'image_count': image_count,
                'content_hash': content_hash
            }

        except Exception as e:
            logger.error(f"Error extracting chapter: {str(e)}", exc_info=True)
            raise

    def process_pdf(
        self,
        file_path: str,
        uploaded_by: Optional[uuid.UUID] = None,
        original_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        MAIN ENTRY POINT: Process PDF and extract all chapters

        Workflow:
        1. Classify PDF (textbook/chapter/paper)
        2. Create PDFBook record
        3. Detect chapters
        4. Extract each chapter
        5. Create PDFChapter records
        6. Return summary

        Args:
            file_path: Path to uploaded PDF file
            uploaded_by: UUID of user who uploaded
            original_filename: Original filename from upload (used as fallback for title)

        Returns:
            Dict with book_id, chapters_created, and status
        """
        try:
            logger.info(f"Processing PDF: {file_path}")

            # Step 1: Classify PDF
            pdf_type = self.classify_pdf(file_path)
            logger.info(f"PDF classified as: {pdf_type}")

            # Step 2: Extract basic metadata
            doc = fitz.open(file_path)
            metadata = doc.metadata
            total_pages = len(doc)
            file_size = Path(file_path).stat().st_size
            doc.close()

            # Step 3: Create PDFBook record
            # Use PDF metadata title, fall back to original filename (without extension), then UUID
            title = metadata.get('title', '') or (
                Path(original_filename).stem if original_filename else Path(file_path).stem
            )

            book = PDFBook(
                title=title,
                authors=self._parse_authors(metadata.get('author', '')),
                publication_year=self._extract_year(metadata.get('creationDate', '')),
                total_pages=total_pages,
                file_path=file_path,
                file_size_bytes=file_size,
                uploaded_by=uploaded_by,
                processing_status='processing',
                book_metadata={
                    'pdf_type': pdf_type,
                    'original_metadata': metadata,
                    'original_filename': original_filename
                }
            )

            self.db.add(book)
            self.db.commit()
            self.db.refresh(book)

            logger.info(f"Created PDFBook record: {book.id}")

            # Step 4: Detect chapters
            chapters = self.detect_chapters(file_path)
            logger.info(f"Detected {len(chapters)} chapters")

            # Step 5: Extract and save each chapter
            chapters_created = 0

            for chapter_info in chapters:
                try:
                    # Extract chapter content
                    chapter_data = self.extract_chapter(
                        file_path,
                        chapter_info.start_page,
                        chapter_info.end_page,
                        chapter_info.chapter_title
                    )

                    # Determine source type
                    if pdf_type == "textbook":
                        source_type = "textbook_chapter"
                    elif pdf_type == "standalone_chapter":
                        source_type = "standalone_chapter"
                    else:  # research_paper
                        source_type = "research_paper"

                    # Create PDFChapter record
                    chapter = PDFChapter(
                        book_id=book.id,
                        source_type=source_type,
                        chapter_number=chapter_info.chapter_number,
                        chapter_title=chapter_data['title'],
                        start_page=chapter_data['start_page'],
                        end_page=chapter_data['end_page'],
                        page_count=chapter_data['page_count'],
                        extracted_text=chapter_data['extracted_text'],
                        word_count=chapter_data['word_count'],
                        has_images=chapter_data['has_images'],
                        image_count=chapter_data['image_count'],
                        content_hash=chapter_data['content_hash'],
                        detection_confidence=chapter_info.confidence,
                        detection_method=chapter_info.detection_method,
                        # Preference score: standalone > textbook chapter
                        preference_score=1.0 if source_type == "standalone_chapter" else 0.5
                    )

                    self.db.add(chapter)
                    chapters_created += 1

                except Exception as e:
                    logger.error(f"Error extracting chapter '{chapter_info.chapter_title}': {str(e)}")
                    continue

            # Commit all chapters
            self.db.commit()

            # Update book record
            book.total_chapters = chapters_created
            book.processing_status = 'completed'
            self.db.commit()

            logger.info(f"Successfully processed {chapters_created} chapters for book {book.id}")

            # TODO: Queue background tasks for:
            # - generate_chapter_embeddings(chapter_id) for each chapter
            # - check_for_duplicates(chapter_id) for each chapter

            return {
                'status': 'success',
                'book_id': str(book.id),
                'chapters_created': chapters_created,
                'pdf_type': pdf_type,
                'total_pages': total_pages
            }

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}", exc_info=True)

            # Mark book as failed if it was created
            if 'book' in locals():
                book.processing_status = 'failed'
                book.processing_error = str(e)
                self.db.commit()

            raise

    # ==================== Helper Methods ====================

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent hashing"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters
        text = re.sub(r'[^\w\s]', '', text)
        # Lowercase
        text = text.lower().strip()
        return text

    def _extract_chapter_number(self, title: str) -> Optional[int]:
        """Extract chapter number from title string"""
        # Try to find "Chapter X" or just "X"
        match = re.search(r'(?:chapter|ch\.?)\s+(\d+)', title, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Try Roman numerals
        match = re.search(r'(?:chapter|ch\.?)\s+([IVXLCDM]+)', title, re.IGNORECASE)
        if match:
            return self._roman_to_int(match.group(1).upper())

        return None

    def _roman_to_int(self, s: str) -> int:
        """Convert Roman numeral to integer"""
        roman_values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        result = 0
        prev_value = 0

        for char in reversed(s):
            value = roman_values.get(char, 0)
            if value < prev_value:
                result -= value
            else:
                result += value
            prev_value = value

        return result

    def _parse_authors(self, author_string: str) -> Optional[List[str]]:
        """Parse author string into list of authors"""
        if not author_string:
            return None

        # Split by common delimiters
        authors = re.split(r'[,;]|\sand\s', author_string)
        authors = [a.strip() for a in authors if a.strip()]

        return authors if authors else None

    def _extract_year(self, date_string: str) -> Optional[int]:
        """Extract year from date string"""
        if not date_string:
            return None

        # Try to find 4-digit year
        match = re.search(r'(\d{4})', date_string)
        if match:
            year = int(match.group(1))
            # Sanity check (1900-2100)
            if 1900 <= year <= 2100:
                return year

        return None
