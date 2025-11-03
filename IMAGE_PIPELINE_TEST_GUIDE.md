# Image Pipeline End-to-End Test Guide

**Date:** November 3, 2025
**Purpose:** Verify the complete image pipeline from PDF upload to Claude Vision analysis
**Status:** Ready to test
**Prerequisites:** All systems operational ✅

---

## System Status Check ✅

Before starting, verify all components are ready:

### 1. Database Migrations
```bash
✅ Migration 010 applied (analysis_metadata column exists)
✅ Migration 011 applied (title editing fields exist)
✅ All 8 required columns verified in database
```

### 2. Celery Workers
```bash
✅ neurocore-celery-worker (Up 5 hours)
✅ neurocore-celery-worker-images (Up 5 hours)
✅ neurocore-celery-worker-embeddings (Up 5 hours)
✅ neurocore-celery-flower (Monitoring UI at :5555)
```

### 3. API Services
```bash
✅ Backend API: http://localhost:8002 (healthy)
✅ Frontend: http://localhost:3002
✅ Flower Monitoring: http://localhost:5555
```

---

## Image Pipeline Components

The complete pipeline consists of 5 Celery tasks:

### Task 1: `extract_text_task` (20% progress)
- Extracts text from all PDF pages
- Stores in `extracted_text` field
- **Location:** `pdf_service.py:extract_text_from_pdf()`

### Task 2: `extract_images_task` (40% progress)
- Extracts images using PyMuPDF
- Generates thumbnails
- Stores metadata: dimensions, format, file_size_bytes
- **Location:** `pdf_service.py:extract_images_from_pdf()`

### Task 3: `analyze_images_task` (60% progress) ⭐ CRITICAL
- **Claude Vision API** 24-field analysis per image
- Fields analyzed:
  1. `image_type` (MRI, CT, diagram, surgical_photo, etc.)
  2. `anatomical_structures` (array of structures identified)
  3. `clinical_context` (medical significance)
  4. `ai_description` (detailed description)
  5. `quality_score` (0.0-1.0)
  6. `confidence_score` (0.0-1.0)
  7. `ocr_text` (text extracted from image)
  8. `contains_text` (boolean)
  9-24. Additional metadata fields
- **Location:** `image_analysis_service.py:analyze_images_batch()`
- **Batch size:** Max 5 images concurrent

### Task 4: `generate_embeddings_task` (80% progress)
- OpenAI text-embedding-3-large (1536 dimensions)
- Embeds: ai_description + ocr_text + anatomical_structures
- **Location:** `embedding_service.py`

### Task 5: `extract_citations_task` (100% progress)
- Currently placeholder
- **Location:** `pdf_service.py:extract_citations()`

---

## Test Procedure

### STEP 1: Prepare Test PDF (5 minutes)

**Requirements for optimal testing:**
- Neurosurgical textbook or atlas
- Contains diverse image types:
  - ✅ MRI scans (T1, T2, FLAIR)
  - ✅ CT scans
  - ✅ Anatomical diagrams
  - ✅ Surgical photographs
  - ✅ Angiograms
  - ✅ Histology images
- PDF size: 10-50 MB (good balance)
- Pages: 20-100 pages ideal

**Recommended test files:**
- Neurosurgical Atlas PDFs
- Operative technique guides
- Clinical case reports with imaging

**Where to find:**
```bash
# Check if you have any suitable PDFs
find ~/Desktop -name "*.pdf" -size +10M -size -50M | head -5
```

---

### STEP 2: Upload via Frontend (2 minutes)

**Option A: Frontend Upload (Recommended)**

1. Open browser: http://localhost:3002
2. Navigate to "Textbooks" page
3. Click "Upload New Book" button
4. Select your image-rich PDF
5. Enter metadata:
   - Title: "Test - Neurosurgical Atlas"
   - Authors: (optional)
   - Publication Year: (optional)
