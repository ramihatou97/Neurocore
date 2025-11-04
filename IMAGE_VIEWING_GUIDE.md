# Image Viewing & Usage Guide
## How to View and Use Textbook Images in Neurocore

---

## 📁 Where Are the Images Stored?

### **Location:**
```
Container: /data/images/2025/11/03/
Docker Volume: neurocore-image-storage
Host Path: /var/lib/docker/volumes/neurocore-image-storage/_data
```

### **Storage Statistics:**
- **Total Images**: 2,643 images
- **Total Size**: 194 MB
- **Format**: JPEG, PNG
- **Organization**: Date-based directories (YYYY/MM/DD)

### **Images by Textbook:**
| Textbook | Images |
|----------|--------|
| Anatomical-Basis-of-Cranial-Neurosurgery.pdf | 749 |
| Keyhole Approaches in Neurosurgery.pdf | 730 |
| Anatomy of Spine Surgery.pdf | 582 (×2 copies) |

---

## 🔍 Method 1: View Images via API

### **Get Image Details**

The API provides rich metadata about each image including AI analysis, quality scores, and which chapters use it.

**Endpoint:** `GET /api/images/{image_id}`

**Example:**
```bash
# Get details for a specific image
curl http://localhost:8002/api/images/518d14e1-8e7d-4208-a94a-a8c0766aeab3
```

**Response Includes:**
```json
{
  "id": "518d14e1-8e7d-4208-a94a-a8c0766aeab3",
  "pdf_id": "daec9f44-f448-4b4e-9b11-406c0b772347",
  "page_number": 41,
  "file_path": "/data/images/2025/11/03/e75d6539-a4a2-44fd-8222-ab0ebb3f0706.jpeg",
  "ai_analysis": {
    "description": "Surgical photograph showing cerebral aneurysm clipping...",
    "image_type": "Surgical photograph",
    "anatomical_structures": [
      "Cerebral vasculature",
      "Aneurysm sac",
      "Parent artery",
      "Surgical clip"
    ],
    "quality_score": 0.7,
    "confidence_score": 0.92
  },
  "used_in_chapters": [],  // Which chapters reference this image
  "chapter_count": 0
}
```

### **Get Image Recommendations**

Find similar images based on a reference image:

```bash
# Get similar images
curl "http://localhost:8002/api/images/518d14e1-8e7d-4208-a94a-a8c0766aeab3/recommendations?max_results=5&min_similarity=0.7"
```

### **Search Images by Text**

Find images relevant to your query:

```bash
# Search for brain tumor images
curl "http://localhost:8002/api/images/semantic-search?query=glioblastoma+tumor&max_results=10"
```

---

## 💻 Method 2: Extract Images to Your Local Machine

### **Option A: Copy Single Image**

```bash
# Find an image ID from the API first
IMAGE_FILE="e75d6539-a4a2-44fd-8222-ab0ebb3f0706.jpeg"

# Copy to your Desktop
docker cp neurocore-api:/data/images/2025/11/03/$IMAGE_FILE ~/Desktop/

# Open it
open ~/Desktop/$IMAGE_FILE
```

### **Option B: Copy All Images**

```bash
# Copy entire image directory
docker cp neurocore-api:/data/images ~/Desktop/textbook_images/

# Browse them
open ~/Desktop/textbook_images/2025/11/03/
```

**Result:** All 2,643 images (194 MB) will be on your Desktop

### **Option C: Copy Images from Specific Textbook**

```bash
# Get PDF ID from API
curl http://localhost:8002/api/v1/pdfs

# Query images from that PDF
curl "http://localhost:8002/api/v1/pdfs/{PDF_ID}/images"

# Then copy specific images based on file paths returned
```

---

## 🎨 Method 3: View Images in the Web App

### **Current Integration: Chapter Generation (Stage 7)**

Images are automatically integrated during chapter generation at **Stage 7: Semantic Image Integration**.

**How It Works:**
1. During chapter generation, relevant images are identified from the textbook database
2. Images are semantically matched to chapter sections using embeddings
3. Images are integrated into the chapter content with references

**Code Location:** `backend/services/chapter_orchestrator.py:1219`

### **To Use During Chapter Generation:**

```bash
# Create a chapter (images will be automatically integrated)
curl -X POST http://localhost:8002/api/v1/chapters \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Cerebral Aneurysm Management",
    "chapter_type": "surgical_disease"
  }'

# The chapter generation process will:
# 1. Research the topic
# 2. Find relevant images from the 2,643 available
# 3. Integrate them into sections
# 4. Return chapter with image references
```

---

## 🖼️ Method 4: Add Image Serving Endpoint (Recommended)

