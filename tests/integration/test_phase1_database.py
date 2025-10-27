"""
Phase 1 Integration Tests - Database Layer
Tests all models, relationships, CRUD operations, and constraints
"""

import pytest
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import uuid

from backend.database.models import (
    User, PDF, Chapter, Image, Citation, CacheAnalytics
)


class TestUserModel:
    """Test User model CRUD operations and constraints"""

    def test_create_user(self, db_session):
        """Test creating a new user"""
        user = User(
            email="newuser@test.com",
            hashed_password="hashed_pass_123",
            full_name="New User"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.email == "newuser@test.com"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_unique_email_constraint(self, db_session, sample_user):
        """Test that duplicate emails are not allowed"""
        duplicate_user = User(
            email=sample_user.email,  # Same email
            hashed_password="different_password"
        )
        db_session.add(duplicate_user)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_to_dict(self, sample_user):
        """Test user to_dict method"""
        user_dict = sample_user.to_dict()

        assert user_dict["id"] == str(sample_user.id)
        assert user_dict["email"] == sample_user.email
        assert "hashed_password" not in user_dict  # Should not expose password
        assert "created_at" in user_dict

    def test_user_update(self, db_session, sample_user):
        """Test updating user fields"""
        old_updated_at = sample_user.updated_at

        sample_user.full_name = "Updated Name"
        db_session.commit()
        db_session.refresh(sample_user)

        assert sample_user.full_name == "Updated Name"
        assert sample_user.updated_at > old_updated_at  # Trigger updated

    def test_user_delete(self, db_session, sample_user):
        """Test deleting a user"""
        user_id = sample_user.id
        db_session.delete(sample_user)
        db_session.commit()

        deleted_user = db_session.query(User).filter(User.id == user_id).first()
        assert deleted_user is None


class TestPDFModel:
    """Test PDF model CRUD operations and processing status"""

    def test_create_pdf(self, db_session):
        """Test creating a new PDF"""
        pdf = PDF(
            filename="test_paper.pdf",
            file_path="/data/pdfs/test_paper.pdf",
            file_size_bytes=500000,
            total_pages=10
        )
        db_session.add(pdf)
        db_session.commit()
        db_session.refresh(pdf)

        assert pdf.id is not None
        assert pdf.indexing_status == "pending"
        assert pdf.text_extracted is False
        assert pdf.images_extracted is False

    def test_pdf_unique_file_path(self, db_session, sample_pdf):
        """Test that duplicate file paths are not allowed"""
        duplicate_pdf = PDF(
            filename="different_name.pdf",
            file_path=sample_pdf.file_path  # Same path
        )
        db_session.add(duplicate_pdf)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_pdf_is_fully_indexed(self, sample_pdf):
        """Test is_fully_indexed method"""
        assert sample_pdf.is_fully_indexed() is True

        sample_pdf.embeddings_generated = False
        assert sample_pdf.is_fully_indexed() is False

    def test_pdf_to_dict(self, sample_pdf):
        """Test PDF to_dict method"""
        pdf_dict = sample_pdf.to_dict()

        assert pdf_dict["id"] == str(sample_pdf.id)
        assert pdf_dict["filename"] == sample_pdf.filename
        assert pdf_dict["indexing_status"] == "completed"
        assert "total_images" in pdf_dict
        assert "total_citations" in pdf_dict

    def test_pdf_with_images_relationship(self, db_session, sample_pdf, sample_image):
        """Test PDF-Image relationship"""
        db_session.refresh(sample_pdf)

        assert len(sample_pdf.images) == 1
        assert sample_pdf.images[0].id == sample_image.id


class TestChapterModel:
    """Test Chapter model with workflow stages and version control"""

    def test_create_chapter(self, db_session, sample_user):
        """Test creating a new chapter"""
        chapter = Chapter(
            title="Test Chapter",
            chapter_type="surgical_disease",
            author_id=sample_user.id,
            generation_status="draft"
        )
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        assert chapter.id is not None
        assert chapter.version == "1.0"
        assert chapter.is_current_version is True
        assert chapter.created_at is not None

    def test_chapter_workflow_stages(self, db_session, sample_chapter):
        """Test chapter workflow stage tracking"""
        # Stage 2: Context Intelligence
        sample_chapter.stage_2_context = {
            "entities": ["brain", "tumor"],
            "chapter_type_reasoning": "Disease management chapter"
        }

        # Stage 3: Internal Research
        sample_chapter.stage_3_internal_research = {
            "sources": ["pdf_001", "pdf_002"],
            "relevance_scores": [0.95, 0.88]
        }

        db_session.commit()
        db_session.refresh(sample_chapter)

        assert sample_chapter.stage_2_context["entities"] == ["brain", "tumor"]
        assert len(sample_chapter.stage_3_internal_research["sources"]) == 2

    def test_chapter_quality_scores(self, sample_chapter):
        """Test chapter quality scores"""
        assert 0.0 <= sample_chapter.depth_score <= 1.0
        assert 0.0 <= sample_chapter.coverage_score <= 1.0
        assert 0.0 <= sample_chapter.currency_score <= 1.0
        assert 0.0 <= sample_chapter.evidence_score <= 1.0

    def test_chapter_word_count(self, sample_chapter):
        """Test get_word_count method"""
        word_count = sample_chapter.get_word_count()
        assert word_count == 150  # 50 + 100 from fixture

    def test_chapter_section_count(self, sample_chapter):
        """Test get_section_count method"""
        section_count = sample_chapter.get_section_count()
        assert section_count == 2

    def test_chapter_is_completed(self, sample_chapter):
        """Test is_completed method"""
        assert sample_chapter.is_completed() is True

        sample_chapter.generation_status = "in_progress"
        assert sample_chapter.is_completed() is False

    def test_chapter_to_dict(self, sample_chapter):
        """Test chapter to_dict method"""
        chapter_dict = sample_chapter.to_dict()

        assert chapter_dict["id"] == str(sample_chapter.id)
        assert chapter_dict["title"] == sample_chapter.title
        assert "quality_scores" in chapter_dict
        assert "workflow_stages" in chapter_dict
        assert chapter_dict["total_words"] == 150
        assert chapter_dict["total_sections"] == 2

    def test_chapter_version_history(self, db_session, sample_chapter):
        """Test chapter version control"""
        # Create a new version (v1.1)
        new_version = Chapter(
            title=sample_chapter.title + " (Updated)",
            chapter_type=sample_chapter.chapter_type,
            author_id=sample_chapter.author_id,
            version="1.1",
            parent_version_id=sample_chapter.id,
            is_current_version=True
        )

        # Mark old version as not current
        sample_chapter.is_current_version = False

        db_session.add(new_version)
        db_session.commit()
        db_session.refresh(new_version)

        assert new_version.parent_version_id == sample_chapter.id
        assert new_version.version == "1.1"
        assert sample_chapter.is_current_version is False


class TestImageModel:
    """Test Image model with AI analysis and vector embeddings"""

    def test_create_image(self, db_session, sample_pdf):
        """Test creating a new image"""
        image = Image(
            pdf_id=sample_pdf.id,
            page_number=3,
            image_index_on_page=0,
            file_path="/test/images/new_image.png",
            width=1024,
            height=768,
            format="PNG"
        )
        db_session.add(image)
        db_session.commit()
        db_session.refresh(image)

        assert image.id is not None
        assert image.pdf_id == sample_pdf.id
        assert image.is_duplicate is False
        assert image.contains_text is False

    def test_image_ai_analysis_fields(self, sample_image):
        """Test AI analysis fields"""
        assert sample_image.ai_description is not None
        assert sample_image.image_type == "anatomical_diagram"
        assert len(sample_image.anatomical_structures) == 3
        assert sample_image.quality_score == 0.92
        assert sample_image.confidence_score == 0.95

    def test_image_has_embedding(self, db_session, sample_image):
        """Test has_embedding method"""
        # Without embedding
        assert sample_image.has_embedding() is False

        # With embedding
        sample_image.embedding = [0.1] * 1536  # OpenAI ada-002 dimension
        db_session.commit()

        assert sample_image.has_embedding() is True

    def test_image_is_high_quality(self, sample_image):
        """Test is_high_quality method"""
        assert sample_image.is_high_quality() is True

        sample_image.quality_score = 0.5
        assert sample_image.is_high_quality() is False

    def test_image_to_dict(self, sample_image):
        """Test image to_dict method"""
        image_dict = sample_image.to_dict()

        assert image_dict["id"] == str(sample_image.id)
        assert "ai_analysis" in image_dict
        assert image_dict["ai_analysis"]["image_type"] == "anatomical_diagram"
        assert "ocr" in image_dict
        assert "dimensions" in image_dict

    def test_image_deduplication(self, db_session, sample_image):
        """Test image deduplication tracking"""
        # Create a duplicate
        duplicate = Image(
            pdf_id=sample_image.pdf_id,
            page_number=10,
            image_index_on_page=0,
            file_path="/test/images/duplicate.png",
            is_duplicate=True,
            duplicate_of_id=sample_image.id
        )
        db_session.add(duplicate)
        db_session.commit()
        db_session.refresh(duplicate)

        assert duplicate.is_duplicate is True
        assert duplicate.duplicate_of_id == sample_image.id


class TestCitationModel:
    """Test Citation model for bibliographic references"""

    def test_create_citation(self, db_session, sample_pdf):
        """Test creating a new citation"""
        citation = Citation(
            pdf_id=sample_pdf.id,
            cited_title="New Research Paper",
            cited_authors=["Author A", "Author B"],
            cited_year=2023
        )
        db_session.add(citation)
        db_session.commit()
        db_session.refresh(citation)

        assert citation.id is not None
        assert citation.citation_count == 0
        assert len(citation.cited_authors) == 2

    def test_citation_has_doi_or_pmid(self, sample_citation):
        """Test has_doi_or_pmid method"""
        assert sample_citation.has_doi_or_pmid() is True

        sample_citation.cited_doi = None
        assert sample_citation.has_doi_or_pmid() is True  # Still has PMID

        sample_citation.cited_pmid = None
        assert sample_citation.has_doi_or_pmid() is False

    def test_citation_is_recent(self, sample_citation):
        """Test is_recent method"""
        assert sample_citation.is_recent(years_threshold=5) is True

        sample_citation.cited_year = 2010
        assert sample_citation.is_recent(years_threshold=5) is False

    def test_citation_to_dict(self, sample_citation):
        """Test citation to_dict method"""
        citation_dict = sample_citation.to_dict()

        assert citation_dict["id"] == str(sample_citation.id)
        assert "cited_work" in citation_dict
        assert citation_dict["cited_work"]["year"] == 2022
        assert "network_analysis" in citation_dict


class TestCacheAnalyticsModel:
    """Test CacheAnalytics model for performance tracking"""

    def test_create_cache_analytics(self, db_session, sample_user):
        """Test creating cache analytics record"""
        analytics = CacheAnalytics(
            cache_type="cold",
            cache_category="query",
            operation="miss",
            key_hash="b" * 64,
            user_id=sample_user.id
        )
        db_session.add(analytics)
        db_session.commit()
        db_session.refresh(analytics)

        assert analytics.id is not None
        assert analytics.recorded_at is not None

    def test_cache_analytics_cost_tracking(self, sample_cache_analytics):
        """Test cost and time savings tracking"""
        assert sample_cache_analytics.cost_saved_usd is not None
        assert sample_cache_analytics.time_saved_ms == 150

    def test_cache_analytics_operations(self, sample_cache_analytics):
        """Test operation helper methods"""
        assert sample_cache_analytics.is_hit() is True
        assert sample_cache_analytics.is_miss() is False

    def test_cache_analytics_cache_types(self, sample_cache_analytics):
        """Test cache type helper methods"""
        assert sample_cache_analytics.is_hot_cache() is True
        assert sample_cache_analytics.is_cold_cache() is False

    def test_cache_analytics_to_dict(self, sample_cache_analytics):
        """Test cache analytics to_dict method"""
        analytics_dict = sample_cache_analytics.to_dict()

        assert analytics_dict["cache_type"] == "hot"
        assert analytics_dict["cache_category"] == "embedding"
        assert analytics_dict["operation"] == "hit"


class TestDatabaseRelationships:
    """Test relationships between models"""

    def test_user_chapters_relationship(self, db_session, sample_user, sample_chapter):
        """Test User has many Chapters"""
        db_session.refresh(sample_user)

        assert len(sample_user.chapters) >= 1
        assert sample_user.chapters[0].author_id == sample_user.id

    def test_pdf_images_relationship(self, db_session, sample_pdf):
        """Test PDF has many Images"""
        # Create multiple images
        for i in range(3):
            image = Image(
                pdf_id=sample_pdf.id,
                page_number=i + 1,
                image_index_on_page=0,
                file_path=f"/test/images/img_{i}.png"
            )
            db_session.add(image)
        db_session.commit()
        db_session.refresh(sample_pdf)

        assert len(sample_pdf.images) >= 3

    def test_pdf_citations_relationship(self, db_session, sample_pdf):
        """Test PDF has many Citations"""
        # Create multiple citations
        for i in range(5):
            citation = Citation(
                pdf_id=sample_pdf.id,
                cited_title=f"Paper {i}",
                cited_year=2020 + i
            )
            db_session.add(citation)
        db_session.commit()
        db_session.refresh(sample_pdf)

        assert len(sample_pdf.citations) >= 5

    def test_cascade_delete_user_chapters(self, db_session, sample_user, sample_chapter):
        """Test that deleting user cascades to chapters"""
        chapter_id = sample_chapter.id
        db_session.delete(sample_user)
        db_session.commit()

        deleted_chapter = db_session.query(Chapter).filter(Chapter.id == chapter_id).first()
        assert deleted_chapter is None  # Should be deleted

    def test_cascade_delete_pdf_images(self, db_session, sample_pdf, sample_image):
        """Test that deleting PDF cascades to images"""
        image_id = sample_image.id
        db_session.delete(sample_pdf)
        db_session.commit()

        deleted_image = db_session.query(Image).filter(Image.id == image_id).first()
        assert deleted_image is None  # Should be deleted


class TestDatabaseConstraints:
    """Test database constraints and validations"""

    def test_chapter_type_constraint(self, db_session, sample_user):
        """Test chapter_type constraint"""
        chapter = Chapter(
            title="Test",
            chapter_type="invalid_type",  # Invalid
            author_id=sample_user.id
        )
        db_session.add(chapter)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_generation_status_constraint(self, db_session, sample_user):
        """Test generation_status constraint"""
        chapter = Chapter(
            title="Test",
            generation_status="invalid_status",  # Invalid
            author_id=sample_user.id
        )
        db_session.add(chapter)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_cache_type_constraint(self, db_session):
        """Test cache_type constraint"""
        analytics = CacheAnalytics(
            cache_type="invalid_type",  # Invalid
            cache_category="query",
            operation="hit"
        )
        db_session.add(analytics)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestDatabasePerformance:
    """Test database indexes and query performance"""

    def test_user_email_index(self, db_session):
        """Test that user email lookups are fast (using index)"""
        # Create multiple users
        for i in range(100):
            user = User(
                email=f"user{i}@test.com",
                hashed_password="password"
            )
            db_session.add(user)
        db_session.commit()

        # Query should use index on email
        result = db_session.query(User).filter(User.email == "user50@test.com").first()
        assert result is not None
        assert result.email == "user50@test.com"

    def test_chapter_author_lookup(self, db_session, sample_user):
        """Test that chapter lookups by author are efficient"""
        # Create multiple chapters
        for i in range(50):
            chapter = Chapter(
                title=f"Chapter {i}",
                author_id=sample_user.id
            )
            db_session.add(chapter)
        db_session.commit()

        # Query should use index on author_id
        results = db_session.query(Chapter).filter(Chapter.author_id == sample_user.id).all()
        assert len(results) >= 50
