"""
Comprehensive Unit Tests for OpenAI Integration
Tests all Phase 1-4 features in isolation

Test Coverage:
- GPT-4o text generation
- GPT-4o structured outputs
- GPT-4o vision analysis
- text-embedding-3-large embeddings
- Fact-checking service
- Batch processing service
- Cost calculations
- Schema validation
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Add backend to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from backend.services.ai_provider_service import AIProviderService, AITask, AIProvider
from backend.services.fact_checking_service import FactCheckingService
from backend.services.batch_provider_service import BatchProviderService
from backend.schemas.ai_schemas import (
    CHAPTER_ANALYSIS_SCHEMA,
    CONTEXT_BUILDING_SCHEMA,
    FACT_CHECK_SCHEMA,
    get_schema_by_name,
    validate_schema_response
)
from backend.config import settings


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def ai_service():
    """Create AI provider service instance"""
    return AIProviderService()


@pytest.fixture
def fact_check_service():
    """Create fact-checking service instance"""
    return FactCheckingService()


@pytest.fixture
def batch_service():
    """Create batch processing service instance"""
    return BatchProviderService(max_concurrent=3)


@pytest.fixture
def sample_sources():
    """Sample research sources for testing"""
    return [
        {
            "title": "Management of Glioblastoma: Current Approaches",
            "authors": ["Smith J", "Johnson M", "Williams R"],
            "year": 2024,
            "pmid": "12345678",
            "journal": "Journal of Neurosurgery",
            "abstract": "Glioblastoma is the most aggressive primary brain tumor..."
        },
        {
            "title": "Surgical Techniques for Craniotomy",
            "authors": ["Brown A", "Davis K"],
            "year": 2023,
            "pmid": "87654321",
            "journal": "Neurosurgical Techniques",
            "abstract": "Modern craniotomy techniques involve careful planning..."
        }
    ]


# ============================================================================
# PHASE 1 TESTS: Core Model Updates
# ============================================================================

class TestPhase1CoreUpdates:
    """Test Phase 1: Core model updates and pricing"""

    def test_configuration_values(self):
        """Test that all configuration values are correct"""
        # Chat model
        assert settings.OPENAI_CHAT_MODEL == "gpt-4o"

        # Embedding model
        assert settings.OPENAI_EMBEDDING_MODEL == "text-embedding-3-large"
        assert settings.OPENAI_EMBEDDING_DIMENSIONS == 3072

        # Pricing
        assert settings.OPENAI_GPT4O_INPUT_COST_PER_1K == 0.0025
        assert settings.OPENAI_GPT4O_OUTPUT_COST_PER_1K == 0.010
        assert settings.OPENAI_EMBEDDING_3_LARGE_COST_PER_1K == 0.00013

    @pytest.mark.asyncio
    async def test_gpt4o_text_generation(self, ai_service):
        """Test GPT-4o basic text generation"""
        response = await ai_service.generate_text(
            prompt="What is a craniotomy? Answer in one sentence.",
            task=AITask.METADATA_EXTRACTION,
            provider=AIProvider.GPT4,
            max_tokens=100,
            temperature=0.3
        )

        # Verify response structure
        assert "text" in response
        assert "provider" in response
        assert "model" in response
        assert "cost_usd" in response
        assert "tokens_used" in response

        # Verify model
        assert response["model"] == "gpt-4o"
        assert response["provider"] == "gpt4o"

        # Verify cost is reasonable (should be very low)
        assert response["cost_usd"] < 0.01

        # Verify text was generated
        assert len(response["text"]) > 0

    @pytest.mark.asyncio
    async def test_embeddings_3_large(self, ai_service):
        """Test text-embedding-3-large embeddings"""
        response = await ai_service.generate_embedding(
            text="Neurosurgical procedures for brain tumor removal",
            model="text-embedding-3-large"
        )

        # Verify response structure
        assert "embedding" in response
        assert "dimensions" in response
        assert "model" in response
        assert "cost_usd" in response

        # Verify dimensions
        assert response["dimensions"] == 3072
        assert len(response["embedding"]) == 3072

        # Verify model
        assert response["model"] == "text-embedding-3-large"

        # Verify cost calculation
        assert response["cost_usd"] > 0

    @pytest.mark.asyncio
    async def test_cost_calculation_accuracy(self, ai_service):
        """Test that cost calculations are accurate"""
        response = await ai_service.generate_text(
            prompt="Test prompt for cost calculation",
            task=AITask.METADATA_EXTRACTION,
            provider=AIProvider.GPT4,
            max_tokens=50,
            temperature=0.3
        )

        # Manually calculate expected cost
        input_tokens = response["input_tokens"]
        output_tokens = response["output_tokens"]

        expected_cost = (
            (input_tokens / 1000) * settings.OPENAI_GPT4O_INPUT_COST_PER_1K +
            (output_tokens / 1000) * settings.OPENAI_GPT4O_OUTPUT_COST_PER_1K
        )

        # Allow small floating-point differences
        assert abs(response["cost_usd"] - expected_cost) < 0.000001


# ============================================================================
# PHASE 2 TESTS: Structured Outputs
# ============================================================================

class TestPhase2StructuredOutputs:
    """Test Phase 2: Structured outputs with schema validation"""

    def test_schema_definitions(self):
        """Test that all schemas are properly defined"""
        schemas = [
            "chapter_analysis",
            "research_context",
            "fact_check",
            "metadata_extraction",
            "source_relevance",
            "image_analysis"
        ]

        for schema_name in schemas:
            schema = get_schema_by_name(schema_name)
            assert "name" in schema
            assert "strict" in schema
            assert "schema" in schema
            assert schema["strict"] is True

    def test_schema_validation(self):
        """Test schema validation helper"""
        # Valid data
        valid_data = {
            "primary_concepts": ["glioblastoma", "surgery"],
            "chapter_type": "surgical_disease",
            "keywords": ["glioblastoma", "treatment", "surgery"],
            "complexity": "advanced",
            "anatomical_regions": ["frontal lobe", "temporal lobe"],
            "surgical_approaches": ["craniotomy", "biopsy"],
            "estimated_section_count": 50
        }

        assert validate_schema_response(valid_data, "chapter_analysis") is True

        # Invalid data (missing required field)
        invalid_data = {
            "primary_concepts": ["glioblastoma"],
            "keywords": ["glioblastoma"]
            # Missing chapter_type, complexity, estimated_section_count
        }

        with pytest.raises(ValueError):
            validate_schema_response(invalid_data, "chapter_analysis")

    @pytest.mark.asyncio
    async def test_chapter_analysis_schema(self, ai_service):
        """Test CHAPTER_ANALYSIS_SCHEMA structured output"""
        response = await ai_service.generate_text_with_schema(
            prompt="""
            Analyze this neurosurgery topic: "Surgical management of glioblastoma"

            Extract all required metadata including concepts, type, keywords, and complexity.
            """,
            schema=CHAPTER_ANALYSIS_SCHEMA,
            task=AITask.METADATA_EXTRACTION,
            temperature=0.3
        )

        # Verify response structure
        assert "data" in response
        assert "schema_name" in response
        assert response["schema_name"] == "chapter_analysis"

        # Verify data has all required fields
        data = response["data"]
        assert "primary_concepts" in data
        assert "chapter_type" in data
        assert "keywords" in data
        assert "complexity" in data
        assert "estimated_section_count" in data

        # Verify data types and constraints
        assert isinstance(data["primary_concepts"], list)
        assert len(data["primary_concepts"]) >= 1
        assert data["chapter_type"] in ["surgical_disease", "pure_anatomy", "surgical_technique"]
        assert isinstance(data["keywords"], list)
        assert 3 <= len(data["keywords"]) <= 20
        assert data["complexity"] in ["beginner", "intermediate", "advanced", "expert"]
        assert 10 <= data["estimated_section_count"] <= 150

        # Schema validation should pass
        assert validate_schema_response(data, "chapter_analysis") is True

    @pytest.mark.asyncio
    async def test_context_building_schema(self, ai_service):
        """Test CONTEXT_BUILDING_SCHEMA structured output"""
        response = await ai_service.generate_text_with_schema(
            prompt="""
            Build research context for: "Craniotomy for tumor resection"

            Identify research gaps, key references needed, content categories,
            temporal coverage, and confidence assessment.
            """,
            schema=CONTEXT_BUILDING_SCHEMA,
            task=AITask.METADATA_EXTRACTION,
            temperature=0.4
        )

        data = response["data"]

        # Verify all required fields
        assert "research_gaps" in data
        assert "key_references" in data
        assert "content_categories" in data
        assert "confidence_assessment" in data

        # Verify data types
        assert isinstance(data["research_gaps"], list)
        assert isinstance(data["key_references"], list)
        assert isinstance(data["content_categories"], dict)
        assert isinstance(data["confidence_assessment"], dict)

        # Verify nested structures
        if len(data["research_gaps"]) > 0:
            gap = data["research_gaps"][0]
            assert "gap_description" in gap
            assert "severity" in gap
            assert gap["severity"] in ["high", "medium", "low"]

        if len(data["key_references"]) > 0:
            ref = data["key_references"][0]
            assert "title" in ref
            assert "relevance_score" in ref
            assert 0 <= ref["relevance_score"] <= 1

        # Schema validation
        assert validate_schema_response(data, "research_context") is True

    @pytest.mark.asyncio
    async def test_no_json_parsing_errors(self, ai_service):
        """Test that structured outputs never fail JSON parsing"""
        # Run 10 iterations to ensure reliability
        for i in range(10):
            response = await ai_service.generate_text_with_schema(
                prompt=f"Analyze neurosurgery topic {i}: Test topic variation",
                schema=CHAPTER_ANALYSIS_SCHEMA,
                task=AITask.METADATA_EXTRACTION,
                temperature=0.3
            )

            # Should never need try/catch - guaranteed valid
            data = response["data"]

            # Verify it's valid
            assert isinstance(data, dict)
            assert "chapter_type" in data
            assert validate_schema_response(data, "chapter_analysis") is True


# ============================================================================
# PHASE 3 TESTS: Fact-Checking
# ============================================================================

class TestPhase3FactChecking:
    """Test Phase 3: Medical fact-checking service"""

    @pytest.mark.asyncio
    async def test_fact_check_section(self, fact_check_service, sample_sources):
        """Test fact-checking a single section"""
        section_content = """
        Glioblastoma is the most aggressive primary brain tumor in adults.
        Standard treatment includes maximal safe resection followed by
        radiotherapy and temozolomide chemotherapy.
        """

        result = await fact_check_service.fact_check_section(
            section_content=section_content,
            sources=sample_sources,
            chapter_title="Glioblastoma Management",
            section_title="Treatment Overview"
        )

        # Verify result structure
        assert "claims" in result
        assert "overall_accuracy" in result
        assert "unverified_count" in result
        assert "critical_issues" in result

        # Verify claims structure
        assert len(result["claims"]) > 0
        claim = result["claims"][0]
        assert "claim" in claim
        assert "verified" in claim
        assert "confidence" in claim
        assert "category" in claim
        assert "severity_if_wrong" in claim

        # Verify confidence is in range
        assert 0 <= claim["confidence"] <= 1

        # Verify overall accuracy
        assert 0 <= result["overall_accuracy"] <= 1

    @pytest.mark.asyncio
    async def test_fact_check_chapter(self, fact_check_service, sample_sources):
        """Test fact-checking entire chapter"""
        sections = [
            {
                "title": "Introduction",
                "content": "Glioblastoma is a malignant brain tumor."
            },
            {
                "title": "Treatment",
                "content": "Surgery is the primary treatment modality."
            }
        ]

        result = await fact_check_service.fact_check_chapter(
            sections=sections,
            sources=sample_sources,
            chapter_title="Glioblastoma"
        )

        # Verify aggregate results
        assert "chapter_title" in result
        assert "sections_checked" in result
        assert "total_claims" in result
        assert "verified_claims" in result
        assert "overall_accuracy" in result
        assert "section_results" in result

        # Verify counts
        assert result["sections_checked"] == len(sections)
        assert result["total_claims"] >= 0
        assert result["verified_claims"] <= result["total_claims"]

    @pytest.mark.asyncio
    async def test_verify_single_claim(self, fact_check_service, sample_sources):
        """Test verifying a single medical claim"""
        claim = "Glioblastoma is the most common malignant primary brain tumor in adults"

        result = await fact_check_service.verify_single_claim(
            claim=claim,
            sources=sample_sources,
            context="Brain tumor epidemiology"
        )

        # Verify claim verification structure
        assert "claim" in result
        assert "verified" in result
        assert "confidence" in result
        assert "category" in result
        assert isinstance(result["verified"], bool)
        assert 0 <= result["confidence"] <= 1

    def test_verification_summary(self, fact_check_service):
        """Test verification summary generation"""
        fact_check_results = {
            "claims": [
                {
                    "claim": "Test claim 1",
                    "verified": True,
                    "confidence": 0.95,
                    "category": "anatomy",
                    "severity_if_wrong": "low"
                },
                {
                    "claim": "Test claim 2",
                    "verified": False,
                    "confidence": 0.60,
                    "category": "treatment",
                    "severity_if_wrong": "high"
                }
            ],
            "critical_issues": ["Issue 1"],
            "recommendations": ["Recommendation 1"]
        }

        summary = fact_check_service.get_verification_summary(fact_check_results)

        assert "total_claims" in summary
        assert summary["total_claims"] == 2
        assert summary["verified"] == 1
        assert summary["unverified"] == 1
        assert summary["accuracy_percentage"] == 50.0
        assert summary["requires_attention"] is True  # Has high severity unverified


# ============================================================================
# PHASE 4 TESTS: Batch Processing
# ============================================================================

class TestPhase4BatchProcessing:
    """Test Phase 4: Batch processing service"""

    @pytest.mark.asyncio
    async def test_batch_generate_text(self, batch_service):
        """Test batch text generation"""
        prompts = [
            {"prompt": "What is a craniotomy?"},
            {"prompt": "What is glioblastoma?"},
            {"prompt": "What is a ventriculostomy?"}
        ]

        result = await batch_service.batch_generate_text(
            prompts=prompts,
            task=AITask.METADATA_EXTRACTION,
            max_tokens=100,
            temperature=0.3
        )

        # Verify result structure
        assert "status" in result
        assert "results" in result
        assert "errors" in result
        assert "summary" in result

        # Verify summary
        summary = result["summary"]
        assert summary["total_requests"] == 3
        assert summary["successful"] >= 0
        assert summary["failed"] >= 0
        assert summary["successful"] + summary["failed"] == 3
        assert "total_cost_usd" in summary
        assert "duration_seconds" in summary

    @pytest.mark.asyncio
    async def test_batch_structured_outputs(self, batch_service):
        """Test batch structured output generation"""
        prompts = [
            {"prompt": "Analyze: Craniotomy procedure"},
            {"prompt": "Analyze: Glioblastoma treatment"}
        ]

        result = await batch_service.batch_generate_structured(
            prompts=prompts,
            schema_name="chapter_analysis",
            task=AITask.METADATA_EXTRACTION,
            temperature=0.3
        )

        # Verify structure
        assert result["schema_name"] == "chapter_analysis"
        assert "results" in result

        # Verify each result has valid schema data
        for item in result["results"]:
            assert "data" in item
            data = item["data"]
            # Should be valid according to schema
            assert "chapter_type" in data
            assert "keywords" in data

    @pytest.mark.asyncio
    async def test_batch_embeddings(self, batch_service):
        """Test batch embedding generation"""
        texts = [
            "Craniotomy surgical procedure",
            "Glioblastoma tumor treatment",
            "Ventriculostomy drainage"
        ]

        result = await batch_service.batch_generate_embeddings(
            texts=texts,
            model="text-embedding-3-large"
        )

        # Verify structure
        assert result["model"] == "text-embedding-3-large"
        assert "results" in result

        # Verify embeddings
        if result["summary"]["successful"] > 0:
            embedding_result = result["results"][0]
            assert "embedding" in embedding_result
            assert len(embedding_result["embedding"]) == 3072

    @pytest.mark.asyncio
    async def test_progress_tracking(self, batch_service):
        """Test progress callback functionality"""
        prompts = [{"prompt": f"Test {i}"} for i in range(5)]

        progress_updates = []

        def track_progress(completed, total):
            progress_updates.append((completed, total))

        result = await batch_service.batch_generate_text(
            prompts=prompts,
            task=AITask.METADATA_EXTRACTION,
            max_tokens=50,
            progress_callback=track_progress
        )

        # Should have received progress updates
        assert len(progress_updates) > 0
        # Last update should be (5, 5)
        assert progress_updates[-1] == (5, 5)

    def test_optimal_batch_size(self, batch_service):
        """Test optimal batch size calculation"""
        # Small tokens
        size = batch_service.get_optimal_batch_size(estimated_tokens_per_request=100)
        assert size > batch_service.max_concurrent

        # Medium tokens
        size = batch_service.get_optimal_batch_size(estimated_tokens_per_request=1000)
        assert size >= batch_service.max_concurrent

        # Large tokens
        size = batch_service.get_optimal_batch_size(estimated_tokens_per_request=5000)
        assert size == batch_service.max_concurrent


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestEndToEndIntegration:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_full_structured_pipeline(self, ai_service):
        """Test complete structured output pipeline"""
        # Stage 1: Chapter analysis
        stage1_response = await ai_service.generate_text_with_schema(
            prompt="Analyze: Surgical treatment of glioblastoma",
            schema=CHAPTER_ANALYSIS_SCHEMA,
            task=AITask.METADATA_EXTRACTION,
            temperature=0.3
        )

        analysis = stage1_response["data"]
        assert validate_schema_response(analysis, "chapter_analysis")

        # Stage 2: Context building
        stage2_response = await ai_service.generate_text_with_schema(
            prompt=f"""
            Build research context for: Glioblastoma surgery
            Primary concepts: {', '.join(analysis['primary_concepts'])}
            """,
            schema=CONTEXT_BUILDING_SCHEMA,
            task=AITask.METADATA_EXTRACTION,
            temperature=0.4
        )

        context = stage2_response["data"]
        assert validate_schema_response(context, "research_context")

        # Verify cost tracking
        total_cost = stage1_response["cost_usd"] + stage2_response["cost_usd"]
        assert total_cost > 0


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