Currently, images can be accessed via metadata but not directly viewed in the browser. Here's how to add image serving:

### **Implementation Needed:**

Add to `backend/main.py`:

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Mount static files for images
app.mount("/images", StaticFiles(directory="/data/images"), name="images")

# Or add a dedicated endpoint
@app.get("/api/v1/images/serve/{image_id}")
async def serve_image(image_id: str, db: Session = Depends(get_db)):
    """Serve an image file by ID"""
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if not os.path.exists(image.file_path):
        raise HTTPException(status_code=404, detail="Image file not found")

    return FileResponse(
        image.file_path,
        media_type=f"image/{image.format.lower()}",
        headers={"Content-Disposition": f"inline; filename={image_id}.{image.format.lower()}"}
    )
```

### **Then Access Images:**

```
http://localhost:8002/api/v1/images/serve/518d14e1-8e7d-4208-a94a-a8c0766aeab3
```

Or via static mount:

```
http://localhost:8002/images/2025/11/03/e75d6539-a4a2-44fd-8222-ab0ebb3f0706.jpeg
```

---

## 🔬 Method 5: Query Images from Database

### **Get All Images from a PDF:**

```python
from backend.database.connection import db
from backend.database.models import Image, PDF

with db.session_scope() as session:
    # Get images from a specific textbook
    pdf = session.query(PDF).filter(
        PDF.filename.like("%Keyhole%")
    ).first()

    images = session.query(Image).filter(
        Image.pdf_id == pdf.id
    ).limit(10).all()

    for img in images:
        print(f"Page {img.page_number}: {img.file_path}")
        print(f"Type: {img.image_type}")
        print(f"Quality: {img.quality_score}")
        print()
```

### **Find Images by Content:**

```python
# Search for specific anatomical structures
images = session.query(Image).filter(
    Image.anatomical_structures.contains(["Cerebellum"])
).all()

# Find high-quality surgical images
images = session.query(Image).filter(
    Image.image_type == "Surgical photograph",
    Image.quality_score >= 0.7
).all()
```

---

## 📊 Image Metadata Available

Each image has rich metadata:

### **Basic Info:**
- `id` - Unique identifier
- `pdf_id` - Source textbook
- `page_number` - Page in textbook
- `file_path` - Physical location
- `width`, `height` - Dimensions
- `format` - JPEG/PNG
- `file_size_bytes` - File size

### **AI Analysis:**
- `ai_description` - Detailed description
- `image_type` - Classification (anatomical, surgical, diagram, etc.)
- `anatomical_structures` - List of structures shown
- `clinical_context` - Medical context
- `quality_score` - Image quality (0-1)
- `confidence_score` - AI confidence (0-1)

### **Text Content:**
- `ocr_text` - Extracted text
- `contains_text` - Boolean flag
- `caption` - Image caption
- `figure_number` - Figure number if available

### **Relationships:**
- `embedding` - Vector embedding for similarity search
- `is_duplicate` - Duplicate detection flag
- `duplicate_of_id` - Reference to original if duplicate

---

## 🎯 Practical Use Cases

### **1. Browse Images from a Specific Textbook**

```bash
# Step 1: Get PDF ID
curl http://localhost:8002/api/v1/pdfs | python3 -m json.tool

# Step 2: Get images from that PDF
PDF_ID="daec9f44-f448-4b4e-9b11-406c0b772347"
curl "http://localhost:8002/api/v1/pdfs/$PDF_ID/images?page=1&limit=50"

# Step 3: Get details for interesting images
curl http://localhost:8002/api/images/518d14e1-8e7d-4208-a94a-a8c0766aeab3

# Step 4: Copy image to view
docker cp neurocore-api:/data/images/2025/11/03/e75d6539-a4a2-44fd-8222-ab0ebb3f0706.jpeg ~/Desktop/
open ~/Desktop/e75d6539-a4a2-44fd-8222-ab0ebb3f0706.jpeg
```

### **2. Find Images for a Chapter Topic**

```bash
# Search for relevant images
curl "http://localhost:8002/api/images/semantic-search?query=aneurysm+clipping&max_results=10"

# Get recommendations based on similar images
curl "http://localhost:8002/api/images/518d14e1-8e7d-4208-a94a-a8c0766aeab3/recommendations?max_results=5"
```

### **3. Generate Chapter with Images**

```bash
# Create chapter (will automatically find and integrate relevant images)
curl -X POST http://localhost:8002/api/v1/chapters \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "topic": "Endoscopic Third Ventriculostomy",
    "chapter_type": "surgical_procedure"
  }'

# Monitor progress
curl http://localhost:8002/api/v1/chapters/{CHAPTER_ID}