6. Click "Upload"
7. You'll be redirected to the book detail page

**What happens next:**
- File uploaded to storage
- Database record created
- Celery task chain queued
- Progress updates via WebSocket

---

### STEP 3: Monitor Processing (10-15 minutes)

**Option A: Watch Celery Flower (Visual)**

1. Open http://localhost:5555
2. Click "Tasks" in navigation
3. Look for tasks:
   - `backend.services.background_tasks.extract_text_task`
   - `backend.services.background_tasks.extract_images_task`
   - `backend.services.background_tasks.analyze_images_task` ⭐
   - `backend.services.background_tasks.generate_embeddings_task`

**Option B: Monitor Database (Real-time)**

```bash
# Watch image extraction progress
watch -n 5 'docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  COUNT(*) as total_images,
  COUNT(CASE WHEN ai_description IS NOT NULL THEN 1 END) as analyzed_images,
  AVG(quality_score)::numeric(3,2) as avg_quality,
  COUNT(CASE WHEN anatomical_structures IS NOT NULL THEN 1 END) as with_structures
FROM images
WHERE created_at > NOW() - INTERVAL '\''30 minutes'\'';"
'
```

**Option C: Monitor API Logs**

```bash
# Watch API logs for processing updates
docker logs -f neurocore-api | grep -E "extract|analyze|embedding"
```

---

### STEP 4: Verify Image Extraction (5 minutes)

After `extract_images_task` completes (40% progress):

```bash
# Get the PDF/Book ID from upload
BOOK_ID="<your-book-id>"

# Check how many images were extracted
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  COUNT(*) as total_images,
  SUM(file_size_bytes) / 1024 / 1024 as total_size_mb,
  AVG(width)::int as avg_width,
  AVG(height)::int as avg_height,
  COUNT(DISTINCT format) as unique_formats
FROM images
WHERE pdf_id IN (
  SELECT id FROM pdfs WHERE id IN (
    SELECT DISTINCT pdf_id FROM pdf_chapters WHERE book_id = '${BOOK_ID}'
  )
);"
```

**Expected Results:**
```
total_images | total_size_mb | avg_width | avg_height | unique_formats
-------------+---------------+-----------+------------+----------------
         47  |          12.5 |       842 |        691 |              3
```

---

### STEP 5: Verify Claude Vision Analysis (10 minutes)

After `analyze_images_task` completes (60% progress):

```bash
# Check analysis completion
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  image_type,
  COUNT(*) as count,
  AVG(quality_score)::numeric(3,2) as avg_quality,
  AVG(confidence_score)::numeric(3,2) as avg_confidence
FROM images
WHERE pdf_id IN (
  SELECT id FROM pdfs WHERE id IN (
    SELECT DISTINCT pdf_id FROM pdf_chapters WHERE book_id = '${BOOK_ID}'
  )
)
AND ai_description IS NOT NULL
GROUP BY image_type
ORDER BY count DESC;"
```

**Expected Results:**
```
   image_type     | count | avg_quality | avg_confidence
------------------+-------+-------------+----------------
 anatomical_diagram |    18 |        0.85 |           0.92
 mri               |    12 |        0.78 |           0.88
 surgical_photo    |     8 |        0.72 |           0.85
 ct                |     5 |        0.81 |           0.90
 angiogram         |     4 |        0.76 |           0.87
```

**Check Anatomical Structures:**
```bash
# See what anatomical structures were identified
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  anatomical_structures,
  COUNT(*) as image_count
FROM images
WHERE pdf_id IN (
  SELECT id FROM pdfs WHERE id IN (
    SELECT DISTINCT pdf_id FROM pdf_chapters WHERE book_id = '${BOOK_ID}'
  )
)
AND anatomical_structures IS NOT NULL
AND array_length(anatomical_structures, 1) > 0
GROUP BY anatomical_structures
ORDER BY image_count DESC
LIMIT 10;"
```

