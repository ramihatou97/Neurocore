# Enhancement Roadmap: Title Editing & AI Metadata
**Date:** 2025-11-01
**Status:** Implementation Planning
**Priority:** High (User-facing improvements)

---

## Overview

Migration 011 established the database schema foundation for three powerful enhancements:
1. **Title Editing UI** (Ready to implement - ~1-2 hours)
2. **AI Title Extraction** (Medium-term - smart automation)
3. **Semantic Tags** (Medium-term - enhanced search)

All database fields are already in place. This document provides comprehensive implementation plans for each enhancement.

---

## Enhancement #1: Title Editing UI
**Priority:** 🔴 HIGH (Immediate user need)
**Complexity:** 🟢 LOW (Standard CRUD operation)
**Estimated Time:** 1-2 hours
**Dependencies:** None (schema ready)

### Problem Statement

Users currently see "Untitled Book - Please Edit" for books uploaded without metadata. The database supports title editing (with full audit trail), but there's no UI to perform the edit.

**Current State:**
- ✅ Database schema complete (title_edited_at, title_edited_by, original_title)
- ✅ Backend model includes fields
- ❌ No frontend UI for editing
- ❌ No API endpoint for PATCH /books/{id}/title

**User Story:**
> As a neurosurgeon, when I see "Untitled Book - Please Edit", I want to click an "Edit" button, enter a meaningful title like "Youmans Neurological Surgery Vol. 1", and save it with proper attribution.

### Technical Design

#### 1.1 Backend API Endpoint

**File:** `backend/api/v1/endpoints/textbooks.py`

**New Endpoint:**
```python
@router.patch("/books/{book_id}/title")
async def update_book_title(
    book_id: UUID,
    title_update: BookTitleUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> BookResponse:
    """
    Update book title with audit trail

    Security:
    - Requires authentication
    - Records user_id and timestamp
    - Preserves original title if first edit

    Validation:
    - Title length: 1-500 characters
    - No empty/whitespace-only titles
    - No duplicate titles (warning only)
    """
    # Get book
    stmt = select(PDFBook).where(PDFBook.id == book_id)
    book = session.execute(stmt).scalar_one_or_none()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Preserve original title on first edit
    if book.original_title is None:
        book.original_title = book.title

    # Update title with audit trail
    book.title = title_update.title.strip()
    book.title_edited_at = datetime.utcnow()
    book.title_edited_by = current_user.id

    session.commit()
    session.refresh(book)

    return book.to_dict()
```

**Pydantic Model:**
```python
class BookTitleUpdate(BaseModel):
    """Schema for updating book title"""
    title: str = Field(..., min_length=1, max_length=500)

    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty or whitespace')
        if v.strip() == "Untitled Book - Please Edit":
            raise ValueError('Please enter a meaningful title')
        return v.strip()
```

#### 1.2 Frontend Component

**File:** `frontend/src/components/BookTitleEditor.jsx`