# The generated chapter will include:
# - Image references in content
# - Links to relevant figures
# - Citations from textbooks
```

### **4. Export Chapter with Images**

```bash
# Export chapter as PDF with embedded images
curl "http://localhost:8002/api/v1/chapters/{CHAPTER_ID}/export/pdf" \
  --output chapter.pdf

# Export as DOCX with images
curl "http://localhost:8002/api/v1/chapters/{CHAPTER_ID}/export/docx" \
  --output chapter.docx
```

---

## 🛠️ Frontend Integration

### **For React/Frontend Developers:**

**1. Display Image Gallery:**

```javascript
// Fetch images
const images = await fetch('/api/v1/pdfs/${pdfId}/images').then(r => r.json());

// Display in gallery
{images.map(img => (
  <div key={img.id}>
    <img
      src={`/api/v1/images/serve/${img.id}`}  // After implementing serving endpoint
      alt={img.ai_analysis.description}
      title={`Page ${img.page_number}`}
    />
    <p>Quality: {img.ai_analysis.quality_percentage}%</p>
    <p>Type: {img.ai_analysis.image_type}</p>
  </div>
))}
```

**2. Image Search Component:**

```javascript
const searchImages = async (query) => {
  const results = await fetch(
    `/api/images/semantic-search?query=${encodeURIComponent(query)}&max_results=20`
  ).then(r => r.json());

  return results;
};
```

**3. Chapter with Images:**

```javascript
// When displaying a chapter, show referenced images
const ChapterView = ({ chapter }) => {
  const [images, setImages] = useState([]);

  useEffect(() => {
    // Get images used in this chapter
    const chapterImages = chapter.referenced_images || [];

    // Fetch full image details
    Promise.all(
      chapterImages.map(imgId =>
        fetch(`/api/images/${imgId}`).then(r => r.json())
      )
    ).then(setImages);
  }, [chapter]);

  return (
    <div>
      <div className="chapter-content">{chapter.content}</div>
      <div className="chapter-images">
        {images.map(img => (
          <figure key={img.id}>
            <img src={`/api/v1/images/serve/${img.id}`} />
            <figcaption>{img.caption || img.ai_analysis.description}</figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
};
```

---

## 📝 Quick Reference Commands

```bash
# List all images
docker exec neurocore-api find /data/images -name "*.png" -o -name "*.jpg" | wc -l

# Copy all images to Desktop
docker cp neurocore-api:/data/images ~/Desktop/textbook_images/

# Get image metadata
curl http://localhost:8002/api/images/{IMAGE_ID}

# Search images
curl "http://localhost:8002/api/images/semantic-search?query=YOUR_QUERY"

# Get similar images
curl "http://localhost:8002/api/images/{IMAGE_ID}/recommendations"

# Check storage size
docker exec neurocore-api du -sh /data/images
```

---

## 🚀 Next Steps for Full Image Integration

### **Recommended Enhancements:**

1. **Add Image Serving Endpoint**
   - Implement `/api/v1/images/serve/{image_id}`
   - Add thumbnail serving for performance
   - Cache responses

2. **Frontend Image Gallery**
   - Create image browser component
   - Add filtering by type, quality, textbook
   - Implement lightbox for full-size viewing

3. **Chapter Image Integration UI**
   - Show image suggestions while writing
   - Drag-and-drop image placement
   - Preview images in chapter editor

4. **Image Search Enhancement**
   - Full-text search on captions and OCR
   - Filter by anatomical structures
   - Sort by quality/relevance

5. **Image Analytics**
   - Track image usage in chapters
   - Popular images dashboard
   - Quality metrics

---

## 📚 Current Status

✅ **Working Now:**
- 2,643 images extracted and indexed
- Rich AI metadata (anatomical structures, quality scores)
- Image recommendations API
- Semantic search capability
- Chapter integration (Stage 7)
- Export with images (PDF, DOCX)

⏳ **Needs Implementation:**
- Direct image serving endpoint (HTTP access)
- Frontend image gallery component
- Interactive image browser
- Image upload/management UI

---

## 💡 Summary

**Your textbook images are:**
- ✅ Extracted (2,643 images, 194 MB)
- ✅ Indexed with AI analysis
- ✅ Searchable by content
- ✅ Integrated into chapter generation
- ✅ Accessible via API

**To view them:**
1. **Copy to local**: `docker cp neurocore-api:/data/images ~/Desktop/textbook_images/`
2. **Use API**: `curl http://localhost:8002/api/images/{IMAGE_ID}`
3. **Generate chapter**: Images auto-integrate at Stage 7

**For production use, implement the image serving endpoint above!**

---

Generated: 2025-11-03
Status: Images ready for use in chapter generation
Next: Add image serving endpoint for browser viewing
