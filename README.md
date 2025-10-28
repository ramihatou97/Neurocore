# Neurosurgery Knowledge Base

> **Status**: Phase 19 Complete ✅ | All 8 containers running | 47 database tables | Production Ready

An AI-powered neurosurgery knowledge base system with intelligent chapter generation, real-time streaming, and continuous evolution capabilities.

## Overview

This system implements a comprehensive 14-stage workflow for creating "Alive Chapters" - dynamic, continuously evolving neurosurgical knowledge that combines:

- **Process A**: Background 24/7 PDF indexation with AI-powered analysis
- **Process B**: User-requested chapter generation with real-time streaming

### Key Features

- **Smart Caching**: 40-65% cost reduction through hybrid hot/cold cache with pattern recognition
- **Real-time Streaming**: WebSocket-based incremental section delivery as content is generated
- **Version Control**: Git-like snapshots with comparison and rollback capabilities
- **Smart Gap Detection**: AI-powered content gap analysis and recommendations
- **Document Integration**: Deep 5-phase integration of user-provided documents
- **Alive Chapter**: Q&A engine, behavioral learning, and continuous evolution
- **Multi-Provider AI**: Claude Sonnet 4.5, GPT-4/5, Gemini Pro 2.5 orchestration

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15 with pgvector extension
- **Cache**: Redis 7 with hybrid hot/cold architecture
- **AI Providers**: Anthropic Claude, OpenAI, Google Gemini
- **PDF Processing**: PyMuPDF, pdfplumber
- **Image Processing**: EasyOCR, Tesseract, OpenCV
- **Vector Embeddings**: OpenAI text-embedding-ada-002 (1536 dimensions)

### Frontend
- **Framework**: React 18 with Vite
- **Styling**: Tailwind CSS
- **State Management**: React Context + Hooks
- **Real-time**: WebSocket connections for streaming

### Infrastructure
- **Containerization**: Docker Compose
- **Authentication**: JWT with bcrypt password hashing
- **Testing**: pytest, pytest-asyncio

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 22+ (for frontend development)
- API Keys:
  - OpenAI API key
  - Anthropic API key
  - Google API key

### Installation

1. **Clone the repository**
```bash
cd "/Users/ramihatoum/Desktop/The neurosurgical core of knowledge"
```

2. **Create environment file**
```bash
cp .env.example .env
```

3. **Configure environment variables**

Edit `.env` and set:
- `DB_PASSWORD`: Secure PostgreSQL password
- `JWT_SECRET`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `OPENAI_API_KEY`: Your OpenAI API key
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `GOOGLE_API_KEY`: Your Google API key

4. **Start services with Docker Compose**
```bash
docker-compose up -d
```

5. **Verify services are running**
```bash
docker-compose ps
```

All 8 services should show as "Up" or "healthy":
- `neurocore-postgres` (PostgreSQL + pgvector)
- `neurocore-redis` (Redis)
- `neurocore-api` (FastAPI Backend)
- `neurocore-frontend` (React Frontend)
- `neurocore-celery-worker` (Background tasks - default queue)
- `neurocore-celery-worker-embeddings` (Embeddings generation)
- `neurocore-celery-worker-images` (Image analysis)
- `neurocore-celery-flower` (Celery monitoring UI)

6. **Access the application**
- API: http://localhost:8002
- API Docs: http://localhost:8002/api/docs
- Frontend: http://localhost:3002
- Celery Flower: http://localhost:5555

## Architecture

### Process A: Background PDF Indexation

Continuous 24/7 background process that:
1. Monitors for new PDF uploads
2. Extracts text, images, tables using PyMuPDF
3. Analyzes images with Claude Vision (anatomical structures, clinical context)
4. Generates vector embeddings with OpenAI ada-002
5. Builds citation network
6. Stores in PostgreSQL with pgvector indexes

### Process B: Chapter Generation (14 Stages)

**Stage 0**: Continuous background indexation (Process A)

**Stage 1**: Authentication & Authorization
- JWT-based user authentication
- Session management

**Stage 2**: Context Intelligence
- Extract medical entities (anatomy, procedures, conditions)
- Determine chapter type (surgical disease, pure anatomy, surgical technique)

**Stage 3**: Internal Research
- Vector search across indexed library
- Retrieve relevant PDFs, images, citations
- Hybrid smart caching with pattern recognition