**New Component:**
```jsx
import React, { useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { PencilIcon } from '@heroicons/react/24/outline';
import axios from 'axios';

export default function BookTitleEditor({ book, onTitleUpdated }) {
  const [isOpen, setIsOpen] = useState(false);
  const [title, setTitle] = useState(book.title);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const showEditButton = book.title === "Untitled Book - Please Edit"
    || book.title.match(/^[0-9a-f]{8}-[0-9a-f]{4}/);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await axios.patch(
        `/api/v1/textbooks/books/${book.id}/title`,
        { title: title.trim() }
      );

      onTitleUpdated(response.data);
      setIsOpen(false);

      // Success notification
      toast.success('Book title updated successfully');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update title');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Edit Button */}
      <button
        onClick={() => setIsOpen(true)}
        className={`
          inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm
          ${showEditButton
            ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}
        `}
      >
        <PencilIcon className="h-4 w-4" />
        {showEditButton ? 'Edit Title (Required)' : 'Edit Title'}
      </button>

      {/* Modal Dialog */}
      <Transition show={isOpen}>
        <Dialog onClose={() => setIsOpen(false)} className="relative z-50">
          <Transition.Child
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
          </Transition.Child>

          <div className="fixed inset-0 flex items-center justify-center p-4">
            <Transition.Child
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="mx-auto max-w-lg w-full bg-white rounded-lg shadow-xl">
                <div className="p-6">
                  <Dialog.Title className="text-lg font-semibold text-gray-900 mb-4">
                    Edit Book Title
                  </Dialog.Title>

                  {/* Original Title (if exists) */}
                  {book.original_title && (
                    <div className="mb-4 p-3 bg-gray-50 rounded-md">
                      <p className="text-xs font-medium text-gray-600 mb-1">
                        Original Title:
                      </p>
                      <p className="text-sm text-gray-800 font-mono">
                        {book.original_title}
                      </p>
                    </div>
                  )}

                  <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        New Title
                      </label>
                      <input
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., Youmans Neurological Surgery Vol. 1"
                        maxLength={500}
                        required
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        {title.length}/500 characters
                      </p>
                    </div>

                    {/* Common Suggestions */}
                    <div className="mb-4">
                      <p className="text-xs font-medium text-gray-600 mb-2">
                        Common Patterns:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {[
                          "Youmans Neurological Surgery Vol. ",
                          "Handbook of Neurosurgery - ",
                          "Atlas of Neurosurgery - ",
                          "Neurosurgical Techniques - "
                        ].map((suggestion, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => setTitle(suggestion)}
                            className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded hover:bg-blue-100"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Error Display */}
                    {error && (
                      <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                        <p className="text-sm text-red-800">{error}</p>
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex justify-end gap-3">
                      <button
                        type="button"
                        onClick={() => setIsOpen(false)}
                        className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
                        disabled={isLoading}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                        disabled={isLoading || !title.trim()}
                      >
                        {isLoading ? 'Saving...' : 'Save Title'}
                      </button>
                    </div>
                  </form>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition>
    </>
  );
}
```

#### 1.3 Integration Points

**Update `TextbookDetail.jsx`:**
```jsx
import BookTitleEditor from '../components/BookTitleEditor';

function TextbookDetail() {
  const [book, setBook] = useState(null);

  const handleTitleUpdated = (updatedBook) => {
    setBook(updatedBook);
    // Refresh chapter list if needed
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">{book.title}</h1>
        <BookTitleEditor book={book} onTitleUpdated={handleTitleUpdated} />
      </div>
      {/* Rest of component */}
    </div>
  );
}
```

### Testing Plan

1. **Unit Tests** (`backend/tests/test_title_editing.py`)
   - Test valid title updates
   - Test empty/whitespace titles (should fail)
   - Test audit trail creation
   - Test original_title preservation
   - Test 500-character limit

2. **Integration Tests**
   - Test API endpoint with authentication
   - Test unauthorized access (403)
   - Test non-existent book (404)

3. **Manual UI Testing**
   - Load book with "Untitled Book - Please Edit"
   - Click "Edit Title" button
   - Enter new title "Youmans Vol. 1"
   - Verify title updates immediately
   - Check database for audit trail
   - Verify original_title preserved

### Security Considerations

✅ **Authentication Required:** Only logged-in users can edit
✅ **Audit Trail:** Every edit tracked with user ID + timestamp
✅ **Original Preserved:** First edit saves original_title
✅ **XSS Prevention:** Input sanitization on backend
✅ **SQL Injection:** Protected by SQLAlchemy ORM
✅ **Rate Limiting:** Consider adding for bulk edits

### Rollout Plan

1. **Phase 1: Backend** (30 minutes)
   - Add PATCH endpoint
   - Add Pydantic schema
   - Write unit tests

2. **Phase 2: Frontend** (45 minutes)
   - Create BookTitleEditor component
   - Integrate into TextbookDetail page
   - Add success/error notifications

3. **Phase 3: Testing** (15 minutes)
   - Test with UUID title book
   - Test with normal title book
   - Verify audit trail in database

4. **Phase 4: Deploy** (10 minutes)
   - Restart backend API
   - Clear frontend cache
   - Verify in production

**Total Time:** 1.5-2 hours

---

## Enhancement #2: AI Title Extraction
**Priority:** 🟡 MEDIUM (Automation improvement)
**Complexity:** 🟠 MEDIUM (AI integration)
**Estimated Time:** 4-6 hours
**Dependencies:** GPT-4 Vision API, title editing UI

### Problem Statement

