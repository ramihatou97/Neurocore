"""
Pytest configuration and fixtures for testing
Provides test database setup and fixtures for all tests
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os
from fastapi.testclient import TestClient

from backend.database.models import Base
from backend.database import db, get_db
from backend.config import settings
from backend.main import app


# Test database URL - use DB_HOST from settings (postgres in Docker, localhost outside)
TEST_DATABASE_URL = (
    f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@"
    f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)


@pytest.fixture(scope="session")
def engine():
    """
    Create a test engine for the session

    This engine is reused across all tests in the session for performance
    """
    _engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        echo=False  # Set to True for SQL debugging
    )
    yield _engine
    _engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """
    Create a new database session for each test

    Each test gets a fresh session and rolls back all changes after the test completes.
    This ensures test isolation.
    """
    # Create a connection
    connection = engine.connect()

    # Begin a transaction
    transaction = connection.begin()

    # Create a session bound to the connection
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    try:
        yield session
    finally:
        # Rollback the transaction to clean up after the test
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def clean_db(db_session):
    """
    Ensure database is clean for each test

    This fixture can be used when you need a guaranteed clean database state
    """
    # Tables are already clean due to transaction rollback in db_session
    yield db_session


@pytest.fixture(scope="function")
def test_client(db_session):
    """
    Create a FastAPI test client with database session override

    This ensures that API endpoint tests use the same transactional session
    as the rest of the test, enabling proper test isolation.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    # Clean up dependency override
    app.dependency_overrides.clear()


# Model-specific fixtures for convenience


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing"""
    from backend.database.models import User

    user = User(
        email="test@example.com",
        hashed_password="hashed_password_123",
        full_name="Test User",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_pdf(db_session):
    """Create a sample PDF for testing"""
    from backend.database.models import PDF

    pdf = PDF(
        filename="sample_paper.pdf",
        file_path="/test/path/sample_paper.pdf",
        file_size_bytes=1024000,
        total_pages=20,
        title="Sample Research Paper",
        authors=["John Doe", "Jane Smith"],
        publication_year=2023,
        journal="Neurosurgery Journal",
        doi="10.1234/test.doi",
        pmid="12345678",
        indexing_status="completed",
        text_extracted=True,
        images_extracted=True,
        embeddings_generated=True
    )
    db_session.add(pdf)
    db_session.commit()
    db_session.refresh(pdf)
    return pdf


@pytest.fixture
def sample_chapter(db_session, sample_user):
    """Create a sample chapter for testing"""
    from backend.database.models import Chapter

    chapter = Chapter(
        title="Neuroanatomy of the Brain",
        chapter_type="pure_anatomy",
        sections=[
            {
                "section_num": 1,
                "title": "Introduction",
                "content": "This is the introduction content.",
                "word_count": 50
            },
            {
                "section_num": 2,
                "title": "Anatomy",
                "content": "This is the anatomy content.",
                "word_count": 100
            }
        ],
        structure_metadata={"total_sections": 2, "total_words": 150},
        stage_2_context={"entities": ["brain", "cerebrum"], "chapter_type_reasoning": "Pure anatomical structure"},
        generation_status="completed",
        version="1.0",
        is_current_version=True,
        author_id=sample_user.id,
        depth_score=0.85,
        coverage_score=0.90,
        currency_score=0.75,
        evidence_score=0.88
    )
    db_session.add(chapter)
    db_session.commit()
    db_session.refresh(chapter)
    return chapter


@pytest.fixture
def sample_image(db_session, sample_pdf):
    """Create a sample image for testing"""
    from backend.database.models import Image

    image = Image(
        pdf_id=sample_pdf.id,
        page_number=5,
        image_index_on_page=0,
        file_path="/test/images/image_001.png",
        thumbnail_path="/test/images/thumbnails/image_001_thumb.png",
        width=1920,
        height=1080,
        format="PNG",
        file_size_bytes=256000,
        ai_description="Anatomical diagram showing the cerebral cortex with labeled regions",
        image_type="anatomical_diagram",
        anatomical_structures=["cerebral cortex", "frontal lobe", "parietal lobe"],
        clinical_context="Used to illustrate cortical anatomy in neurosurgical planning",
        quality_score=0.92,
        confidence_score=0.95,
        ocr_text="Figure 3.2: Cerebral Cortex",
        contains_text=True,
        is_duplicate=False
    )
    db_session.add(image)
    db_session.commit()
    db_session.refresh(image)
    return image


@pytest.fixture
def sample_citation(db_session, sample_pdf):
    """Create a sample citation for testing"""
    from backend.database.models import Citation

    citation = Citation(
        pdf_id=sample_pdf.id,
        cited_title="Advanced Neurosurgical Techniques",
        cited_authors=["Dr. Smith", "Dr. Johnson"],
        cited_journal="Journal of Neurosurgery",
        cited_year=2022,
        cited_doi="10.5678/citation.doi",
        cited_pmid="87654321",
        citation_context="As described by Smith et al., the technique shows promising results...",
        page_number=15,
        citation_count=5,
        relevance_score=0.88
    )
    db_session.add(citation)
    db_session.commit()
    db_session.refresh(citation)
    return citation


@pytest.fixture
def sample_cache_analytics(db_session, sample_user, sample_chapter):
    """Create sample cache analytics for testing"""
    from backend.database.models import CacheAnalytics

    analytics = CacheAnalytics(
        cache_type="hot",
        cache_category="embedding",
        operation="hit",
        key_hash="a" * 64,  # 64-char hash
        cost_saved_usd=0.0025,
        time_saved_ms=150,
        user_id=sample_user.id,
        chapter_id=sample_chapter.id
    )
    db_session.add(analytics)
    db_session.commit()
    db_session.refresh(analytics)
    return analytics