**Stage 4**: External Research (Optional)
- Gemini 2.5 Deep Search → Perplexity → OpenAI
- PubMed, Google Scholar, arXiv integration
- Citation extraction and ranking

**Stage 5**: Primary Synthesis
- Claude Sonnet 4.5 → GPT-4/5 fallback
- Adaptive sectioning (48-150 sections based on chapter type)
- Image selection and integration
- Quality assessment (depth, coverage, currency, evidence)
- Real-time WebSocket streaming of completed sections

**Stage 6**: Smart Gap Detection
- Coverage analysis (missing topics)
- User demand analysis (frequently requested)
- Literature currency (recent advances)
- Semantic completeness

**Stage 7**: Decision Point
- User reviews gaps
- Decides to fill gaps or proceed

**Stage 8**: Document Integration (Optional)
- 5-phase deep analysis (analyze, map, extract, plan, execute)
- Nuance merge engine with 7 similarity algorithms
- Conflict detection and resolution

**Stage 9**: Secondary Evidence-Based Enrichment
- Additional citations
- Cross-references
- Statistical data

**Stage 10**: Summary Generation
- Key points extraction
- Clinical pearls
- Practice recommendations

**Stage 11**: Alive Chapter Creation
- Q&A engine for chapter content
- Behavioral learning from user interactions

**Stages 12-14**: Continuous Evolution
- Literature monitoring (automated PubMed alerts)
- Auto-update recommendations
- Community feedback integration

## Project Structure

```
.
├── backend/
│   ├── config/           # Settings and configuration
│   ├── database/         # Models, migrations, connection
│   │   ├── models/       # SQLAlchemy models
│   │   └── migrations/   # SQL migration scripts
│   ├── services/         # Business logic services
│   ├── api/              # FastAPI routes
│   ├── workers/          # Background workers
│   ├── utils/            # Utilities and helpers
│   └── main.py           # FastAPI application entry
├── frontend/
│   └── src/
│       ├── components/   # React components
│       ├── services/     # API client
│       └── hooks/        # Custom React hooks
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── e2e/              # End-to-end tests
│   └── fixtures/         # Test fixtures and sample data
├── docker/               # Dockerfiles
├── docker-compose.yml    # Docker Compose configuration
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/unit/test_auth_service.py -v

# Run integration tests only
pytest tests/integration/ -v
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Run migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Code Quality

```bash
# Format code
black backend/

# Sort imports
isort backend/

# Type checking
mypy backend/

# Linting
flake8 backend/
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user info

### PDFs
- `POST /api/v1/pdfs/upload` - Upload PDF file
- `POST /api/v1/pdfs/{pdf_id}/process` - Trigger PDF processing
- `GET /api/v1/pdfs/{pdf_id}/status` - Get PDF processing status

### Chapters
- `POST /api/v1/chapters/generate` - Generate new chapter
- `GET /api/v1/chapters/{id}` - Get chapter by ID
- `GET /api/v1/chapters/{id}/gaps` - Get detected gaps
- `POST /api/v1/chapters/{id}/integrate` - Integrate user document
- `POST /api/v1/chapters/{id}/qa` - Ask question about chapter

### WebSocket
- `WS /api/v1/ws/chapter/{session_id}?token=<jwt>` - Real-time chapter streaming
- `WS /api/v1/ws/dashboard?token=<jwt>` - Real-time metrics dashboard

## Environment Variables

See `.env.example` for full list. Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `DB_PASSWORD` | PostgreSQL password | Yes |
| `JWT_SECRET` | JWT signing secret (256-bit) | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | Yes |
| `GOOGLE_API_KEY` | Google Gemini API key | Yes |
| `PUBMED_EMAIL` | Email for PubMed API | Recommended |

## Deployment

### Production Configuration

1. Update `docker-compose.yml` for production:
   - Remove `--reload` flags
   - Add restart policies
   - Configure resource limits

2. Set production environment variables:
   - Use strong passwords
   - Rotate JWT secrets regularly
   - Enable HTTPS

3. Configure backups:
   - PostgreSQL database backups
   - Redis persistence
   - PDF/image storage backups

### Monitoring

- Health checks: `/health`
- Metrics: Enable `ENABLE_METRICS=true`
- Cache analytics: `ENABLE_CACHE_ANALYTICS=true`

## License

Proprietary - All rights reserved

## Support

For issues and questions, contact the development team.

## Version

Current version: 1.0.0

Last updated: 2025