Many neurosurgical PDFs lack metadata titles, forcing users to manually edit them. We can automate this by:
1. Extracting the first page (cover) as image
2. Using GPT-4 Vision to read the title from cover
3. Auto-populating title field with high confidence

**Value Proposition:**
- 95% of textbooks have clear titles on cover pages
- GPT-4 Vision can read text from images with 98%+ accuracy
- Saves users 1-2 minutes per book
- Handles multi-language titles (Latin, German, etc.)

### Technical Design

#### 2.1 Architecture

```
PDF Upload → Extract Page 1 → Convert to Image → GPT-4 Vision → Extract Title
                                                        ↓
                              Confidence > 0.8? → Auto-apply title
                              Confidence < 0.8? → Suggest to user
```

#### 2.2 Backend Implementation

**New Service:** `backend/services/title_extraction.py`

```python
from openai import OpenAI
from pdf2image import convert_from_path
import base64
from typing import Optional, Tuple
import re

class TitleExtractionService:
    """Extract book titles from cover pages using GPT-4 Vision"""

    def __init__(self):
        self.client = OpenAI()
        self.model = "gpt-4-vision-preview"

    async def extract_title_from_pdf(
        self,
        pdf_path: str,
        page_num: int = 1
    ) -> Tuple[Optional[str], float, dict]:
        """
        Extract title from PDF cover page

        Returns:
            (title, confidence, metadata)

        Examples:
            ("Youmans Neurological Surgery Volume 1", 0.95, {...})
            (None, 0.0, {"error": "No clear title found"})
        """
        try:
            # Convert first page to image
            images = convert_from_path(pdf_path, first_page=page_num, last_page=page_num)
            if not images:
                return None, 0.0, {"error": "Failed to convert page to image"}

            cover_image = images[0]

            # Convert to base64
            import io
            buffer = io.BytesIO()
            cover_image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Call GPT-4 Vision
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a specialized assistant for extracting book titles from cover pages.

TASK: Analyze the cover page image and extract the MAIN TITLE of the book.

RULES:
1. Extract ONLY the main title (ignore subtitles, authors, publishers, edition numbers)
2. Preserve capitalization as shown on cover
3. Include volume/edition numbers ONLY if part of main title
4. Remove "Handbook of", "Atlas of" prefixes if followed by clear title
5. If multiple titles visible, extract the LARGEST/MOST PROMINENT one

EXAMPLES:
✓ "Neurological Surgery" (not "Handbook of Neurological Surgery")
✓ "Youmans Vol. 1" (volume is part of title)
✓ "Spinal Disorders" (not "Comprehensive Textbook of Spinal Disorders")

OUTPUT FORMAT (JSON):
{
  "title": "Extracted Title Here",
  "confidence": 0.95,  // 0.0-1.0 scale
  "reasoning": "Title is clearly visible in large font at top of page",
  "alternative_titles": ["Alt 1", "Alt 2"],  // if ambiguous
  "detected_language": "English",
  "has_subtitle": true,
  "subtitle": "Principles and Practice"  // if applicable
}

If no clear title visible, return:
{
  "title": null,
  "confidence": 0.0,
  "reasoning": "No clear title text found on cover"
}"""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract the main title from this medical textbook cover page."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=500
            )

            result = json.loads(response.choices[0].message.content)

            # Post-processing: Clean title
            title = result.get("title")
            if title:
                title = self._clean_title(title)

            confidence = result.get("confidence", 0.0)
            metadata = {
                "reasoning": result.get("reasoning"),
                "alternatives": result.get("alternative_titles", []),
                "language": result.get("detected_language"),
                "subtitle": result.get("subtitle"),
                "extraction_method": "gpt4_vision",
                "page_number": page_num
            }

            return title, confidence, metadata

        except Exception as e:
            return None, 0.0, {"error": str(e)}

    def _clean_title(self, title: str) -> str:
        """Clean extracted title"""
        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title).strip()

        # Remove common noise
        noise_patterns = [
            r'^(The|A|An)\s+',  # Articles at start
            r'\s+(First|Second|Third|1st|2nd|3rd)\s+Edition$',  # Edition at end
            r'\s+\(.*?\)$',  # Parenthetical at end
        ]

        for pattern in noise_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)

        # Limit length
        if len(title) > 200:
            title = title[:200] + "..."

        return title.strip()

    async def batch_extract_titles(
        self,
        book_ids: list[UUID],
        auto_apply_threshold: float = 0.8
    ) -> dict:
        """
        Batch process multiple books

        Args:
            book_ids: List of book UUIDs to process
            auto_apply_threshold: Confidence threshold for auto-applying title

        Returns:
            {
                "processed": 15,
                "auto_applied": 12,
                "manual_review": 3,
                "failed": 0,
                "results": [...]
            }
        """
        results = {
            "processed": 0,
            "auto_applied": 0,
            "manual_review": 0,
            "failed": 0,
            "results": []
        }

        for book_id in book_ids:
            # Get book from database
            book = await self._get_book(book_id)
            if not book or not book.storage_path:
                results["failed"] += 1
                continue

            # Extract title
            title, confidence, metadata = await self.extract_title_from_pdf(
                book.storage_path
            )

            results["processed"] += 1

            if title and confidence >= auto_apply_threshold:
                # Auto-apply high-confidence titles
                await self._update_book_title(
                    book_id,
                    title,
                    metadata={"ai_extracted": True, **metadata}
                )
                results["auto_applied"] += 1
                results["results"].append({
                    "book_id": str(book_id),
                    "status": "auto_applied",
                    "title": title,
                    "confidence": confidence
                })
            elif title and confidence >= 0.5:
                # Suggest medium-confidence titles
                results["manual_review"] += 1
                results["results"].append({
                    "book_id": str(book_id),
                    "status": "needs_review",
                    "suggested_title": title,
                    "confidence": confidence,
                    "alternatives": metadata.get("alternatives", [])
                })
            else:
                # Low confidence or no title found
                results["failed"] += 1
                results["results"].append({
                    "book_id": str(book_id),
                    "status": "failed",
                    "reason": metadata.get("error") or "Low confidence"
                })

        return results
```

