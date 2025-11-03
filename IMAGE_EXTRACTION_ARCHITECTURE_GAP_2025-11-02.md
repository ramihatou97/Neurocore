# Image Extraction Architecture Gap - Critical Finding

**Date:** November 2, 2025
**Status:** 🚨 CRITICAL - Image extraction not working for textbooks
**Impact:** All textbook uploads missing image analysis and Claude Vision integration

---

## Executive Summary

The system has **two separate PDF processing tracks** that are not integrated:

1. **Legacy PDF Track** (`pdfs` table) - ✅ HAS image extraction
2. **Textbook Track** (`pdf_books` → `pdf_chapters`) - ❌ NO image extraction

**Result:** "Keyhole Approaches in Neurosurgery" (310 pages, image-rich) shows **0 images extracted** because textbook uploads bypass the image extraction pipeline entirely.

---

## Root Cause Analysis

### Architecture Discovery

#### Track 1: Legacy PDF Upload (Working)
**Endpoint:** `POST /api/v1/pdfs/upload`
**Location:** `backend/api/pdf_routes.py:451`
**Database:** `pdfs` table
**Pipeline:** `start_pdf_processing()` → `process_pdf_async()` → Celery chain

```python
# backend/services/background_tasks.py:86-93
workflow = chain(
    extract_text_task.si(pdf_id),         # Step 1: 20% progress
    extract_images_task.si(pdf_id),       # Step 2: 40% progress ⭐
    analyze_images_task.si(pdf_id),       # Step 3: 60% progress (Claude Vision)
    generate_embeddings_task.si(pdf_id),  # Step 4: 80% progress
    extract_citations_task.si(pdf_id),    # Step 5: 100% progress
    finalize_pdf_processing.si(pdf_id)
)
```

#### Track 2: Textbook Upload (Missing Image Extraction)
**Endpoint:** `POST /api/v1/textbooks/upload`
**Location:** `backend/api/textbook_routes.py:285`
**Database:** `pdf_books` → `pdf_chapters`
**Pipeline:** Manual chapter processing + selective task queuing

```python
# backend/api/textbook_routes.py:351-406
# Tasks queued:
1. ✅ generate_chapter_embeddings.delay(chapter_id)  # Line 361
2. ✅ check_for_duplicates.delay(chapter_id)         # Line 373
3. ✅ extract_title_from_cover.delay(book_id)        # Line 399 (conditional)
4. ❌ extract_images_task - NOT QUEUED
5. ❌ analyze_images_task - NOT QUEUED
```

---

## Evidence: "Keyhole Approaches" Case Study

### Book Details
```sql
SELECT id, title, original_title, total_pages, uploaded_at
FROM pdf_books
WHERE id = 'f2e1cd71-2db5-4ba1-a5ba-7206b74f3b2b';
```

**Results:**
- **Title:** "Keyhole Approaches in Neurosurgery" (edited from UUID)
- **Original Title:** `6b24de89-ca05-439b-a36a-a6cdd713ae89` (UUID)
- **Total Pages:** 310
- **Uploaded:** 2025-11-01 01:36:00
- **File Path:** `/data/pdfs/2025/11/01/6b24de89-ca05-439b-a36a-a6cdd713ae89.pdf`
- **File Size:** 16 MB

### Chapter Processing Status
```sql
SELECT COUNT(*) as chapters,
       AVG(word_count)::int as avg_words,
       COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embeddings
FROM pdf_chapters
WHERE book_id = 'f2e1cd71-2db5-4ba1-a5ba-7206b74f3b2b';
```

**Results:**
- ✅ 13 chapters extracted
- ✅ 6,046 avg words per chapter
- ✅ 13/13 chapters have embeddings
- ✅ Text extraction working
- ❌ **0 images in `images` table**

### Image Extraction Status
```sql
SELECT COUNT(*) FROM images
WHERE pdf_id IN (
  SELECT id FROM pdfs WHERE file_path LIKE '%6b24de89%'
);
```

**Result:** `0 rows` - No images extracted

### pdfs Table Status
```sql
SELECT id, filename, text_extracted, images_extracted
FROM pdfs
WHERE file_path LIKE '%6b24de89%';
```

**Result:** `0 rows` - **No entry in pdfs table!**

**Conclusion:** Textbook upload never creates a record in the `pdfs` table, so the image extraction pipeline (which operates on `pdfs` table) is never triggered.

---

## Technical Details

### Database Schema