**Expected Results:**
```
         anatomical_structures          | image_count
----------------------------------------+-------------
 {frontal lobe, motor cortex}           |           5
 {lateral ventricle, corpus callosum}   |           4
 {cerebellum, brainstem}                |           3
 {pituitary gland, sella turcica}       |           3
```

**Check AI Descriptions:**
```bash
# Sample AI descriptions
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  image_type,
  SUBSTRING(ai_description, 1, 100) as description_sample,
  quality_score
FROM images
WHERE pdf_id IN (
  SELECT id FROM pdfs WHERE id IN (
    SELECT DISTINCT pdf_id FROM pdf_chapters WHERE book_id = '${BOOK_ID}'
  )
)
AND ai_description IS NOT NULL
ORDER BY quality_score DESC
LIMIT 5;"
```

---

### STEP 6: Verify Embeddings Generated (2 minutes)

After `generate_embeddings_task` completes (80% progress):

```bash
# Check embeddings
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  COUNT(*) as total_images,
  COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as embedded_images,
  (COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END)::float / COUNT(*)::float * 100)::numeric(5,2) as percent_embedded
FROM images
WHERE pdf_id IN (
  SELECT id FROM pdfs WHERE id IN (
    SELECT DISTINCT pdf_id FROM pdf_chapters WHERE book_id = '${BOOK_ID}'
  )
);"
```

**Expected Results:**
```
total_images | embedded_images | percent_embedded
-------------+-----------------+------------------
          47 |              47 |           100.00
```

---

### STEP 7: Test Image Integration in Chapter Generation (30 minutes)

Now test if images integrate into generated chapters:

1. **Generate a test chapter:**
   ```bash
   # Via API
   curl -X POST http://localhost:8002/api/v1/chapters \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "topic": "Frontal lobe anatomy and surgical approaches",
       "target_word_count": 3000,
       "include_images": true
     }'
   ```

2. **Monitor Stage 7 (Image Integration):**
   - WebSocket progress updates
   - Watch for "stage_7_image_integration" event

3. **Verify images in chapter:**
   ```bash
   CHAPTER_ID="<generated-chapter-id>"

   # Check how many images were integrated
   docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
   SELECT
     jsonb_array_length(sections) as total_sections,
     (
       SELECT COUNT(*)
       FROM jsonb_array_elements(sections) AS section
       WHERE jsonb_array_length(section->'images') > 0
     ) as sections_with_images,
     (
       SELECT SUM(jsonb_array_length(section->'images'))
       FROM jsonb_array_elements(sections) AS section
     ) as total_images_integrated
   FROM chapters
   WHERE id = '${CHAPTER_ID}';"
   ```

4. **View integrated images:**
   ```bash
   # See which images were used
   docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
   SELECT
     section->>'title' as section_title,
     jsonb_array_length(section->'images') as image_count,
     image->>'caption' as image_caption,
     (image->>'relevance_score')::numeric(3,2) as relevance
   FROM chapters,
     jsonb_array_elements(sections) AS section,
     jsonb_array_elements(section->'images') AS image
   WHERE id = '${CHAPTER_ID}'
   ORDER BY (image->>'relevance_score')::numeric DESC
   LIMIT 10;"
   ```

---

## Success Criteria

### ✅ Image Extraction Complete
- [ ] Images extracted from PDF (count > 0)
- [ ] Thumbnails generated
- [ ] Metadata populated (dimensions, format, size)
- [ ] Files stored in storage directory

### ✅ Claude Vision Analysis Complete
- [ ] All images have `ai_description`
- [ ] `anatomical_structures` populated (arrays with 1+ items)
- [ ] `image_type` classified correctly
- [ ] `quality_score` between 0.4-1.0
- [ ] `confidence_score` between 0.7-1.0
- [ ] `clinical_context` provided