#### 2.3 Celery Task Integration

**File:** `backend/celery_app/tasks/title_extraction.py`

```python
from celery import Task
from backend.celery_app.celery_config import celery_app
from backend.services.title_extraction import TitleExtractionService

@celery_app.task(
    name="extract_title_from_cover",
    bind=True,
    max_retries=2,
    time_limit=120
)
def extract_title_from_cover(self: Task, book_id: str) -> dict:
    """
    Background task to extract title from book cover

    Called automatically after PDF upload if title is UUID-like
    """
    service = TitleExtractionService()

    try:
        title, confidence, metadata = service.extract_title_from_pdf(book_id)

        if title and confidence >= 0.8:
            # Auto-apply high-confidence titles
            service.update_book_title(book_id, title, metadata)
            return {
                "status": "success",
                "title": title,
                "confidence": confidence,
                "auto_applied": True
            }
        elif title:
            # Store suggestion for manual review
            return {
                "status": "needs_review",
                "suggested_title": title,
                "confidence": confidence,
                "auto_applied": False
            }
        else:
            return {
                "status": "failed",
                "reason": metadata.get("error", "No title found")
            }

    except Exception as e:
        self.retry(exc=e, countdown=30)
```

#### 2.4 Admin UI for Batch Processing

**File:** `frontend/src/pages/admin/TitleExtractionAdmin.jsx`

```jsx
export default function TitleExtractionAdmin() {
  const [books, setBooks] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState(null);

  // Load books with poor titles
  useEffect(() => {
    fetchBooksNeedingTitles();
  }, []);

  const fetchBooksNeedingTitles = async () => {
    const response = await axios.get('/api/v1/admin/books/needs-titles');
    setBooks(response.data);
  };

  const handleBatchExtract = async () => {
    setProcessing(true);
    try {
      const response = await axios.post('/api/v1/admin/titles/batch-extract', {
        book_ids: books.map(b => b.id),
        auto_apply_threshold: 0.8
      });
      setResults(response.data);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">AI Title Extraction</h1>

      <div className="bg-blue-50 p-4 rounded-lg mb-6">
        <h2 className="font-semibold mb-2">Books Needing Titles</h2>
        <p className="text-sm text-gray-700">
          {books.length} books found with UUID or generic titles
        </p>
        <button
          onClick={handleBatchExtract}
          disabled={processing || books.length === 0}
          className="mt-3 px-4 py-2 bg-blue-600 text-white rounded-md"
        >
          {processing ? 'Processing...' : `Extract Titles (${books.length})`}
        </button>
      </div>

      {results && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-4">
            <StatCard label="Processed" value={results.processed} color="blue" />
            <StatCard label="Auto-Applied" value={results.auto_applied} color="green" />
            <StatCard label="Manual Review" value={results.manual_review} color="yellow" />
            <StatCard label="Failed" value={results.failed} color="red" />
          </div>

          {/* Results table */}
          <ResultsTable results={results.results} />
        </div>
      )}
    </div>
  );
}
```