#### images Table (32 columns)
```sql
CREATE TABLE images (
  id UUID PRIMARY KEY,
  pdf_id UUID NOT NULL,  -- ⚠️ Links to pdfs.id, NOT pdf_books.id!
  page_number INTEGER,
  image_index_on_page INTEGER,
  file_path VARCHAR(1000),

  -- Claude Vision Analysis Fields (24 fields)
  ai_description TEXT,
  image_type VARCHAR(100),
  anatomical_structures TEXT[],
  clinical_context TEXT,
  quality_score REAL,
  confidence_score REAL,
  ocr_text TEXT,
  analysis_metadata JSONB,

  -- Vector Search
  embedding VECTOR(1536),

  -- ... 19 more columns
  FOREIGN KEY (pdf_id) REFERENCES pdfs(id) ON DELETE CASCADE
);
```

**Problem:** `pdf_id` references `pdfs` table, but textbooks create records in `pdf_books` table with no link to `pdfs`.

#### Relationship Gap
```
Current Architecture:

Legacy Track:
pdfs (id, file_path, images_extracted)
  ↓ [1:N]
images (pdf_id → pdfs.id)

Textbook Track (Isolated):
pdf_books (id, file_path, total_pages)
  ↓ [1:N]
pdf_chapters (book_id → pdf_books.id)
  ↓ [NO LINK TO IMAGES]
(images table unreachable)
```

---

## Impact Assessment

### Books Affected
**Query:** All books uploaded via textbook endpoint
```sql
SELECT
  COUNT(*) as total_books,
  SUM(total_pages) as total_pages,
  COUNT(DISTINCT id) as books_without_images
FROM pdf_books
WHERE id NOT IN (
  SELECT DISTINCT book_id FROM pdf_chapters pc
  WHERE EXISTS (
    SELECT 1 FROM images WHERE pdf_id = ANY(
      SELECT id FROM pdfs WHERE file_path LIKE '%' || pc.id::text || '%'
    )
  )
);
```

Expected: **All textbook uploads have 0 images extracted**

### Features Broken

#### ❌ Chapter 7: Image Integration (Stage 7)
**Location:** `backend/services/chapter_orchestrator.py:896-1012`
- Cannot find relevant images for generated chapters
- Image search returns empty results
- Captions not generated

#### ❌ Claude Vision Analysis
**Location:** `backend/services/image_analysis_service.py`
- 24-field analysis never runs
- `anatomical_structures` never populated
- `clinical_context` never extracted
- `quality_score` never calculated

#### ❌ Image Embeddings
**Location:** `backend/services/embedding_service.py`
- Image embeddings never generated
- Semantic image search unavailable
- Multi-modal search (text + images) broken

#### ❌ Frontend Image Display
**Components:**
- `TextbookChapterDetail.jsx` - Would show images if they existed
- `EmbeddingHeatmap.jsx` - Cannot visualize image embeddings

---

## Solution Options

### Option 1: Create pdfs Entry for Each Textbook Upload ⭐ RECOMMENDED
**Approach:** Extend textbook upload to create corresponding `pdfs` record

**Implementation:**
```python
# backend/api/textbook_routes.py:333-350 (after PDF saved)

# Create pdfs table entry for image extraction pipeline
from backend.database.models import PDF

pdf_record = PDF(
    id=uuid_module.uuid4(),
    file_path=file_path,
    filename=original_filename,
    file_size=len(file_content),
    uploaded_by=current_user.id,
    indexing_status="pending_images"
)
db.add(pdf_record)
db.commit()

# Store pdf_id in pdf_books for reference
book.pdf_id = pdf_record.id  # Requires migration: ALTER TABLE pdf_books ADD COLUMN pdf_id UUID
db.commit()

# Queue image extraction pipeline
from backend.services.background_tasks import extract_images_task, analyze_images_task
extract_images_task.delay(str(pdf_record.id))
```

**Pros:**
- ✅ Minimal changes to existing code
- ✅ Reuses battle-tested image extraction pipeline
- ✅ No changes to `images` table schema
- ✅ Existing Celery tasks work as-is

**Cons:**
- Requires migration: `ALTER TABLE pdf_books ADD COLUMN pdf_id UUID`
- Creates some data duplication (file_path in both tables)

**Estimated Effort:** 2-3 hours
- Migration: 30 min
- Code changes: 1 hour
- Testing: 1-2 hours

---

### Option 2: Create Chapter-Level Image Extraction
**Approach:** Extract images per chapter instead of per PDF

