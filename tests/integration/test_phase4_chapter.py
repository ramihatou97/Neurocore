"""
Phase 4 Integration Tests - Chapter Generation
Tests chapter generation workflow, AI integration (mocked), and API endpoints
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import ChapterService, AIProviderService, ResearchService
from backend.database.models import Chapter


# ==================== Mocked AI Responses ====================

MOCK_AI_RESPONSES = {
    "stage_1_input": {
        "text": '{"primary_concepts": ["traumatic brain injury", "management"], "chapter_type": "surgical_disease", "keywords": ["TBI", "trauma", "neurosurgery"], "complexity": "intermediate"}',
        "provider": "claude",
        "cost_usd": 0.01,
        "tokens_used": 100,
        "model": "claude-sonnet-4"
    },
    "stage_2_context": {
        "text": '{"entities": ["traumatic brain injury", "ICP monitoring"], "search_queries": ["TBI management", "intracranial pressure"], "related_topics": ["brain trauma"], "key_questions": ["When to operate?"], "anatomy": ["frontal lobe"]}',
        "provider": "claude",
        "cost_usd": 0.015,
        "tokens_used": 150,
        "model": "claude-sonnet-4"
    },
    "stage_5_planning": {
        "text": '{"sections": [{"title": "Introduction", "key_points": ["Definition", "Epidemiology"], "word_count": 300}, {"title": "Pathophysiology", "key_points": ["Primary injury", "Secondary injury"], "word_count": 500}, {"title": "Management", "key_points": ["Initial assessment", "Surgical indications"], "word_count": 700}]}',
        "provider": "claude",
        "cost_usd": 0.02,
        "tokens_used": 200,
        "model": "claude-sonnet-4"
    },
    "section_content": {
        "text": "# Section Content\n\nThis is a comprehensive section on neurosurgical management. It covers key clinical principles and evidence-based approaches [Author, 2023].",
        "provider": "claude",
        "cost_usd": 0.03,
        "tokens_used": 300,
        "model": "claude-sonnet-4"
    }
}

MOCK_INTERNAL_SOURCES = [
    {
        "pdf_id": "test-pdf-1",
        "title": "Management of TBI",
        "authors": ["Smith et al."],
        "year": 2023,
        "relevance_score": 0.9,
        "doi": "10.1234/test.1"
    }
]

MOCK_EXTERNAL_SOURCES = [
    {
        "pmid": "12345678",
        "title": "Recent advances in TBI management",
        "authors": ["Johnson", "Williams"],
        "year": 2024,
        "journal": "Journal of Neurosurgery",
        "source": "pubmed"
    }
]


# ==================== Service Tests ====================

class TestChapterOrchestrator:
    """Test ChapterOrchestrator 14-stage workflow"""

    @pytest.mark.asyncio
    async def test_stage_1_input_validation(self, db_session, sample_user):
        """Test Stage 1: Input validation"""
        from backend.services.chapter_orchestrator import ChapterOrchestrator

        # Mock AI service
        with patch.object(AIProviderService, 'generate_text', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_AI_RESPONSES["stage_1_input"]

            orchestrator = ChapterOrchestrator(db_session)

            # Create chapter
            chapter = Chapter(
                title="Test Topic",
                author_id=sample_user.id,
                generation_status="stage_1_input"
            )
            db_session.add(chapter)
            db_session.commit()

            # Run stage 1
            await orchestrator._stage_1_input_validation(chapter, "Test Topic")

            assert chapter.stage_1_input is not None
            assert chapter.chapter_type == "surgical_disease"

    @pytest.mark.asyncio
    async def test_stage_2_context_building(self, db_session, sample_user):
        """Test Stage 2: Context building"""
        from backend.services.chapter_orchestrator import ChapterOrchestrator

        with patch.object(AIProviderService, 'generate_text', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_AI_RESPONSES["stage_2_context"]

            orchestrator = ChapterOrchestrator(db_session)

            chapter = Chapter(
                title="Test Topic",
                author_id=sample_user.id,
                generation_status="stage_2_context",
                chapter_type="surgical_disease"
            )
            db_session.add(chapter)
            db_session.commit()

            # Set stage_1_input after commit since it's a JSONB field
            chapter.stage_1_input = {"analysis": {"primary_concepts": ["test"]}}
            db_session.commit()

            await orchestrator._stage_2_context_building(chapter, "Test Topic")

            assert chapter.stage_2_context is not None
            assert "context" in chapter.stage_2_context

    @pytest.mark.asyncio
    async def test_stage_3_internal_research(self, db_session, sample_user):
        """Test Stage 3: Internal research"""
        from backend.services.chapter_orchestrator import ChapterOrchestrator

        with patch.object(ResearchService, 'internal_research', new_callable=AsyncMock) as mock_research:
            mock_research.return_value = MOCK_INTERNAL_SOURCES

            with patch.object(ResearchService, 'search_images', new_callable=AsyncMock) as mock_images:
                mock_images.return_value = []

                with patch.object(ResearchService, 'rank_sources', new_callable=AsyncMock) as mock_rank:
                    mock_rank.return_value = MOCK_INTERNAL_SOURCES

                    orchestrator = ChapterOrchestrator(db_session)

                    chapter = Chapter(
                        title="Test Topic",
                        author_id=sample_user.id,
                        generation_status="stage_3_research_internal",
                        stage_2_context={"context": {"search_queries": ["test query"]}}
                    )
                    db_session.add(chapter)
                    db_session.commit()

                    await orchestrator._stage_3_internal_research(chapter)

                    assert chapter.stage_3_internal_research is not None
                    assert len(chapter.stage_3_internal_research.get("sources", [])) > 0

    @pytest.mark.asyncio
    async def test_stage_4_external_research(self, db_session, sample_user):
        """Test Stage 4: External research (PubMed)"""
        from backend.services.chapter_orchestrator import ChapterOrchestrator

        with patch.object(ResearchService, 'external_research_pubmed', new_callable=AsyncMock) as mock_pubmed:
            mock_pubmed.return_value = MOCK_EXTERNAL_SOURCES

            orchestrator = ChapterOrchestrator(db_session)

            chapter = Chapter(
                title="Test Topic",
                author_id=sample_user.id,
                generation_status="stage_4_research_external",
                stage_2_context={"context": {"search_queries": ["test query"]}}
            )
            db_session.add(chapter)
            db_session.commit()

            await orchestrator._stage_4_external_research(chapter)

            assert chapter.stage_4_external_research is not None
            assert len(chapter.stage_4_external_research.get("sources", [])) > 0

    @pytest.mark.asyncio
    async def test_stage_5_synthesis_planning(self, db_session, sample_user):
        """Test Stage 5: Synthesis planning"""
        from backend.services.chapter_orchestrator import ChapterOrchestrator

        with patch.object(AIProviderService, 'generate_text', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_AI_RESPONSES["stage_5_planning"]

            orchestrator = ChapterOrchestrator(db_session)

            chapter = Chapter(
                title="Test Topic",
                author_id=sample_user.id,
                generation_status="stage_5_planning",
                stage_2_context={"context": {}},
                stage_3_internal_research={"sources": MOCK_INTERNAL_SOURCES},
                stage_4_external_research={"sources": MOCK_EXTERNAL_SOURCES}
            )
            db_session.add(chapter)
            db_session.commit()

            await orchestrator._stage_5_synthesis_planning(chapter)

            assert chapter.structure_metadata is not None
            assert "outline" in chapter.structure_metadata

    @pytest.mark.asyncio
    async def test_stage_6_section_generation(self, db_session, sample_user):
        """Test Stage 6: Section generation"""
        from backend.services.chapter_orchestrator import ChapterOrchestrator

        with patch.object(AIProviderService, 'generate_text', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_AI_RESPONSES["section_content"]

            orchestrator = ChapterOrchestrator(db_session)

            chapter = Chapter(
                title="Test Topic",
                author_id=sample_user.id,
                generation_status="stage_6_generation",
                structure_metadata={
                    "outline": {
                        "sections": [
                            {"title": "Introduction", "key_points": [], "word_count": 300}
                        ]
                    }
                },
                stage_3_internal_research={"sources": []},
                stage_4_external_research={"sources": []}
            )
            db_session.add(chapter)
            db_session.commit()

            await orchestrator._stage_6_section_generation(chapter)

            assert chapter.sections is not None
            assert len(chapter.sections) == 1


# ==================== API Endpoint Tests ====================

class TestChapterEndpoints:
    """Test Chapter API endpoints"""

    def test_chapter_health_check(self, test_client):
        """Test GET /chapters/health endpoint"""
        response = test_client.get("/api/v1/chapters/health")

        assert response.status_code == 200
        assert "message" in response.json()

    @pytest.mark.asyncio
    async def test_create_chapter_without_auth(self, test_client):
        """Test chapter creation without authentication fails"""
        response = test_client.post(
            "/api/v1/chapters",
            json={"topic": "Test topic", "chapter_type": "surgical_disease"}
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_chapters(self, test_client):
        """Test listing chapters"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "chapteruser@test.com",
                "password": "ChapterTest123"
            }
        )
        token = reg_response.json()["access_token"]

        # List chapters
        response = test_client.get(
            "/api/v1/chapters",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_my_chapters(self, test_client):
        """Test getting user's own chapters"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "mychapters@test.com",
                "password": "MyChapters123"
            }
        )
        token = reg_response.json()["access_token"]

        # Get my chapters
        response = test_client.get(
            "/api/v1/chapters/mine",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_chapter_statistics(self, test_client):
        """Test getting chapter statistics"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "stats@test.com",
                "password": "Stats123"
            }
        )
        token = reg_response.json()["access_token"]

        # Get statistics
        response = test_client.get(
            "/api/v1/chapters/statistics",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_chapters" in data
        assert "completed" in data
        assert "completion_rate" in data

    @pytest.mark.asyncio
    async def test_search_chapters(self, test_client):
        """Test searching chapters"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "search@test.com",
                "password": "Search123"
            }
        )
        token = reg_response.json()["access_token"]

        # Search chapters
        response = test_client.get(
            "/api/v1/chapters/search?q=test",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ==================== Service Integration Tests ====================

class TestChapterService:
    """Test ChapterService business logic"""

    def test_get_chapter_statistics(self, db_session):
        """Test chapter statistics calculation"""
        chapter_service = ChapterService(db_session)

        stats = chapter_service.get_chapter_statistics()

        assert "total_chapters" in stats
        assert "completed" in stats
        assert "failed" in stats
        assert "in_progress" in stats
        assert isinstance(stats["completion_rate"], (int, float))

    def test_list_chapters_with_filters(self, db_session, sample_user, sample_chapter):
        """Test listing chapters with type filter"""
        chapter_service = ChapterService(db_session)

        chapters = chapter_service.list_chapters(
            chapter_type="pure_anatomy",
            status="completed",
            skip=0,
            limit=10
        )

        assert isinstance(chapters, list)
        # Should include sample_chapter which has type pure_anatomy
        if chapters:
            assert chapters[0].chapter_type == "pure_anatomy"

    def test_get_user_chapters(self, db_session, sample_user, sample_chapter):
        """Test getting chapters for specific user"""
        chapter_service = ChapterService(db_session)

        chapters = chapter_service.get_user_chapters(
            user_id=str(sample_user.id),
            include_draft=True
        )

        assert isinstance(chapters, list)
        assert len(chapters) > 0
        assert all(str(c.author_id) == str(sample_user.id) for c in chapters)

    def test_export_chapter_markdown(self, db_session, sample_chapter):
        """Test exporting chapter as markdown"""
        chapter_service = ChapterService(db_session)

        # Update chapter to completed status
        sample_chapter.generation_status = "completed"
        db_session.commit()

        markdown = chapter_service.export_chapter_markdown(str(sample_chapter.id))

        assert isinstance(markdown, str)
        assert sample_chapter.title in markdown
        assert "## " in markdown  # Markdown headers
        assert "Quality Metrics" in markdown