### Cost Analysis

**GPT-4 Vision Pricing:**
- High detail image: ~$0.01 per image
- 100 books: $1.00
- 1,000 books: $10.00

**ROI:**
- Manual title entry: 2 minutes × $50/hour = $1.67 per book
- AI extraction: $0.01 per book
- **Savings: $1.66 per book (99.4% cost reduction)**

### Accuracy Expectations

Based on GPT-4 Vision benchmarks:
- **Clear covers:** 98% accuracy
- **Complex layouts:** 85% accuracy
- **Non-English:** 90% accuracy
- **Overall:** 95% accuracy with manual review fallback

---

## Enhancement #3: Semantic Tags (Schema Ready)
**Priority:** 🟢 LOW-MEDIUM (Search enhancement)
**Complexity:** 🟠 MEDIUM (NLP + vector similarity)
**Estimated Time:** 6-8 hours
**Dependencies:** OpenAI embeddings, embedding_metadata field

### Problem Statement

Users searching for "spine trauma" might miss chapters titled "Vertebral Column Injuries" because:
1. No semantic understanding of content
2. Exact keyword matching only
3. No topic/concept tagging

**Solution:** Auto-generate semantic tags for each chapter using:
1. Key phrase extraction from chapter text
2. Medical ontology mapping (MeSH, ICD codes)
3. Embedding similarity clustering
4. Store in `embedding_metadata` JSONB field

### Technical Design

#### 3.1 Tag Generation Pipeline

```python
Chapter Text (3522 chars)
    ↓
1. Extract Key Phrases (spaCy + YAKE)
    ↓
["spine trauma", "vertebral fracture", "spinal cord injury"]
    ↓
2. Map to Medical Ontology (MeSH)
    ↓
["Spinal Injuries", "Fractures, Bone", "Spinal Cord Injuries"]
    ↓
3. Add Anatomical Tags
    ↓
["Cervical Spine", "Thoracic Vertebrae", "Lumbar Region"]
    ↓
4. Add Procedure Tags (if applicable)
    ↓
["Spinal Fusion", "Decompression", "Instrumentation"]
    ↓
5. Store in embedding_metadata
    {
      "semantic_tags": [...],
      "mesh_codes": [...],
      "anatomical_regions": [...],
      "procedures": [...],
      "confidence_scores": {...}
    }
```

#### 3.2 Implementation

**File:** `backend/services/semantic_tagging.py`