**Implementation:**
```python
# New table: chapter_images
CREATE TABLE chapter_images (
  id UUID PRIMARY KEY,
  chapter_id UUID REFERENCES pdf_chapters(id),
  page_number INTEGER,
  image_index_on_page INTEGER,
  -- ... all other image fields
);

# New Celery task
@celery_app.task
def extract_chapter_images_task(chapter_id: str):
    chapter = db.query(PDFChapter).get(chapter_id)
    # Extract images from chapter.start_page to chapter.end_page
    # Store in chapter_images table
```

**Pros:**
- ✅ More granular (chapter-level)
- ✅ Better alignment with new architecture
- ✅ No link to legacy `pdfs` table

**Cons:**
- ⚠️ Requires new table `chapter_images`
- ⚠️ Requires new Celery task
- ⚠️ Need to update chapter_orchestrator.py image search
- ⚠️ More complex migration path

**Estimated Effort:** 6-8 hours
- Schema design: 1 hour
- Migration: 1 hour
- New Celery tasks: 2-3 hours
- Update chapter orchestrator: 2-3 hours
- Testing: 2 hours

---

### Option 3: Unified PDF Processing (Major Refactor)
**Approach:** Merge both tracks into single processing pipeline

**Too large for immediate implementation - defer to Phase 6+**

---

## Recommended Action Plan

### Phase 1: Quick Fix (Today) ⏱️ 2-3 hours
1. ✅ Add `pdf_id` column to `pdf_books` table
2. ✅ Update textbook upload endpoint to create `pdfs` record
3. ✅ Queue `extract_images_task` + `analyze_images_task`
4. ✅ Test with "Keyhole Approaches" book (re-upload or trigger manually)

### Phase 2: Backfill Existing Books (Tomorrow) ⏱️ 4-6 hours
1. Create script to process existing textbooks
2. Generate `pdfs` records for all books in `pdf_books`
3. Trigger image extraction for all historical uploads
4. Monitor Celery workers and API logs

### Phase 3: Verification (Day 3) ⏱️ 2 hours
1. Run IMAGE_PIPELINE_TEST_GUIDE.md verification
2. Check image counts for all books
3. Verify Claude Vision analysis quality
4. Test image integration in chapter generation
5. Document results

---

## Migration Script (Phase 1)

### Migration 012: Add pdf_id to pdf_books
```sql
-- 012_link_books_to_pdfs.sql

BEGIN;

-- Add pdf_id column to pdf_books (nullable for now)
ALTER TABLE pdf_books
ADD COLUMN pdf_id UUID;

-- Add foreign key constraint
ALTER TABLE pdf_books
ADD CONSTRAINT fk_pdf_books_pdf_id
FOREIGN KEY (pdf_id) REFERENCES pdfs(id)
ON DELETE SET NULL;

-- Create index for faster lookups
CREATE INDEX idx_pdf_books_pdf_id ON pdf_books(pdf_id);

COMMIT;
```

---

## Code Changes (Phase 1)

### File: backend/api/textbook_routes.py

**Location:** Lines 333-350 (after `processor.process_pdf()`)

```python
# AFTER line 341: result = processor.process_pdf(...)

# ========== NEW CODE: Create pdfs entry for image extraction ==========
try:
    from backend.database.models import PDF

    # Create pdfs table entry to enable image extraction pipeline
    pdf_record = PDF(
        id=uuid_module.uuid4(),
        file_path=file_path,
        filename=original_filename,
        file_size_bytes=len(file_content),
        uploaded_by=current_user.id,
        indexing_status="pending_images",
        text_extracted=True  # Text already extracted by textbook processor
    )
    db.add(pdf_record)
    db.commit()

    # Link book to pdf record
    book = db.query(PDFBook).filter(
        PDFBook.id == uuid_module.UUID(book_id)
    ).first()
    if book:
        book.pdf_id = pdf_record.id
        db.commit()

        logger.info(
            f"Created pdfs record {pdf_record.id} for book {book_id}, "
            f"queuing image extraction"
        )

    # Queue image extraction pipeline
    from backend.services.background_tasks import (
        extract_images_task,
        analyze_images_task,
        generate_embeddings_task
    )

    # Queue image extraction (already has text)
    extract_images_task.delay(str(pdf_record.id))

    logger.info(f"Queued image extraction pipeline for PDF {pdf_record.id}")

except Exception as e:
    logger.error(
        f"Failed to queue image extraction for book {book_id}: {str(e)}",
        exc_info=True
    )
    # Don't fail the upload if image extraction queueing fails
# ========== END NEW CODE ==========

# Continue with existing code (line 351: Queue embedding tasks...)
```

