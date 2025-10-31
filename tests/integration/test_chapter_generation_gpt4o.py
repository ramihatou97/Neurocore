"""
Integration Tests for Chapter Generation with GPT-4o
Tests the complete chapter generation pipeline with Phase 1-4 enhancements

Focus:
- Stage 1 & 2 with structured outputs
- Stage 10 with fact-checking
- End-to-end chapter generation
- Cost tracking and analytics
"""

import pytest
import asyncio
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from backend.services.chapter_orchestrator import ChapterOrchestrator
from backend.services.ai_provider_service import AIProviderService
from backend.services.fact_checking_service import FactCheckingService
from backend.database.models import Chapter, User
from backend.database.connection import get_db, SessionLocal
from backend.schemas.ai_schemas import validate_schema_response


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def db_session():
    """Create test database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """Create test user"""
    user = User(
        email="test@neurosurgery.com",
        username="test_user",
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def chapter_orchestrator(db_session):
    """Create chapter orchestrator instance"""
    return ChapterOrchestrator(db_session)


# ============================================================================
# STAGE 1 & 2 INTEGRATION TESTS
# ============================================================================

class TestStage1And2StructuredOutputs:
    """Test Stage 1 and 2 with structured outputs"""

    @pytest.mark.asyncio
    async def test_stage_1_input_validation(self, chapter_orchestrator, db_session, test_user):
        """Test Stage 1 with CHAPTER_ANALYSIS_SCHEMA"""
        topic = "Surgical management of glioblastoma multiforme"

        # Create chapter
        chapter = Chapter(
            title=topic,
            author_id=test_user.id,
            generation_status="pending"
        )
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        # Run Stage 1
        await chapter_orchestrator._stage_1_input_validation(chapter, topic)

        # Verify chapter was updated
        assert chapter.generation_status == "stage_1_input"
        assert chapter.stage_1_input is not None

        # Verify structured output metadata
        stage_1_data = chapter.stage_1_input
        assert stage_1_data["schema_validated"] is True
        assert "analysis" in stage_1_data

        # Verify analysis structure
        analysis = stage_1_data["analysis"]
        assert "primary_concepts" in analysis
        assert "chapter_type" in analysis
        assert "keywords" in analysis
        assert "complexity" in analysis
        assert "estimated_section_count" in analysis

        # Verify data types and constraints
        assert isinstance(analysis["primary_concepts"], list)
        assert len(analysis["primary_concepts"]) >= 1
        assert analysis["chapter_type"] in ["surgical_disease", "pure_anatomy", "surgical_technique"]
        assert isinstance(analysis["keywords"], list)
        assert 3 <= len(analysis["keywords"]) <= 20
        assert 10 <= analysis["estimated_section_count"] <= 150

        # Schema validation should pass
        assert validate_schema_response(analysis, "chapter_analysis") is True

        # Verify chapter type was set
        assert chapter.chapter_type is not None

        # Verify cost tracking
        assert "ai_cost_usd" in stage_1_data
        assert stage_1_data["ai_cost_usd"] > 0

    @pytest.mark.asyncio
    async def test_stage_2_context_building(self, chapter_orchestrator, db_session, test_user):
        """Test Stage 2 with CONTEXT_BUILDING_SCHEMA"""
        topic = "Craniotomy for brain tumor resection"

        # Create chapter with Stage 1 data
        chapter = Chapter(
            title=topic,
            author_id=test_user.id,
            chapter_type="surgical_technique",
            stage_1_input={
                "analysis": {
                    "primary_concepts": ["craniotomy", "brain tumor", "resection"],
                    "chapter_type": "surgical_technique",
                    "keywords": ["craniotomy", "tumor", "neurosurgery"],
                    "complexity": "advanced",
                    "estimated_section_count": 40
                }
            }
        )
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        # Run Stage 2
        await chapter_orchestrator._stage_2_context_building(chapter, topic)

        # Verify chapter was updated
        assert chapter.generation_status == "stage_2_context"
        assert chapter.stage_2_context is not None

        # Verify structured output metadata
        stage_2_data = chapter.stage_2_context
        assert stage_2_data["schema_validated"] is True
        assert "context" in stage_2_data

        # Verify context structure
        context = stage_2_data["context"]
        assert "research_gaps" in context
        assert "key_references" in context
        assert "content_categories" in context
        assert "confidence_assessment" in context

        # Verify data types
        assert isinstance(context["research_gaps"], list)
        assert isinstance(context["key_references"], list)
        assert isinstance(context["content_categories"], dict)
        assert isinstance(context["confidence_assessment"], dict)

        # Verify confidence assessment structure
        confidence = context["confidence_assessment"]
        assert "overall_confidence" in confidence
        assert "evidence_quality" in confidence
        assert 0 <= confidence["overall_confidence"] <= 1
        assert confidence["evidence_quality"] in ["high", "moderate", "low", "very_low"]

        # Schema validation should pass
        assert validate_schema_response(context, "research_context") is True

        # Verify metadata
        assert "research_gaps_count" in stage_2_data
        assert "key_references_count" in stage_2_data
        assert "confidence_score" in stage_2_data
        assert stage_2_data["ai_cost_usd"] > 0


# ============================================================================
# STAGE 10 FACT-CHECKING INTEGRATION TESTS
# ============================================================================

class TestStage10FactChecking:
    """Test Stage 10 fact-checking integration"""

    @pytest.mark.asyncio
    async def test_stage_10_fact_checking_with_sources(
        self,
        chapter_orchestrator,
        db_session,
        test_user
    ):
        """Test Stage 10 with research sources"""
        # Create chapter with sections and sources
        chapter = Chapter(
            title="Glioblastoma Management",
            author_id=test_user.id,
            chapter_type="surgical_disease",
            sections=[
                {
                    "section_num": 1,
                    "title": "Introduction",
                    "content": """
                    Glioblastoma is the most aggressive primary brain tumor in adults.
                    It accounts for approximately 45% of all malignant brain tumors.
                    Standard treatment involves maximal safe surgical resection.
                    """
                },
                {
                    "section_num": 2,
                    "title": "Treatment",
                    "content": """
                    The standard of care includes surgery followed by radiation and chemotherapy.
                    Temozolomide is the chemotherapy agent of choice.
                    """
                }
            ],
            stage_3_internal_research={
                "sources": [
                    {
                        "title": "Glioblastoma: Standard of Care",
                        "authors": ["Smith J"],
                        "year": 2024,
                        "pmid": "12345678",
                        "abstract": "Glioblastoma management requires multimodal therapy..."
                    }
                ]
            },
            stage_4_external_research={
                "sources": [
                    {
                        "title": "Temozolomide in Glioblastoma",
                        "authors": ["Johnson M"],
                        "year": 2023,
                        "pmid": "87654321",
                        "abstract": "Temozolomide combined with radiation improves survival..."
                    }
                ]
            }
        )
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        # Run Stage 10
        await chapter_orchestrator._stage_10_fact_checking(chapter)

        # Verify fact-checking was performed
        assert chapter.fact_checked is True
        assert chapter.stage_10_fact_check is not None

        # Verify fact-check results structure
        fact_check = chapter.stage_10_fact_check
        assert "overall_accuracy" in fact_check
        assert "total_claims" in fact_check
        assert "verified_claims" in fact_check
        assert "unverified_claims" in fact_check
        assert "critical_issues" in fact_check
        assert "passed" in fact_check
        assert "ai_cost_usd" in fact_check

        # Verify accuracy metrics
        assert 0 <= fact_check["overall_accuracy"] <= 1
        assert fact_check["total_claims"] >= 0
        assert fact_check["verified_claims"] <= fact_check["total_claims"]

        # Verify pass/fail logic was applied
        assert isinstance(fact_check["passed"], bool)
        assert fact_check["passed"] == chapter.fact_check_passed

        # Verify section results
        assert "section_results" in fact_check
        assert len(fact_check["section_results"]) == 2

    @pytest.mark.asyncio
    async def test_stage_10_without_sources(
        self,
        chapter_orchestrator,
        db_session,
        test_user
    ):
        """Test Stage 10 behavior when no sources available"""
        chapter = Chapter(
            title="Test Chapter",
            author_id=test_user.id,
            sections=[{"title": "Test", "content": "Test content"}]
        )
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        # Run Stage 10 (should handle gracefully)
        await chapter_orchestrator._stage_10_fact_checking(chapter)

        # Should be marked as checked but failed
        assert chapter.fact_checked is True
        assert chapter.fact_check_passed is False
        assert chapter.stage_10_fact_check["status"] == "no_sources"


# ============================================================================
# END-TO-END TESTS
# ============================================================================

class TestEndToEndChapterGeneration:
    """Test complete chapter generation with all enhancements"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_minimal_chapter_generation(
        self,
        chapter_orchestrator,
        db_session,
        test_user
    ):
        """Test chapter generation for stages 1-2 with structured outputs"""
        topic = "Ventriculostomy procedure"

        # Create initial chapter
        chapter = Chapter(
            title=topic,
            author_id=test_user.id,
            generation_status="stage_1_input"
        )
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        # Run Stage 1
        await chapter_orchestrator._stage_1_input_validation(chapter, topic)

        # Verify Stage 1 completed with structured outputs
        assert chapter.stage_1_input is not None
        assert chapter.stage_1_input["schema_validated"] is True
        analysis = chapter.stage_1_input["analysis"]
        assert validate_schema_response(analysis, "chapter_analysis") is True

        # Run Stage 2
        await chapter_orchestrator._stage_2_context_building(chapter, topic)

        # Verify Stage 2 completed with structured outputs
        assert chapter.stage_2_context is not None
        assert chapter.stage_2_context["schema_validated"] is True
        context = chapter.stage_2_context["context"]
        assert validate_schema_response(context, "research_context") is True

        # Verify cost tracking
        total_cost = (
            chapter.stage_1_input.get("ai_cost_usd", 0) +
            chapter.stage_2_context.get("ai_cost_usd", 0)
        )
        assert total_cost > 0

        print(f"\n✅ Stages 1-2 completed successfully")
        print(f"   Total cost: ${total_cost:.6f}")
        print(f"   Chapter type: {chapter.chapter_type}")
        print(f"   Keywords: {len(analysis['keywords'])}")
        print(f"   Research gaps: {len(context['research_gaps'])}")


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformanceAndCosts:
    """Test performance and cost tracking"""

    @pytest.mark.asyncio
    async def test_cost_tracking_accuracy(
        self,
        chapter_orchestrator,
        db_session,
        test_user
    ):
        """Verify cost tracking is accurate across stages"""
        topic = "Test topic for cost tracking"

        chapter = Chapter(
            title=topic,
            author_id=test_user.id
        )
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)

        # Run Stage 1
        await chapter_orchestrator._stage_1_input_validation(chapter, topic)
        stage1_cost = chapter.stage_1_input.get("ai_cost_usd", 0)

        # Run Stage 2
        await chapter_orchestrator._stage_2_context_building(chapter, topic)
        stage2_cost = chapter.stage_2_context.get("ai_cost_usd", 0)

        # Verify costs are reasonable
        assert 0.001 <= stage1_cost <= 0.05  # Should be ~$0.01-0.03
        assert 0.001 <= stage2_cost <= 0.10  # Should be ~$0.02-0.06

        total_cost = stage1_cost + stage2_cost
        print(f"\n💰 Cost breakdown:")
        print(f"   Stage 1 (Input Validation): ${stage1_cost:.6f}")
        print(f"   Stage 2 (Context Building): ${stage2_cost:.6f}")
        print(f"   Total: ${total_cost:.6f}")

    @pytest.mark.asyncio
    async def test_structured_outputs_performance(self, db_session, test_user):
        """Test that structured outputs don't significantly impact performance"""
        from backend.services.ai_provider_service import AIProviderService, AITask
        from backend.schemas.ai_schemas import CHAPTER_ANALYSIS_SCHEMA

        service = AIProviderService()

        # Measure structured output time
        start = datetime.utcnow()
        response = await service.generate_text_with_schema(
            prompt="Analyze: Test neurosurgery topic",
            schema=CHAPTER_ANALYSIS_SCHEMA,
            task=AITask.METADATA_EXTRACTION,
            temperature=0.3
        )
        duration = (datetime.utcnow() - start).total_seconds()

        print(f"\n⚡ Performance:")
        print(f"   Structured output duration: {duration:.2f}s")
        print(f"   Cost: ${response['cost_usd']:.6f}")

        # Should complete in reasonable time
        assert duration < 30  # Should be well under 30 seconds


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])