### ✅ Embeddings Generated
- [ ] All images have 1536-dim embeddings
- [ ] Embeddings stored in pgvector format
- [ ] Vector search works on images

### ✅ Chapter Integration Working
- [ ] Generated chapter includes images
- [ ] Images match section content
- [ ] Captions are contextual and descriptive
- [ ] Relevance scores > 0.7
- [ ] Multiple images per chapter (if relevant)

---

## Troubleshooting

### Issue: No images extracted

**Check:**
```bash
# Verify PDF has images
docker exec neurocore-api python3 -c "
import fitz
doc = fitz.open('/app/storage/pdfs/<path-to-pdf>')
image_count = sum(len(page.get_images()) for page in doc)
print(f'Total images in PDF: {image_count}')
"
```

**Solution:** Use a different PDF with actual images

---

### Issue: Claude Vision analysis not running

**Check:**
```bash
# Check if image worker is processing
docker logs neurocore-celery-worker-images --tail 50

# Check for API key
docker exec neurocore-api env | grep ANTHROPIC_API_KEY
```

**Solution:** Verify ANTHROPIC_API_KEY is set in environment

---

### Issue: Low quality scores (<0.4)

**Possible causes:**
- Low resolution images
- Unclear/blurry images
- Non-medical images (graphs, text-heavy diagrams)

**Solution:** This is expected behavior - system filters low quality images

---

### Issue: Embeddings not generated

**Check:**
```bash
# Check embedding worker
docker logs neurocore-celery-worker-embeddings --tail 50

# Check OpenAI API key
docker exec neurocore-api env | grep OPENAI_API_KEY
```

**Solution:** Verify OPENAI_API_KEY is set

---

## Expected Timeline

For a typical 50-page neurosurgical PDF with ~40 images:

| Stage | Duration | Cumulative |
|-------|----------|------------|
| Upload | 30 sec | 0:30 |
| Text Extraction | 1-2 min | 2:30 |
| Image Extraction | 2-3 min | 5:30 |
| **Claude Vision Analysis** | **5-8 min** | **13:30** |
| Embedding Generation | 2-3 min | 16:30 |
| Citations (placeholder) | < 10 sec | 16:40 |
| **TOTAL** | **~17 minutes** | |

**Note:** Claude Vision analysis is the slowest step (10-15 sec per image)

---

## Quick Verification Commands

```bash
# 1. Check processing status
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  text_extracted,
  images_extracted,
  embeddings_generated
FROM pdfs
ORDER BY uploaded_at DESC
LIMIT 1;"

# 2. Count images
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT COUNT(*) as total_images FROM images WHERE created_at > NOW() - INTERVAL '1 hour';"

# 3. Check analysis progress
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN ai_description IS NOT NULL THEN 1 END) as analyzed,
  COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as embedded
FROM images
WHERE created_at > NOW() - INTERVAL '1 hour';"

# 4. View sample results
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  image_type,
  quality_score,
  confidence_score,
  array_length(anatomical_structures, 1) as structure_count
FROM images
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY quality_score DESC
LIMIT 5;"
```

---

## Next Steps After Verification

Once image pipeline is verified:

1. **Document results** in test report
2. **Generate sample chapter** with images
3. **Test semantic image search**
4. **Verify image display** in frontend
5. **Performance optimization** if needed

---

## Support

**If you encounter issues:**
1. Check Celery logs: `docker logs neurocore-celery-worker-images`
2. Check API logs: `docker logs neurocore-api | grep -i error`
3. Verify API keys are set
4. Check Flower monitoring at http://localhost:5555

**Documentation:**
- Image Analysis Service: `backend/services/image_analysis_service.py`
- Background Tasks: `backend/services/background_tasks.py`
- Image Integration: `backend/services/chapter_orchestrator.py:896-1012`

---

**Test Guide Version**: 1.0
**Created**: November 3, 2025
**Status**: Ready for Testing
**Estimated Time**: 30-45 minutes total