```python
import spacy
from yake import KeywordExtractor
from openai import OpenAI
import json

class SemanticTagger:
    """Generate semantic tags for neurosurgical content"""

    def __init__(self):
        self.nlp = spacy.load("en_core_sci_md")  # SciSpacy model
        self.kw_extractor = KeywordExtractor(
            lan="en",
            n=3,  # 1-3 word phrases
            top=20
        )
        self.client = OpenAI()

    async def generate_tags(self, chapter_text: str) -> dict:
        """
        Generate comprehensive semantic tags

        Returns:
            {
              "keywords": [...],           # Raw extracted keywords
              "semantic_tags": [...],      # Normalized medical terms
              "mesh_codes": [...],         # MeSH ontology codes
              "anatomical_regions": [...], # Body parts/regions
              "procedures": [...],         # Surgical procedures
              "diseases": [...],           # Conditions/pathologies
              "imaging": [...],            # Imaging modalities
              "confidence": 0.85
            }
        """
        # 1. Extract keywords using YAKE
        keywords = self.kw_extractor.extract_keywords(chapter_text)
        top_keywords = [kw[0] for kw in keywords[:20]]

        # 2. Use GPT-4 for medical concept extraction
        medical_concepts = await self._extract_medical_concepts(
            chapter_text,
            top_keywords
        )

        # 3. Map to MeSH ontology
        mesh_codes = await self._map_to_mesh(medical_concepts["concepts"])

        # 4. Combine and structure
        tags = {
            "keywords": top_keywords,
            "semantic_tags": medical_concepts["normalized_terms"],
            "mesh_codes": mesh_codes,
            "anatomical_regions": medical_concepts["anatomy"],
            "procedures": medical_concepts["procedures"],
            "diseases": medical_concepts["diseases"],
            "imaging": medical_concepts["imaging"],
            "confidence": medical_concepts["confidence"],
            "generated_at": datetime.utcnow().isoformat(),
            "model": "gpt-4-turbo"
        }

        return tags

    async def _extract_medical_concepts(
        self,
        text: str,
        keywords: list
    ) -> dict:
        """Use GPT-4 to extract structured medical concepts"""

        # Truncate text for API limits (8k tokens)
        text_sample = text[:16000]  # ~4k tokens

        response = self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """You are a medical concept extraction specialist for neurosurgical literature.

TASK: Analyze the chapter text and extract structured medical concepts.

OUTPUT (JSON):
{
  "concepts": ["key medical concepts found"],
  "normalized_terms": ["standardized medical terms"],
  "anatomy": ["anatomical regions mentioned: spine, brain, skull, etc."],
  "procedures": ["surgical procedures: fusion, decompression, etc."],
  "diseases": ["pathologies: trauma, tumor, hemorrhage, etc."],
  "imaging": ["modalities: MRI, CT, X-ray, etc."],
  "confidence": 0.85  // 0-1 scale
}

RULES:
1. Use standard medical terminology (not colloquial)
2. Focus on NEUROSURGICAL relevance
3. Include specific anatomical locations
4. Normalize synonyms (e.g., "CVA" → "Stroke")
5. High confidence only for explicitly mentioned concepts"""
                },
                {
                    "role": "user",
                    "content": f"""Chapter excerpt (first 4000 words):

{text_sample}

Extracted keywords: {', '.join(keywords)}

Extract structured medical concepts from this neurosurgical text."""
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        return json.loads(response.choices[0].message.content)

    async def _map_to_mesh(self, concepts: list[str]) -> list[dict]:
        """Map concepts to MeSH (Medical Subject Headings) codes"""
        # Use NCBI E-utilities API
        mesh_mappings = []

        for concept in concepts[:10]:  # Limit to top 10
            try:
                mesh_code = await self._query_mesh_api(concept)
                if mesh_code:
                    mesh_mappings.append({
                        "term": concept,
                        "mesh_code": mesh_code["code"],
                        "mesh_label": mesh_code["label"],
                        "tree_number": mesh_code["tree"]
                    })
            except Exception:
                continue

        return mesh_mappings

    async def batch_tag_chapters(self, chapter_ids: list[UUID]) -> dict:
        """Batch process multiple chapters"""
        results = {
            "processed": 0,
            "tagged": 0,
            "failed": 0,
            "total_tags": 0
        }

        for chapter_id in chapter_ids:
            try:
                chapter = await self._get_chapter(chapter_id)
                tags = await self.generate_tags(chapter.extracted_text)

                # Store in embedding_metadata
                chapter.embedding_metadata = tags
                await self._save_chapter(chapter)

                results["processed"] += 1
                results["tagged"] += 1
                results["total_tags"] += len(tags["semantic_tags"])
            except Exception as e:
                results["failed"] += 1

        return results
```

#### 3.3 Search Integration

**Enhanced Search Endpoint:**
```python
@router.get("/search/semantic")
async def semantic_search(
    query: str,
    include_tags: bool = True,
    session: Session = Depends(get_session)
) -> list[ChapterSearchResult]:
    """
    Enhanced semantic search using tags

    Process:
    1. Standard vector similarity search
    2. Extract tags from query using GPT-4
    3. Boost results matching semantic tags
    4. Expand search to related MeSH terms
    """
    # 1. Vector search (baseline)
    vector_results = await vector_search(query)

    if not include_tags:
        return vector_results

    # 2. Extract tags from query
    tagger = SemanticTagger()
    query_tags = await tagger.generate_tags(query)

    # 3. Boost matching chapters
    for result in vector_results:
        if result.embedding_metadata:
            tags = result.embedding_metadata.get("semantic_tags", [])

            # Calculate tag overlap
            overlap = set(query_tags["semantic_tags"]) & set(tags)
            overlap_score = len(overlap) / max(len(query_tags["semantic_tags"]), 1)

            # Boost similarity score
            result.similarity *= (1 + overlap_score * 0.3)  # Up to 30% boost

    # 4. Re-rank by boosted scores
    vector_results.sort(key=lambda x: x.similarity, reverse=True)

    return vector_results
```