---

## Testing Commands (Phase 1)

### 1. Apply Migration
```bash
# Apply migration 012
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb \
  -f /app/backend/database/migrations/012_link_books_to_pdfs.sql

# Verify column added
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'pdf_books' AND column_name = 'pdf_id';"
```

### 2. Test with Existing Book
```bash
# Check current state
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  b.id as book_id,
  b.title,
  b.file_path,
  b.pdf_id,
  (SELECT COUNT(*) FROM images i
   JOIN pdfs p ON i.pdf_id = p.id
   WHERE b.pdf_id = p.id) as image_count
FROM pdf_books b
WHERE b.id = 'f2e1cd71-2db5-4ba1-a5ba-7206b74f3b2b';"
```

### 3. Manually Trigger Image Extraction (Testing)
```python
# Create script: test_trigger_image_extraction.py

import uuid
from backend.database.connection import db
from backend.database.models import PDF, PDFBook
from backend.services.background_tasks import extract_images_task

# Get the book
book_id = uuid.UUID('f2e1cd71-2db5-4ba1-a5ba-7206b74f3b2b')
session = db.get_session()
book = session.query(PDFBook).get(book_id)

# Create pdfs entry
pdf_record = PDF(
    id=uuid.uuid4(),
    file_path=book.file_path,
    filename=book.title + ".pdf",
    file_size_bytes=book.file_size_bytes,
    uploaded_by=book.uploaded_by,
    indexing_status="pending_images",
    text_extracted=True
)
session.add(pdf_record)

# Link book to pdf
book.pdf_id = pdf_record.id
session.commit()

print(f"Created PDF record: {pdf_record.id}")
print(f"Linked to book: {book.id}")

# Queue image extraction
extract_images_task.delay(str(pdf_record.id))
print(f"Queued image extraction task for PDF: {pdf_record.id}")
```

**Run:**
```bash
docker exec neurocore-api python3 test_trigger_image_extraction.py
```

### 4. Monitor Progress
```bash
# Watch Celery Flower
open http://localhost:5555

# Watch database for images
watch -n 5 'docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  COUNT(*) as total_images,
  COUNT(CASE WHEN ai_description IS NOT NULL THEN 1 END) as analyzed,
  AVG(quality_score)::numeric(3,2) as avg_quality
FROM images
WHERE created_at > NOW() - INTERVAL '\''1 hour'\'';"'
```

---

## Success Criteria

### ✅ Phase 1 Complete When:
- [ ] Migration 012 applied successfully
- [ ] `pdf_books.pdf_id` column exists
- [ ] Textbook upload creates `pdfs` record
- [ ] Image extraction task queued on upload
- [ ] "Keyhole Approaches" book has >0 images extracted
- [ ] Claude Vision analysis runs on extracted images
- [ ] Image embeddings generated

### ✅ Phase 2 Complete When:
- [ ] All existing books have `pdf_id` populated
- [ ] All books have images extracted and analyzed
- [ ] Image counts match expectations (manual spot-check)
- [ ] No Celery task failures

### ✅ Phase 3 Complete When:
- [ ] IMAGE_PIPELINE_TEST_GUIDE.md verification passes
- [ ] Chapter generation includes relevant images
- [ ] Image captions generated correctly
- [ ] Frontend displays images properly

---

## Risk Assessment

### Low Risk ✅
- Creating `pdf_id` column (nullable, no data loss)
- Queuing image extraction tasks (idempotent)
- Testing with single book first

### Medium Risk ⚠️
- Celery worker load (may need to scale workers)
- Storage space (images + thumbnails)
- API costs (Claude Vision ~$0.01-0.02 per image)

### High Risk 🚨
- None identified (changes are additive, not destructive)

---

## Next Steps

**Immediate Actions:**
1. Review this document with team
2. Approve Option 1 implementation
3. Create Migration 012
4. Update textbook upload endpoint
5. Test with "Keyhole Approaches" book
6. Monitor results

**Questions to Resolve:**
1. Should we backfill existing books immediately or gradually?
2. Do we need to scale Celery workers for backfill?
3. What's the priority: fix new uploads first, or backfill old books?
4. Should we add a `/books/{book_id}/extract-images` manual trigger endpoint?

---

**Document Status:** Ready for Review
**Recommended Priority:** P0 - Critical (blocks image features entirely)
**Estimated Resolution Time:** 2-3 hours (Phase 1)
**Testing Required:** Yes (manual + automated)
