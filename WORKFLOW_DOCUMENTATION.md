# Chapter Generation Workflow - Complete Technical Documentation

> **Last Updated**: 2025-10-29
> **Status**: Phase 1 Implementation - Documentation + Section Editing

## Table of Contents

1. [Overview](#overview)
2. [Architecture Components](#architecture-components)
3. [14-Stage Chapter Generation Pipeline](#14-stage-chapter-generation-pipeline)
4. [Real-Time WebSocket Streaming](#real-time-websocket-streaming)
5. [Background PDF Processing](#background-pdf-processing)
6. [Data Flow & State Management](#data-flow--state-management)
7. [Cost Analysis](#cost-analysis)
8. [Error Handling & Recovery](#error-handling--recovery)
9. [API Endpoints Reference](#api-endpoints-reference)
10. [Database Schema](#database-schema)

---

## Overview

The Neurosurgery Knowledge Base implements a sophisticated two-process architecture:

- **Process A**: Continuous 24/7 background PDF indexation (Celery workers)
- **Process B**: On-demand chapter generation with real-time streaming (14-stage workflow)

### Key Characteristics

- **Async/Await**: All orchestration uses Python asyncio for non-blocking I/O
- **WebSocket Streaming**: Real-time section delivery as content is generated
- **Smart Caching**: Hot cache (1 hour) + Cold cache (24 hours) = 40-65% cost reduction
- **Multi-AI Orchestration**: Claude Sonnet 4.5, GPT-4/5, Gemini Pro 2.5
- **Vector Search**: pgvector with 1536-dimensional embeddings (OpenAI ada-002)
- **Version Control**: Git-like snapshots with diff capability

---

## Architecture Components

### Backend Services

```
backend/
├── services/
│   ├── chapter_orchestrator.py       # 14-stage workflow coordinator
│   ├── research_service.py           # Vector search + PubMed integration
│   ├── ai_provider_service.py        # Multi-provider AI orchestration
│   ├── pdf_processor.py              # PDF extraction and analysis
│   ├── embedding_service.py          # OpenAI embedding generation
│   └── cache_service.py              # Hybrid hot/cold caching
├── utils/
│   ├── websocket_emitter.py          # Real-time progress updates
│   └── events.py                     # Event type definitions
└── database/models/
    ├── chapter.py                    # Chapter model (47 columns)
    ├── pdf.py                        # PDF document metadata
    └── pdf_chunk.py                  # Text chunks with embeddings
```

### Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Framework** | FastAPI | Async HTTP + WebSocket support |
| **Database** | PostgreSQL 15 + pgvector | Relational data + vector similarity |
| **Cache** | Redis 7 | Hot/cold caching, rate limiting |
| **Task Queue** | Celery 5 | Background PDF processing |
| **AI Providers** | Claude, GPT-4, Gemini | Multi-model orchestration |
| **Embeddings** | OpenAI ada-002 | 1536-dim vector embeddings |

---

## 14-Stage Chapter Generation Pipeline

### Entry Point

```python
# backend/services/chapter_orchestrator.py
async def generate_chapter(topic: str, user: User) -> Chapter
```

### Complete Stage Breakdown

#### Stage 1: Topic Input & Validation
**File**: `chapter_orchestrator.py:164-228`

**Purpose**: Parse and validate user query, extract key medical concepts

**Process**:
1. Validate topic length (≥3 characters)
2. AI analysis to extract:
   - Primary medical concepts (anatomy, procedures, diseases)
   - Suggested chapter type (surgical_disease, pure_anatomy, surgical_technique)
   - Related keywords for research
   - Complexity level (beginner, intermediate, advanced)
3. Store in `chapter.stage_1_input` JSONB column

**AI Task**: `AITask.METADATA_EXTRACTION`
**Model**: Claude Sonnet 4.5 or GPT-4 (fallback)
**Timing**: 2-4 seconds
**Cost**: $0.002-0.005

**Database Updates**:
```python
chapter.stage_1_input = {
    "original_topic": str,
    "analysis": {
        "primary_concepts": List[str],
        "chapter_type": str,
        "keywords": List[str],
        "complexity": str
    },
    "validated_at": ISO timestamp,
    "ai_cost_usd": float
}
chapter.generation_status = "stage_1_input"
```

**WebSocket Event**:
```json
{
  "event": "chapter_progress",
  "chapter_id": "uuid",
  "stage": "stage_1_input",
  "stage_number": 1,
  "message": "Validating input and analyzing topic",
  "timestamp": "ISO 8601"
}
```

---

#### Stage 2: Context Building
**File**: `chapter_orchestrator.py:230-310`

**Purpose**: Build comprehensive research context and search queries

**Process**:
1. Extract entities from Stage 1 analysis
2. Build synonym lists for medical terms
3. Generate search queries optimized for:
   - Vector search (semantic similarity)
   - PubMed API (MeSH terms, keywords)
   - Google Scholar (phrase matching)
4. Identify related anatomical structures

**AI Task**: `AITask.RESEARCH_PLANNING`
**Model**: GPT-4 or Claude Sonnet 4.5
**Timing**: 3-5 seconds
**Cost**: $0.003-0.007

**Database Updates**:
```python
chapter.stage_2_context = {
    "entities": {
        "diseases": List[str],
        "anatomical_structures": List[str],
        "procedures": List[str],
        "medications": List[str]
    },
    "search_queries": {
        "vector_queries": List[str],      # 5-10 semantic queries
        "pubmed_queries": List[str],      # 3-5 MeSH-optimized queries
        "keyword_queries": List[str]      # 3-5 keyword combinations
    },
    "synonyms": Dict[str, List[str]],
    "ai_cost_usd": float
}
```

**Example Output**:
```json
{
  "entities": {
    "diseases": ["glioblastoma", "high-grade glioma"],
    "anatomical_structures": ["cerebral hemisphere", "frontal lobe"],
    "procedures": ["craniotomy", "gross total resection"]
  },
  "search_queries": {
    "vector_queries": [
      "glioblastoma surgical management and outcomes",
      "extent of resection impact on glioblastoma survival"
    ],
    "pubmed_queries": [
      "glioblastoma[MeSH] AND neurosurgical procedures[MeSH]"
    ]
  }
}
```

---

#### Stage 3: Internal Research
**File**: `chapter_orchestrator.py:312-450`

**Purpose**: Search indexed PDF library using vector similarity

**Process**:
1. For each vector query from Stage 2:
   - Generate query embedding (OpenAI ada-002)
   - Execute pgvector similarity search
   - Retrieve top 20 most relevant chunks
2. Expand to full PDF metadata
3. Extract associated images with high relevance scores
4. Build citation network (papers citing/cited by results)
5. Apply smart caching (check hot cache → cold cache → API)

**Key Methods**:
```python
# backend/services/research_service.py
async def internal_vector_search(
    query: str,
    limit: int = 20,
    similarity_threshold: float = 0.75
) -> List[Dict]
```

**SQL Query Pattern**:
```sql
SELECT
    pc.id,
    pc.pdf_id,
    pc.content,
    pc.embedding <-> $1 AS distance,
    p.title,
    p.authors,
    p.publication_year
FROM pdf_chunks pc
JOIN pdfs p ON pc.pdf_id = p.id
WHERE pc.embedding <-> $1 < $2  -- similarity_threshold
ORDER BY pc.embedding <-> $1
LIMIT $3;
```

**Timing**: 8-15 seconds (5-10 queries × 1-2 seconds each)
**Cost**: $0.005-0.015 (embedding generation only, search is free)

**Cache Hit Rates**:
- Hot cache (1 hour TTL): 45-60% hit rate
- Cold cache (24 hours TTL): 20-30% hit rate
- Total cache savings: 40-65% cost reduction

**Database Updates**:
```python
chapter.stage_3_internal_research = {
    "sources": [
        {
            "pdf_id": UUID,
            "title": str,
            "authors": List[str],
            "year": int,
            "doi": Optional[str],
            "relevance_score": float,  # 0.0-1.0
            "chunks": [
                {
                    "chunk_id": UUID,
                    "content": str,
                    "page_number": int,
                    "similarity": float
                }
            ],
            "images": [
                {
                    "image_id": UUID,
                    "caption": str,
                    "relevance_score": float
                }
            ]
        }
    ],
    "total_sources": int,
    "total_chunks": int,
    "avg_relevance": float,
    "cache_hits": int,
    "cache_misses": int,
    "search_cost_usd": float
}
```

---

#### Stage 4: External Research
**File**: `chapter_orchestrator.py:452-580`

**Purpose**: Query external databases (PubMed) for recent publications

**Process**:
1. For each PubMed query from Stage 2 (top 3 queries):
   - Execute ESearch API to get PMIDs
   - Batch fetch with EFetch API (XML format)
   - Parse XML to extract metadata
2. Deduplicate against internal sources (by DOI/title)
3. **Current Issue**: No AI relevance filtering (accepts all results)
4. Slice to top 15 external sources

**Key Methods**:
```python
# backend/services/research_service.py
async def external_research_pubmed(
    query: str,
    max_results: int = 5,
    recent_years: int = 5
) -> List[Dict]
```

**PubMed API Calls**:
```python
# ESearch: Get PMIDs
url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
params = {
    "db": "pubmed",
    "term": query,
    "retmax": max_results,
    "retmode": "json",
    "sort": "relevance",
    "reldate": recent_years * 365  # Days
}

# EFetch: Get full records
url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
params = {
    "db": "pubmed",
    "id": ",".join(pmids),
    "retmode": "xml"
}
```

**Current Performance**:
- **Sequential Execution**: 3 queries × 3 seconds = 9 seconds total
- **No Caching**: Every query hits PubMed API
- **No AI Filtering**: 60-70% relevance rate (many false positives)

**Proposed Improvements** (Phase 2):
- Parallel execution: `asyncio.gather()` → 3 seconds total
- Redis caching: 24-hour TTL → 300x faster for repeated queries
- AI relevance scoring: GPT-4 analysis → 85-95% relevance rate

**Timing**: 9-12 seconds (current), 3-5 seconds (optimized)
**Cost**: $0 (PubMed is free), $0.07 with AI filtering

**Database Updates**:
```python
chapter.stage_4_external_research = {
    "pubmed_sources": [
        {
            "pmid": str,
            "title": str,
            "authors": List[str],
            "journal": str,
            "year": int,
            "doi": Optional[str],
            "abstract": str,
            "mesh_terms": List[str],
            "citation_count": Optional[int]
        }
    ],
    "total_external": int,
    "deduplication_removed": int,
    "queries_executed": List[str],
    "search_duration_seconds": float
}
```

---

#### Stage 5: Content Synthesis Planning
**File**: `chapter_orchestrator.py:582-750`

**Purpose**: Plan chapter structure and create detailed outline

**Process**:
1. Combine Stage 3 (internal) + Stage 4 (external) sources
2. AI analyzes all sources and creates:
   - Chapter outline with 8-15 major sections
   - Subsection breakdown (48-150 total sections based on chapter type)
   - Image placement strategy
   - Citation distribution plan
3. Determine section ordering (pathophysiology → diagnosis → treatment → outcomes)
4. Allocate tokens per section based on importance

**AI Task**: `AITask.CHAPTER_PLANNING`
**Model**: Claude Sonnet 4.5 (preferred for long context)
**Timing**: 5-8 seconds
**Cost**: $0.015-0.030

**Section Count by Chapter Type**:
```python
SECTION_COUNTS = {
    "surgical_disease": {
        "min_sections": 80,
        "max_sections": 120,
        "typical": 100
    },
    "pure_anatomy": {
        "min_sections": 48,
        "max_sections": 80,
        "typical": 60
    },
    "surgical_technique": {
        "min_sections": 60,
        "max_sections": 100,
        "typical": 80
    }
}
```

**Database Updates**:
```python
chapter.stage_5_synthesis_plan = {
    "outline": [
        {
            "section_number": int,
            "title": str,
            "subsections": [
                {
                    "subsection_number": int,
                    "title": str,
                    "estimated_words": int,
                    "key_sources": List[UUID],  # PDF IDs
                    "image_slots": int
                }
            ]
        }
    ],
    "total_sections": int,
    "estimated_total_words": int,
    "image_plan": {
        "total_images": int,
        "placement": Dict[int, List[UUID]]  # section -> image_ids
    },
    "ai_cost_usd": float
}
```

**Example Outline**:
```json
{
  "outline": [
    {
      "section_number": 1,
      "title": "Introduction and Epidemiology",
      "subsections": [
        {"subsection_number": 1, "title": "Definition and Classification", "estimated_words": 300},
        {"subsection_number": 2, "title": "Incidence and Demographics", "estimated_words": 250}
      ]
    },
    {
      "section_number": 2,
      "title": "Pathophysiology and Molecular Biology",
      "subsections": [
        {"subsection_number": 3, "title": "Genetic Alterations", "estimated_words": 400},
        {"subsection_number": 4, "title": "Cellular Mechanisms", "estimated_words": 350}
      ]
    }
  ]
}
```

---

#### Stage 6: Section Generation
**File**: `chapter_orchestrator.py:752-950`

**Purpose**: Generate actual chapter content section by section

**Process**:
1. For each section in the outline:
   - Select relevant sources (from stages 3-4)
   - Build context with source excerpts
   - Generate section content with AI
   - **Stream immediately via WebSocket** (incremental delivery)
   - Store section in database
2. Continue until all sections complete
3. Aggregate into full chapter HTML

**AI Task**: `AITask.CONTENT_GENERATION`
**Model**: Claude Sonnet 4.5 (primary), GPT-4 (fallback)
**Timing**: 120-240 seconds (depends on section count)
**Cost**: $0.30-0.60 (largest cost component)

**Streaming Pattern**:
```python
# Emit each section immediately when generated
for section_num, section_data in enumerate(outline):
    content = await self.ai_service.generate_text(
        prompt=build_section_prompt(section_data, sources),
        task=AITask.CONTENT_GENERATION,
        max_tokens=2000
    )

    # Store in database
    chapter.sections[section_num] = {
        "title": section_data["title"],
        "content": content["text"],
        "sources": section_data["key_sources"],
        "generated_at": datetime.utcnow().isoformat()
    }
    self.db.commit()

    # Stream to frontend immediately
    await emitter.emit_section_generated(
        chapter_id=str(chapter.id),
        section_number=section_num,
        section_title=section_data["title"],
        section_content=content["text"],
        total_sections=len(outline)
    )
```

**WebSocket Event**:
```json
{
  "event": "section_generated",
  "chapter_id": "uuid",
  "section_number": 5,
  "section_title": "Surgical Approaches",
  "section_content": "<h2>Surgical Approaches</h2><p>Content...</p>",
  "total_sections": 100,
  "progress_percent": 5,
  "timestamp": "ISO 8601"
}
```

**Database Updates**:
```python
chapter.stage_6_section_content = {
    "sections": [
        {
            "number": int,
            "title": str,
            "content": str,  # HTML formatted
            "word_count": int,
            "sources_used": List[UUID],
            "images_embedded": List[UUID],
            "generation_cost_usd": float,
            "generated_at": ISO timestamp
        }
    ],
    "total_words": int,
    "total_cost_usd": float,
    "generation_duration_seconds": float
}
```

---

#### Stage 7: Image Integration
**File**: `chapter_orchestrator.py:952-1050`

**Purpose**: Embed relevant images within chapter sections

**Process**:
1. For each section, retrieve images from image plan (Stage 5)
2. Select best placement within section HTML
3. Add captions with source attribution
4. Optimize image references (thumbnail vs full)

**Timing**: 5-10 seconds
**Cost**: $0 (no AI, database queries only)

**Database Updates**:
```python
# Images stored in stage_6_section_content, updated in place
chapter.stage_7_images = {
    "total_images": int,
    "images_by_section": Dict[int, List[UUID]],
    "placement_complete": bool
}
```

---

#### Stage 8: Citation Network
**File**: `chapter_orchestrator.py:1052-1150`

**Purpose**: Build bibliography and in-text citations

**Process**:
1. Aggregate all sources used across sections
2. Format citations (AMA style for neurosurgery)
3. Build citation links (papers citing/cited by each source)
4. Generate bibliography HTML

**Timing**: 3-5 seconds
**Cost**: $0

**Database Updates**:
```python
chapter.stage_8_citations = {
    "bibliography": [
        {
            "citation_id": int,
            "source_id": UUID,
            "formatted_citation": str,  # AMA format
            "cited_in_sections": List[int],
            "citation_count": int
        }
    ],
    "total_citations": int,
    "citation_network": {
        "nodes": List[UUID],  # PDF IDs
        "edges": List[Tuple[UUID, UUID]]  # (citing, cited)
    }
}
```

---

#### Stage 9: Quality Assurance
**File**: `chapter_orchestrator.py:1152-1280`

**Purpose**: Calculate quality metrics

**Process**:
1. **Depth Score** (0-100): Average section word count relative to target
2. **Coverage Score** (0-100): Percentage of planned topics addressed
3. **Evidence Score** (0-100): Citation density and source quality
4. **Currency Score** (0-100): Recency of citations (weight recent papers)

**AI Task**: `AITask.QUALITY_ASSESSMENT`
**Model**: GPT-4 or Claude
**Timing**: 5-8 seconds
**Cost**: $0.010-0.020

**Calculation Formulas**:
```python
# Depth Score
depth_score = min(100, (avg_section_words / target_words) * 100)

# Coverage Score
coverage_score = (sections_with_content / total_planned_sections) * 100

# Evidence Score
citations_per_1000_words = (total_citations / total_words) * 1000
evidence_score = min(100, citations_per_1000_words * 10)

# Currency Score
avg_citation_age = mean([2025 - year for year in citation_years])
currency_score = max(0, 100 - (avg_citation_age * 5))
```

**Database Updates**:
```python
chapter.depth_score = float  # 0-100
chapter.coverage_score = float  # 0-100
chapter.evidence_score = float  # 0-100
chapter.currency_score = float  # 0-100

chapter.stage_9_qa = {
    "depth_analysis": {
        "avg_section_words": int,
        "target_words": int,
        "sections_below_target": int
    },
    "coverage_analysis": {
        "planned_topics": int,
        "addressed_topics": int,
        "missing_topics": List[str]
    },
    "evidence_analysis": {
        "total_citations": int,
        "citations_per_1000_words": float,
        "high_quality_sources": int
    },
    "currency_analysis": {
        "avg_citation_age": float,
        "recent_papers_count": int,  # Last 3 years
        "oldest_citation_year": int
    }
}
```

---

#### Stage 10: Fact-Checking
**File**: `chapter_orchestrator.py:1282-1400`

**Purpose**: Cross-reference claims with sources

**Process**:
1. Extract factual claims from chapter content
2. For each claim, verify against source documents
3. Flag unsupported claims
4. Add confidence scores

**AI Task**: `AITask.FACT_CHECKING`
**Model**: Claude Sonnet 4.5 (best for accuracy)
**Timing**: 15-25 seconds
**Cost**: $0.025-0.040

**Database Updates**:
```python
chapter.stage_10_fact_check = {
    "claims_checked": int,
    "verified_claims": int,
    "unsupported_claims": [
        {
            "claim": str,
            "section_number": int,
            "confidence": float  # 0.0-1.0
        }
    ],
    "verification_rate": float,  # Percentage
    "ai_cost_usd": float
}
```

---

#### Stage 11: Formatting & Structure
**File**: `chapter_orchestrator.py:1402-1480`

**Purpose**: Apply consistent HTML formatting

**Process**:
1. Apply CSS classes for typography
2. Ensure heading hierarchy (h2 → h3 → h4)
3. Format tables consistently
4. Add anchor links for navigation

**Timing**: 2-3 seconds
**Cost**: $0

---

#### Stage 12: Review & Refinement
**File**: `chapter_orchestrator.py:1482-1580`

**Purpose**: AI-powered clarity review

**Process**:
1. Check for jargon without definitions
2. Identify unclear sentences
3. Suggest improvements (stored, not auto-applied)

**AI Task**: `AITask.REVIEW`
**Model**: GPT-4
**Timing**: 8-12 seconds
**Cost**: $0.015-0.025

**Database Updates**:
```python
chapter.stage_12_review = {
    "suggestions": [
        {
            "section_number": int,
            "type": str,  # "clarity", "jargon", "structure"
            "issue": str,
            "suggestion": str,
            "priority": str  # "low", "medium", "high"
        }
    ],
    "total_suggestions": int,
    "ai_cost_usd": float
}
```

---

#### Stage 13: Finalization
**File**: `chapter_orchestrator.py:1582-1650`

**Purpose**: Generate metadata and summary

**Process**:
1. Create executive summary (300-500 words)
2. Extract key points (5-10 bullet points)
3. Generate suggested tags
4. Calculate final statistics

**AI Task**: `AITask.SUMMARIZATION`
**Model**: Claude or GPT-4
**Timing**: 5-8 seconds
**Cost**: $0.008-0.015

**Database Updates**:
```python
chapter.summary = str  # Executive summary
chapter.key_points = List[str]
chapter.tags = List[str]

chapter.stage_13_finalization = {
    "summary": str,
    "key_points": List[str],
    "suggested_tags": List[str],
    "statistics": {
        "total_words": int,
        "total_sections": int,
        "total_images": int,
        "total_citations": int,
        "generation_time_seconds": float,
        "total_cost_usd": float
    }
}
```

---

#### Stage 14: Delivery
**File**: `chapter_orchestrator.py:1652-1700`

**Purpose**: Final storage and notification

**Process**:
1. Set `generation_status = "completed"`
2. Create initial version snapshot (version 1)
3. Emit completion WebSocket event with quality scores

**Timing**: 1-2 seconds
**Cost**: $0

**Database Updates**:
```python
chapter.generation_status = "completed"
chapter.completed_at = datetime.utcnow()
chapter.version = 1

# Create version snapshot
ChapterVersion(
    chapter_id=chapter.id,
    version=1,
    content=chapter.full_content,
    metadata={"initial_generation": True},
    created_by=user.id
)
```

**WebSocket Event**:
```json
{
  "event": "chapter_completed",
  "chapter_id": "uuid",
  "message": "Chapter generation completed successfully",
  "quality_scores": {
    "depth_score": 87.5,
    "coverage_score": 92.0,
    "evidence_score": 78.3,
    "currency_score": 85.0
  },
  "statistics": {
    "total_words": 12500,
    "total_sections": 95,
    "total_images": 22,
    "total_citations": 87,
    "generation_time_seconds": 185.3,
    "total_cost_usd": 0.52
  },
  "timestamp": "ISO 8601"
}
```

---

## Real-Time WebSocket Streaming

### Connection Setup

```javascript
// frontend/src/services/websocket.js
const socket = io('http://localhost:8002/api/v1/ws', {
  auth: {
    token: userJwtToken
  },
  transports: ['websocket'],
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000
});
```

### Event Types

| Event | Description | Frequency |
|-------|-------------|-----------|
| `chapter_progress` | Stage update (stages 1-14) | 14 times per chapter |
| `section_generated` | New section complete | 48-150 times per chapter |
| `chapter_completed` | Generation finished | 1 time per chapter |
| `chapter_failed` | Generation error | 0-1 times per chapter |

### Frontend Integration

```jsx
// frontend/src/components/ChapterViewer.jsx
useEffect(() => {
  socket.on('section_generated', (data) => {
    // Append section to DOM immediately
    setSections(prev => [...prev, {
      number: data.section_number,
      title: data.section_title,
      content: data.section_content
    }]);

    // Update progress bar
    const progress = (data.section_number / data.total_sections) * 100;
    setProgress(progress);
  });

  socket.on('chapter_completed', (data) => {
    setGenerationComplete(true);
    setQualityScores(data.quality_scores);
    setStatistics(data.statistics);
  });

  return () => {
    socket.off('section_generated');
    socket.off('chapter_completed');
  };
}, []);
```

### Backend Emission

```python
# backend/utils/websocket_emitter.py
from socketio import AsyncServer

class WebSocketEmitter:
    def __init__(self, sio: AsyncServer):
        self.sio = sio

    async def emit_section_generated(
        self,
        chapter_id: str,
        section_number: int,
        section_title: str,
        section_content: str,
        total_sections: int
    ):
        await self.sio.emit(
            'section_generated',
            {
                'chapter_id': chapter_id,
                'section_number': section_number,
                'section_title': section_title,
                'section_content': section_content,
                'total_sections': total_sections,
                'progress_percent': (section_number / total_sections) * 100,
                'timestamp': datetime.utcnow().isoformat()
            },
            room=f'chapter_{chapter_id}'
        )
```

---

## Background PDF Processing

### 5-Stage Celery Pipeline

```python
# backend/workers/pdf_processor_worker.py
@celery_app.task
def process_pdf_pipeline(pdf_id: UUID):
    """
    Stage 0 (Background): 5-phase PDF indexation
    """
    chain(
        extract_text_and_metadata.s(pdf_id),
        extract_images.s(),
        analyze_images_with_vision.s(),
        generate_embeddings.s(),
        build_citation_network.s()
    ).apply_async()
```

#### Phase 1: Text Extraction
**Worker**: `celery-worker` (default queue)

```python
@celery_app.task(queue='default')
def extract_text_and_metadata(pdf_id: UUID):
    """Extract text, tables, and metadata using PyMuPDF"""
    pdf = db.query(PDF).get(pdf_id)

    with fitz.open(pdf.file_path) as doc:
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            tables = page.find_tables()

            # Store as chunks (500 words each)
            chunks = split_into_chunks(text, chunk_size=500)
            for chunk_text in chunks:
                PDFChunk(
                    pdf_id=pdf_id,
                    page_number=page_num,
                    content=chunk_text,
                    chunk_type="text"
                )
```

**Timing**: 10-30 seconds per PDF
**Queue**: `default`

---

#### Phase 2: Image Extraction
**Worker**: `celery-worker-images` (images queue)

```python
@celery_app.task(queue='images')
def extract_images(pdf_id: UUID):
    """Extract images, apply OCR, detect image type"""
    pdf = db.query(PDF).get(pdf_id)

    with fitz.open(pdf.file_path) as doc:
        for page_num, page in enumerate(doc):
            images = page.get_images()

            for img_index, img in enumerate(images):
                # Extract image bytes
                xref = img[0]
                base_image = doc.extract_image(xref)

                # OCR for text in image
                ocr_text = pytesseract.image_to_string(base_image["image"])

                PDFImage(
                    pdf_id=pdf_id,
                    page_number=page_num,
                    image_data=base_image["image"],
                    ocr_text=ocr_text,
                    image_type="unknown"  # Updated in Phase 3
                )
```

**Timing**: 5-15 seconds per PDF
**Queue**: `images`

---

#### Phase 3: Image Analysis with Vision AI
**Worker**: `celery-worker-images` (images queue)

```python
@celery_app.task(queue='images')
def analyze_images_with_vision(pdf_id: UUID):
    """Analyze images with Claude Vision to identify content"""
    images = db.query(PDFImage).filter_by(pdf_id=pdf_id).all()

    for image in images:
        # Use Claude Vision API
        analysis = await claude_vision_api.analyze_image(
            image_bytes=image.image_data,
            prompt="""
            Analyze this medical image and identify:
            1. Image type (anatomical diagram, surgical photo, MRI/CT scan, graph, table)
            2. Anatomical structures visible
            3. Key features and pathology
            4. Clinical relevance

            Return as JSON.
            """
        )

        image.image_type = analysis["image_type"]
        image.anatomical_structures = analysis["anatomical_structures"]
        image.ai_description = analysis["description"]
        image.clinical_relevance = analysis["clinical_relevance"]
```

**Timing**: 2-5 seconds per image
**Cost**: $0.005-0.015 per image
**Queue**: `images`

---

#### Phase 4: Embedding Generation
**Worker**: `celery-worker-embeddings` (embeddings queue)

```python
@celery_app.task(queue='embeddings')
def generate_embeddings(pdf_id: UUID):
    """Generate vector embeddings for all text chunks"""
    chunks = db.query(PDFChunk).filter_by(pdf_id=pdf_id).all()

    # Batch API calls (up to 100 chunks per request)
    for batch in chunks_of(chunks, 100):
        texts = [chunk.content for chunk in batch]

        # OpenAI Embeddings API
        response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts
        )

        for chunk, embedding_data in zip(batch, response.data):
            chunk.embedding = embedding_data.embedding  # 1536 dims
```

**Timing**: 5-15 seconds per PDF (batched)
**Cost**: $0.0001 per 1K tokens × total tokens
**Queue**: `embeddings`

---

#### Phase 5: Citation Network Building
**Worker**: `celery-worker` (default queue)

```python
@celery_app.task(queue='default')
def build_citation_network(pdf_id: UUID):
    """Extract citations and build network"""
    pdf = db.query(PDF).get(pdf_id)
    chunks = db.query(PDFChunk).filter_by(pdf_id=pdf_id).all()

    # Extract DOIs from text
    all_text = " ".join(chunk.content for chunk in chunks)
    cited_dois = extract_dois(all_text)

    # Build citation edges
    for cited_doi in cited_dois:
        cited_pdf = db.query(PDF).filter_by(doi=cited_doi).first()
        if cited_pdf:
            PDFCitation(
                citing_pdf_id=pdf_id,
                cited_pdf_id=cited_pdf.id
            )
```

**Timing**: 3-8 seconds per PDF
**Queue**: `default`

---

## Data Flow & State Management

### Chapter State Transitions

```
┌─────────────┐
│   created   │ Initial database record
└──────┬──────┘
       │
       v
┌─────────────────┐
│ stage_1_input   │ Topic validation (2-4s)
└──────┬──────────┘
       │
       v
┌─────────────────┐
│ stage_2_context │ Context building (3-5s)
└──────┬──────────┘
       │
       v
┌──────────────────────────┐
│ stage_3_internal_research│ Vector search (8-15s)
└──────┬───────────────────┘
       │
       v
┌──────────────────────────┐
│ stage_4_external_research│ PubMed search (9-12s)
└──────┬───────────────────┘
       │
       v
┌─────────────────────┐
│ stage_5_planning    │ Chapter outline (5-8s)
└──────┬──────────────┘
       │
       v
┌─────────────────────┐
│ stage_6_generation  │ Content generation (120-240s) ← Longest stage
└──────┬──────────────┘
       │
       v
┌─────────────────┐
│ stage_7_images  │ Image integration (5-10s)
└──────┬──────────┘
       │
       v
┌──────────────────┐
│ stage_8_citations│ Bibliography (3-5s)
└──────┬───────────┘
       │
       v
┌─────────────┐
│ stage_9_qa  │ Quality metrics (5-8s)
└──────┬──────┘
       │
       v
┌──────────────────────┐
│ stage_10_fact_check  │ Fact verification (15-25s)
└──────┬───────────────┘
       │
       v
┌───────────────────────┐
│ stage_11_formatting   │ HTML formatting (2-3s)
└──────┬────────────────┘
       │
       v
┌─────────────────┐
│ stage_12_review │ Clarity review (8-12s)
└──────┬──────────┘
       │
       v
┌───────────────────────┐
│ stage_13_finalization │ Summary generation (5-8s)
└──────┬────────────────┘
       │
       v
┌──────────────────┐
│ stage_14_delivery│ Final storage (1-2s)
└──────┬───────────┘
       │
       v
┌───────────┐
│ completed │ Generation finished
└───────────┘
```

### Database Persistence

Each stage commits results to the database immediately:

```python
# After each stage
chapter.stage_X_data = {...}
chapter.generation_status = "stage_X_..."
db.commit()

# Allows recovery from failures
# If process crashes at stage 7, can resume from stage 6 data
```

---

## Cost Analysis

### Per-Chapter Cost Breakdown

| Stage | AI Provider | Cost Range | Percentage |
|-------|-------------|------------|------------|
| Stage 1: Input Validation | Claude/GPT-4 | $0.002-0.005 | 0.5% |
| Stage 2: Context Building | GPT-4 | $0.003-0.007 | 1.0% |
| Stage 3: Internal Research | OpenAI Embeddings | $0.005-0.015 | 2.0% |
| Stage 4: External Research | None (PubMed free) | $0 | 0% |
| Stage 5: Planning | Claude Sonnet 4.5 | $0.015-0.030 | 4.0% |
| **Stage 6: Generation** | **Claude Sonnet 4.5** | **$0.30-0.60** | **75%** |
| Stage 9: QA | GPT-4 | $0.010-0.020 | 2.5% |
| Stage 10: Fact-Checking | Claude Sonnet 4.5 | $0.025-0.040 | 5.0% |
| Stage 12: Review | GPT-4 | $0.015-0.025 | 3.0% |
| Stage 13: Finalization | Claude/GPT-4 | $0.008-0.015 | 2.0% |
| **TOTAL** | | **$0.383-0.757** | **100%** |

**Average Cost per Chapter**: $0.50-0.70

**With Caching** (40-65% reduction): $0.25-0.40

---

### PDF Processing Costs

| Phase | AI Provider | Cost per PDF |
|-------|-------------|--------------|
| Phase 1: Text Extraction | None | $0 |
| Phase 2: Image Extraction | None | $0 |
| Phase 3: Image Analysis | Claude Vision | $0.05-0.15 |
| Phase 4: Embeddings | OpenAI ada-002 | $0.01-0.05 |
| Phase 5: Citation Network | None | $0 |
| **TOTAL** | | **$0.06-0.20** |

**Average Cost per PDF**: $0.10-0.15

---

### Monthly Operational Costs (Example)

**Assumptions**:
- 200 chapters generated/month
- 100 PDFs indexed/month
- 40% cache hit rate

**Calculation**:
```
Chapter Generation: 200 × $0.35 (with cache) = $70
PDF Processing: 100 × $0.12 = $12
Total: $82/month
```

**With Phase 2 Enhancements** (Parallel Research + AI Filtering):
- External research AI filtering: +$0.07 per chapter
- Monthly increase: 200 × $0.07 = $14
- **New Total**: $96/month (+17%)

---

## Error Handling & Recovery

### Automatic Retry Logic

```python
# backend/services/chapter_orchestrator.py
async def _execute_stage_with_retry(
    self,
    stage_func: Callable,
    stage_name: str,
    max_retries: int = 3
) -> None:
    """Execute stage with exponential backoff retry"""

    for attempt in range(max_retries):
        try:
            await stage_func()
            return
        except OpenAIError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Stage {stage_name} failed (attempt {attempt+1}), retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                raise
        except Exception as e:
            logger.error(f"Stage {stage_name} failed permanently: {str(e)}")
            raise
```

### State Recovery

```python
# backend/services/chapter_orchestrator.py
async def resume_generation(chapter_id: UUID) -> Chapter:
    """Resume failed generation from last completed stage"""

    chapter = db.query(Chapter).get(chapter_id)

    if chapter.generation_status == "failed":
        # Determine last successful stage
        last_stage = determine_last_successful_stage(chapter)

        # Resume from next stage
        if last_stage == "stage_5_planning":
            await self._stage_6_section_generation(chapter)
        elif last_stage == "stage_6_generation":
            await self._stage_7_image_integration(chapter)
        # ... etc
```

### Error Reporting

All errors emit WebSocket event:

```json
{
  "event": "chapter_failed",
  "chapter_id": "uuid",
  "error": "OpenAI API rate limit exceeded",
  "stage": "stage_6_generation",
  "retry_possible": true,
  "timestamp": "ISO 8601"
}
```

---

## API Endpoints Reference

### Chapter Generation

#### Generate New Chapter
```http
POST /api/v1/chapters/generate
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "topic": "Glioblastoma surgical management",
  "chapter_type": "surgical_disease"  // Optional
}

Response 201:
{
  "chapter_id": "uuid",
  "status": "stage_1_input",
  "websocket_room": "chapter_<uuid>"
}
```

#### Get Chapter Status
```http
GET /api/v1/chapters/{chapter_id}
Authorization: Bearer <jwt_token>

Response 200:
{
  "id": "uuid",
  "title": "Glioblastoma surgical management",
  "generation_status": "stage_6_generation",
  "progress_percent": 45,
  "quality_scores": {
    "depth_score": null,      // Only after stage 9
    "coverage_score": null,
    "evidence_score": null,
    "currency_score": null
  },
  "created_at": "ISO 8601",
  "estimated_completion_time": "2025-10-29T14:35:00Z"
}
```

#### Get Chapter Content
```http
GET /api/v1/chapters/{chapter_id}/content
Authorization: Bearer <jwt_token>

Response 200:
{
  "chapter_id": "uuid",
  "title": "Glioblastoma surgical management",
  "sections": [
    {
      "number": 1,
      "title": "Introduction",
      "content": "<h2>Introduction</h2><p>...</p>",
      "word_count": 450,
      "images": [
        {
          "image_id": "uuid",
          "caption": "MRI showing glioblastoma",
          "url": "/api/v1/images/uuid"
        }
      ]
    }
  ],
  "bibliography": [...]
}
```

---

### Phase 1 New Endpoints (Section Editing)

#### Edit Section Content
```http
PATCH /api/v1/chapters/{chapter_id}/sections/{section_number}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "content": "<h2>Updated Section</h2><p>New content...</p>"
}

Response 200:
{
  "chapter_id": "uuid",
  "section_number": 5,
  "updated_content": "<h2>Updated Section</h2><p>New content...</p>",
  "version": 2,  // New version created automatically
  "updated_at": "ISO 8601"
}
```

#### Regenerate Single Section
```http
POST /api/v1/chapters/{chapter_id}/sections/{section_number}/regenerate
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "additional_sources": ["pdf_id_1", "pdf_id_2"],  // Optional
  "instructions": "Focus more on surgical technique"  // Optional
}

Response 202:
{
  "chapter_id": "uuid",
  "section_number": 5,
  "regeneration_status": "in_progress",
  "websocket_room": "chapter_<uuid>"
}

WebSocket Event (when complete):
{
  "event": "section_regenerated",
  "chapter_id": "uuid",
  "section_number": 5,
  "new_content": "<h2>Regenerated Section</h2>...",
  "cost_usd": 0.08
}
```

#### Add Research Sources
```http
POST /api/v1/chapters/{chapter_id}/sources
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "pdf_ids": ["uuid1", "uuid2"],
  "external_dois": ["10.1234/example"],
  "pubmed_ids": ["12345678"]
}

Response 200:
{
  "chapter_id": "uuid",
  "sources_added": 3,
  "total_sources": 67
}
```

---

## Database Schema

### Chapter Table (Partial)

```sql
CREATE TABLE chapters (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    author_id UUID REFERENCES users(id),
    chapter_type TEXT,  -- 'surgical_disease', 'pure_anatomy', 'surgical_technique'
    generation_status TEXT NOT NULL,  -- 'stage_1_input', 'stage_2_context', ..., 'completed'

    -- Stage data (JSONB columns)
    stage_1_input JSONB,
    stage_2_context JSONB,
    stage_3_internal_research JSONB,
    stage_4_external_research JSONB,
    stage_5_synthesis_plan JSONB,
    stage_6_section_content JSONB,
    stage_7_images JSONB,
    stage_8_citations JSONB,
    stage_9_qa JSONB,
    stage_10_fact_check JSONB,
    stage_11_formatting JSONB,
    stage_12_review JSONB,
    stage_13_finalization JSONB,

    -- Quality scores
    depth_score FLOAT,
    coverage_score FLOAT,
    evidence_score FLOAT,
    currency_score FLOAT,

    -- Metadata
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    generation_error TEXT,

    -- Full content (generated from sections)
    full_content TEXT,
    summary TEXT,
    key_points JSONB,
    tags TEXT[]
);

CREATE INDEX idx_chapters_status ON chapters(generation_status);
CREATE INDEX idx_chapters_author ON chapters(author_id);
CREATE INDEX idx_chapters_type ON chapters(chapter_type);
```

### PDF Chunk Table (Vector Search)

```sql
CREATE TABLE pdf_chunks (
    id UUID PRIMARY KEY,
    pdf_id UUID REFERENCES pdfs(id) ON DELETE CASCADE,
    page_number INTEGER,
    content TEXT NOT NULL,
    chunk_type TEXT,  -- 'text', 'table', 'caption'

    -- Vector embedding (1536 dimensions)
    embedding vector(1536),

    -- Metadata
    word_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- pgvector index for similarity search
CREATE INDEX idx_pdf_chunks_embedding ON pdf_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Standard indexes
CREATE INDEX idx_pdf_chunks_pdf_id ON pdf_chunks(pdf_id);
```

### Chapter Versions Table

```sql
CREATE TABLE chapter_versions (
    id UUID PRIMARY KEY,
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,

    -- Snapshot of content
    content JSONB NOT NULL,  -- Full chapter state
    metadata JSONB,

    -- Version metadata
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    comment TEXT,

    UNIQUE(chapter_id, version)
);

CREATE INDEX idx_chapter_versions_chapter ON chapter_versions(chapter_id);
```

---

## Performance Metrics

### Typical Generation Times

| Chapter Type | Sections | Total Time | Notes |
|--------------|----------|------------|-------|
| Pure Anatomy | 48-80 | 2.5-3.5 min | Shorter, descriptive content |
| Surgical Technique | 60-100 | 3-4 min | Medium complexity |
| Surgical Disease | 80-120 | 4-5 min | Longest, most comprehensive |

### Bottlenecks

1. **Stage 6 (Content Generation)**: 65-75% of total time
   - Limited by AI API response times
   - Cannot parallelize (sections depend on previous context)

2. **Stage 4 (External Research)**: 10-15% of total time
   - PubMed API has rate limits
   - Currently sequential (Phase 2 will parallelize)

3. **Stage 10 (Fact-Checking)**: 8-12% of total time
   - AI verification is thorough but slow

### Optimization Opportunities

| Optimization | Impact | Status |
|--------------|--------|--------|
| Parallel external research | 40% faster Stage 4 | Phase 2 |
| PubMed caching | 300x faster repeated queries | Phase 2 |
| AI relevance filtering | 25% higher quality | Phase 2 |
| Section editing (vs full regen) | 80% cost reduction | Phase 1 |
| Smart deduplication | 30-70% more knowledge | Phase 2 |

---

## Next Steps: Phase 1 Implementation

### Week 1: Documentation ✅ Complete

This file (`WORKFLOW_DOCUMENTATION.md`) provides comprehensive technical documentation of the entire system.

### Weeks 2-3: Section Editing

Implementation plan:

1. **Backend API Endpoints** (2 days)
   - `PATCH /api/v1/chapters/{id}/sections/{section_num}`
   - `POST /api/v1/chapters/{id}/sections/{section_num}/regenerate`
   - `POST /api/v1/chapters/{id}/sources`

2. **Selective Regeneration Logic** (3 days)
   - New method: `chapter_orchestrator.regenerate_section()`
   - Reuse stages 3-5 data (research, planning)
   - Only re-run stage 6 for target section
   - Cost: $0.08 vs $0.50 (84% savings)

3. **React UI Components** (3 days)
   - `<SectionEditor />` with inline editing
   - `<SourceAdder />` for manual source addition
   - `<SectionRegenerateButton />` with loading states
   - Version comparison UI

4. **Testing** (2 days)
   - Unit tests for new endpoints
   - Integration tests for selective regeneration
   - E2E tests for full editing workflow

**Total**: 10 days

**Decision Gate**: Only proceed to Phase 2 if adoption ≥15% of users

---

## Appendix: Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `backend/services/chapter_orchestrator.py` | ~1800 | 14-stage workflow coordinator |
| `backend/services/research_service.py` | ~900 | Vector search + PubMed integration |
| `backend/services/ai_provider_service.py` | ~600 | Multi-provider AI orchestration |
| `backend/utils/websocket_emitter.py` | ~300 | Real-time WebSocket events |
| `frontend/src/components/ChapterViewer.jsx` | ~450 | Real-time chapter display |
| `frontend/src/hooks/useWebSocket.js` | ~200 | WebSocket connection management |

---

**End of Documentation**