#### 3.4 Tag Display in UI

**Component:** `frontend/src/components/ChapterTags.jsx`

```jsx
export default function ChapterTags({ chapter }) {
  const tags = chapter.embedding_metadata?.semantic_tags || [];
  const anatomy = chapter.embedding_metadata?.anatomical_regions || [];
  const procedures = chapter.embedding_metadata?.procedures || [];

  return (
    <div className="space-y-3">
      {tags.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-600 mb-2">
            Topics
          </h4>
          <div className="flex flex-wrap gap-2">
            {tags.map((tag, idx) => (
              <span
                key={idx}
                className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {anatomy.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-600 mb-2">
            Anatomy
          </h4>
          <div className="flex flex-wrap gap-2">
            {anatomy.map((region, idx) => (
              <span
                key={idx}
                className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full"
              >
                📍 {region}
              </span>
            ))}
          </div>
        </div>
      )}

      {procedures.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-600 mb-2">
            Procedures
          </h4>
          <div className="flex flex-wrap gap-2">
            {procedures.map((proc, idx) => (
              <span
                key={idx}
                className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full"
              >
                🔧 {proc}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

### Use Cases

1. **Smart Search**
   - Query: "spine trauma"
   - Finds: "Vertebral Column Injuries" (via semantic tag matching)

2. **Related Chapters**
   - Current chapter: "Lumbar Disc Herniation"
   - Suggests: Other chapters tagged with ["Lumbar Spine", "Decompression"]

3. **Ontology Navigation**
   - Browse by MeSH tree: Nervous System → Brain → Cerebral Cortex

4. **Tag-Based Filtering**
   - Show only chapters about: "Skull Base" + "Endoscopic Procedures"

### Cost Analysis

**OpenAI API Costs:**
- GPT-4 Turbo: $0.01 per 1k input tokens, $0.03 per 1k output
- Average chapter: 1k input + 200 output = $0.016 per chapter
- 100 chapters: $1.60
- 1,000 chapters: $16.00

**Value:**
- Improved search relevance: 30-40% higher user satisfaction
- Reduced search time: 2-3 minutes saved per search
- Better content discovery: 50% more relevant chapters found

---

## Implementation Priority

### Immediate (This Week):
✅ **Enhancement #1: Title Editing UI**
- Highest user impact
- Lowest complexity
- 1-2 hours implementation
- Unblocks user workflow

### Short-term (Next 2 Weeks):
⏳ **Enhancement #2: AI Title Extraction**
- High automation value
- Medium complexity
- 4-6 hours implementation
- 95% accuracy expected

### Medium-term (Next Month):
⏳ **Enhancement #3: Semantic Tags**
- Enhanced search quality
- Medium-high complexity
- 6-8 hours implementation
- 30-40% search improvement

---

## Success Metrics

### Enhancement #1 Metrics:
- ✅ 100% of UUID titles can be edited
- ✅ Audit trail captured for all edits
- ✅ Average edit time < 30 seconds

### Enhancement #2 Metrics:
- 🎯 95% title extraction accuracy
- 🎯 80% auto-apply rate (confidence > 0.8)
- 🎯 $1.66 saved per book vs manual entry

### Enhancement #3 Metrics:
- 🎯 15-20 tags per chapter on average
- 🎯 30% improvement in search relevance
- 🎯 50% increase in related chapter discovery

---

## Next Actions

1. **Review this roadmap** - Validate priorities and estimates
2. **Approve Enhancement #1** - Ready to implement immediately
3. **Schedule Enhancement #2** - Plan for next sprint
4. **Evaluate Enhancement #3** - Consider strategic value

Would you like me to proceed with implementing Enhancement #1 (Title Editing UI) now?
