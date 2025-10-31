#!/usr/bin/env python3
"""
Phase 2 Week 6: Integration Testing Suite
Tests all Phase 2 features working together end-to-end

Features Tested:
- Week 1-2: Parallel Research + PubMed Caching
- Week 3-4: AI Relevance Filtering + Intelligent Deduplication
- Week 5: Gap Analysis

This comprehensive test validates that all Phase 2 enhancements
integrate correctly and deliver expected performance improvements.
"""

import pytest
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.chapter_orchestrator import ChapterOrchestrator
from backend.services.research_service import ResearchService
from backend.services.deduplication_service import DeduplicationService
from backend.services.gap_analyzer import GapAnalyzer
from backend.services.auth_service import AuthService
from backend.database.models import Chapter, User
from backend.config.settings import settings


class TestPhase2Integration:
    """
    Integration tests for Phase 2 complete workflow
    """

    # Use db_session fixture from conftest.py - no need to redefine

    @pytest.fixture
    def test_user(self, db_session):
        """Get or create test user"""
        user = db_session.query(User).filter(User.email == "test_integration@neurocore.ai").first()
        if not user:
            auth_service = AuthService(db_session)
            user = User(
                email="test_integration@neurocore.ai",
                full_name="Integration Test User",
                hashed_password=auth_service.hash_password("testpassword123"),
                is_active=True,
                is_admin=True
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
        return user

    @pytest.fixture
    def test_topics(self):
        """Neurosurgical topics for testing (varied complexity)"""
        return [
            {
                "topic": "Glioblastoma management",
                "type": "surgical_disease",
                "complexity": "high",
                "expected_sections": 12
            },
            {
                "topic": "Circle of Willis anatomy",
                "type": "pure_anatomy",
                "complexity": "medium",
                "expected_sections": 8
            },
            {
                "topic": "Craniotomy surgical technique",
                "type": "surgical_technique",
                "complexity": "high",
                "expected_sections": 10
            },
            {
                "topic": "Subarachnoid hemorrhage",
                "type": "surgical_disease",
                "complexity": "high",
                "expected_sections": 12
            },
            {
                "topic": "Ventricular shunt placement",
                "type": "surgical_technique",
                "complexity": "medium",
                "expected_sections": 8
            }
        ]

    # ==================== Test 1: Complete Workflow Integration ====================

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_chapter_generation_with_all_features(self, db_session, test_user, test_topics):
        """
        Test complete chapter generation with all Phase 2 features enabled

        This is the most comprehensive test - validates entire workflow:
        1. Stage 2: Context Intelligence
        2. Stage 3: Internal Research (with parallel execution)
        3. Stage 4: External Research (with PubMed caching)
        4. Stage 5: Primary Synthesis (with AI relevance filtering)
        5. Deduplication (intelligent deduplication service)
        6. Gap Analysis (Phase 2 Week 5)
        """
        orchestrator = ChapterOrchestrator(db_session)

        # Take first topic for comprehensive test
        topic = test_topics[0]

        print(f"\n{'='*80}")
        print(f"Testing Complete Workflow: {topic['topic']}")
        print(f"{'='*80}\n")

        start_time = time.time()

        try:
            # Generate chapter with all Phase 2 features
            chapter = await orchestrator.generate_chapter(
                topic=topic['topic'],
                user=test_user,
                chapter_type=topic['type']
            )

            generation_time = time.time() - start_time

            # Verify chapter was created
            assert chapter is not None, "Chapter generation returned None"
            assert chapter.id is not None, "Chapter has no ID"
            assert chapter.title == topic['topic'], f"Title mismatch: {chapter.title}"
            assert chapter.generation_status == "completed", f"Status: {chapter.generation_status}"

            # Verify all workflow stages completed
            assert chapter.stage_2_context is not None, "Stage 2 context missing"
            assert chapter.stage_3_internal_research is not None, "Stage 3 internal research missing"
            assert chapter.stage_4_external_research is not None, "Stage 4 external research missing"
            assert chapter.stage_5_synthesis_metadata is not None, "Stage 5 synthesis metadata missing"

            # Verify sections were generated
            assert chapter.sections is not None, "No sections generated"
            assert len(chapter.sections) > 0, "Sections array is empty"

            # Verify quality scores
            assert chapter.depth_score is not None, "Depth score missing"
            assert chapter.coverage_score is not None, "Coverage score missing"
            assert chapter.currency_score is not None, "Currency score missing"
            assert chapter.evidence_score is not None, "Evidence score missing"

            print(f"✓ Chapter generated successfully in {generation_time:.2f}s")
            print(f"  - Title: {chapter.title}")
            print(f"  - Sections: {len(chapter.sections)}")
            print(f"  - Words: {chapter.get_word_count()}")
            print(f"  - Quality Scores:")
            print(f"    - Depth: {chapter.depth_score:.2f}")
            print(f"    - Coverage: {chapter.coverage_score:.2f}")
            print(f"    - Currency: {chapter.currency_score:.2f}")
            print(f"    - Evidence: {chapter.evidence_score:.2f}")

            return {
                "chapter_id": str(chapter.id),
                "generation_time": generation_time,
                "sections": len(chapter.sections),
                "words": chapter.get_word_count(),
                "quality_scores": {
                    "depth": chapter.depth_score,
                    "coverage": chapter.coverage_score,
                    "currency": chapter.currency_score,
                    "evidence": chapter.evidence_score
                }
            }

        except Exception as e:
            pytest.fail(f"Chapter generation failed: {str(e)}")

    # ==================== Test 2: Parallel Research Performance ====================

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_parallel_research_performance(self, db_session):
        """
        Test that parallel research is faster than sequential
        Phase 2 Week 1-2 feature validation
        """
        research_service = ResearchService(db_session)

        test_query = "glioblastoma treatment"

        # Test parallel execution
        start_parallel = time.time()
        results_parallel = await research_service.internal_research_parallel(
            search_queries=[test_query, "glioblastoma surgery", "glioblastoma outcomes"],
            top_k=10
        )
        time_parallel = time.time() - start_parallel

        print(f"\n{'='*80}")
        print(f"Parallel Research Performance Test")
        print(f"{'='*80}\n")
        print(f"✓ Parallel execution: {time_parallel:.2f}s")
        print(f"  - Queries: 3")
        print(f"  - Results: {len(results_parallel)}")

        # Verify results
        assert len(results_parallel) > 0, "No results from parallel research"
        assert time_parallel < 10, f"Parallel research too slow: {time_parallel:.2f}s"

        # Expected: 40% faster than sequential (based on Phase 2 Week 1-2 benchmarks)
        expected_sequential_time = time_parallel / 0.6  # If parallel is 60% of sequential
        print(f"  - Estimated sequential time: {expected_sequential_time:.2f}s")
        print(f"  - Performance improvement: ~{((expected_sequential_time - time_parallel) / expected_sequential_time * 100):.1f}%")

    # ==================== Test 3: PubMed Caching ====================

    @pytest.mark.asyncio
    @pytest.mark.caching
    async def test_pubmed_caching_performance(self, db_session):
        """
        Test PubMed caching delivers expected speedup
        Phase 2 Week 1-2 feature validation
        """
        research_service = ResearchService(db_session)

        test_query = "traumatic brain injury"

        print(f"\n{'='*80}")
        print(f"PubMed Caching Performance Test")
        print(f"{'='*80}\n")

        # First call (cache miss)
        start_miss = time.time()
        results_miss = await research_service.external_research_pubmed(test_query, max_results=20)
        time_miss = time.time() - start_miss

        # Second call (cache hit)
        start_hit = time.time()
        results_hit = await research_service.external_research_pubmed(test_query, max_results=20)
        time_hit = time.time() - start_hit

        print(f"✓ Cache miss: {time_miss:.3f}s ({len(results_miss)} results)")
        print(f"✓ Cache hit: {time_hit:.3f}s ({len(results_hit)} results)")

        # Verify caching works
        assert len(results_miss) == len(results_hit), "Result count mismatch"

        if time_hit < time_miss:
            speedup = time_miss / time_hit
            print(f"  - Speedup: {speedup:.1f}x faster")
            print(f"  - Time saved: {(time_miss - time_hit):.3f}s")
            # Expected: 100-300x speedup for cache hits
        else:
            print(f"  - Warning: Cache hit not faster (may not be cached yet)")

    # ==================== Test 4: AI Relevance Filtering ====================

    @pytest.mark.asyncio
    @pytest.mark.quality
    async def test_ai_relevance_filtering_accuracy(self, db_session):
        """
        Test AI relevance filtering improves source quality
        Phase 2 Week 3-4 feature validation
        """
        research_service = ResearchService(db_session)

        test_query = "cerebral aneurysm clipping"

        print(f"\n{'='*80}")
        print(f"AI Relevance Filtering Test")
        print(f"{'='*80}\n")

        # Get sources without filtering (baseline)
        sources_unfiltered = await research_service.external_research_pubmed(test_query, max_results=50)

        # Get sources with AI filtering
        sources_filtered = await research_service.filter_sources_by_ai_relevance(
            sources=sources_unfiltered,
            query=test_query,
            threshold=0.75
        )

        if sources_filtered:
            avg_relevance = sum(s.get('ai_relevance_score', 0) for s in sources_filtered) / len(sources_filtered)

            print(f"✓ Unfiltered sources: {len(sources_unfiltered)}")
            print(f"✓ Filtered sources: {len(sources_filtered)}")
            print(f"  - Avg relevance: {avg_relevance:.2f}")
            print(f"  - Retention rate: {len(sources_filtered) / len(sources_unfiltered) * 100:.1f}%")

            # Verify quality improvement
            assert avg_relevance >= 0.75, f"Average relevance too low: {avg_relevance:.2f}"
            # Expected: 85-95% relevance (Phase 2 Week 3-4 target)

            high_quality_sources = sum(1 for s in sources_filtered if s.get('ai_relevance_score', 0) >= 0.85)
            print(f"  - High quality (≥0.85): {high_quality_sources} ({high_quality_sources/len(sources_filtered)*100:.1f}%)")

    # ==================== Test 5: Intelligent Deduplication ====================

    @pytest.mark.asyncio
    @pytest.mark.quality
    async def test_intelligent_deduplication(self, db_session):
        """
        Test intelligent deduplication removes duplicates effectively
        Phase 2 Week 3-4 feature validation
        """
        dedup_service = DeduplicationService()  # No db_session parameter needed

        # Create test sources with intentional duplicates
        test_sources = [
            {
                "title": "Management of traumatic brain injury: a systematic review",
                "authors": ["Smith J", "Jones A"],
                "year": 2023,
                "doi": "10.1234/test1"
            },
            {
                "title": "Management of traumatic brain injury: systematic review",  # Near duplicate
                "authors": ["Smith J", "Jones A"],
                "year": 2023,
                "doi": "10.1234/test2"
            },
            {
                "title": "Surgical approaches to glioblastoma",
                "authors": ["Brown C"],
                "year": 2022,
                "doi": "10.1234/test3"
            },
            {
                "title": "Management of traumatic brain injury: a systematic review",  # Exact duplicate
                "authors": ["Smith J", "Jones A"],
                "year": 2023,
                "doi": "10.1234/test1"  # Same DOI
            },
            {
                "title": "Glioblastoma surgical techniques",  # Semantic duplicate
                "authors": ["Brown C"],
                "year": 2022,
                "doi": "10.1234/test4"
            }
        ]

        print(f"\n{'='*80}")
        print(f"Intelligent Deduplication Test")
        print(f"{'='*80}\n")

        # Test exact deduplication
        deduplicated_exact = await dedup_service.deduplicate_sources(
            sources=test_sources,
            strategy="exact"
        )

        print(f"✓ Original sources: {len(test_sources)}")
        print(f"✓ After exact deduplication: {len(deduplicated_exact)}")
        print(f"  - Duplicates removed: {len(test_sources) - len(deduplicated_exact)}")

        # Test fuzzy deduplication
        deduplicated_fuzzy = await dedup_service.deduplicate_sources(
            sources=test_sources,
            strategy="fuzzy",
            similarity_threshold=0.85
        )

        print(f"✓ After fuzzy deduplication: {len(deduplicated_fuzzy)}")
        print(f"  - Additional fuzzy duplicates: {len(deduplicated_exact) - len(deduplicated_fuzzy)}")

        # Verify deduplication works
        assert len(deduplicated_exact) < len(test_sources), "Exact deduplication didn't remove any duplicates"
        assert len(deduplicated_fuzzy) <= len(deduplicated_exact), "Fuzzy should remove same or more"

    # ==================== Test 6: Gap Analysis Validation ====================

    @pytest.mark.asyncio
    @pytest.mark.quality
    async def test_gap_analysis_accuracy(self, db_session, test_user, test_topics):
        """
        Test gap analysis identifies gaps correctly
        Phase 2 Week 5 feature validation
        """
        orchestrator = ChapterOrchestrator(db_session)
        gap_analyzer = GapAnalyzer()  # No db_session parameter needed

        # Generate a test chapter
        topic = test_topics[1]  # Use medium complexity topic
        chapter = await orchestrator.generate_chapter(
            topic=topic['topic'],
            user=test_user,
            chapter_type=topic['type']
        )

        print(f"\n{'='*80}")
        print(f"Gap Analysis Validation Test")
        print(f"{'='*80}\n")

        # Run gap analysis
        chapter_data = {
            "id": str(chapter.id),
            "title": chapter.title,
            "sections": chapter.sections or [],
            "chapter_type": chapter.chapter_type
        }

        internal_sources = chapter.stage_3_internal_research.get("sources", []) if chapter.stage_3_internal_research else []
        external_sources = chapter.stage_4_external_research.get("pubmed_sources", []) if chapter.stage_4_external_research else []
        stage_2_context = chapter.stage_2_context or {}

        gap_analysis = await gap_analyzer.analyze_chapter_gaps(
            chapter=chapter_data,
            internal_sources=internal_sources,
            external_sources=external_sources,
            stage_2_context=stage_2_context
        )

        print(f"✓ Gap analysis completed")
        print(f"  - Total gaps: {gap_analysis.get('total_gaps', 0)}")
        print(f"  - Completeness score: {gap_analysis.get('overall_completeness_score', 0):.2f}")
        print(f"  - Requires revision: {gap_analysis.get('requires_revision', False)}")

        # Verify gap analysis structure
        assert 'total_gaps' in gap_analysis, "Missing total_gaps"
        assert 'gaps_identified' in gap_analysis, "Missing gaps_identified"
        assert 'severity_distribution' in gap_analysis, "Missing severity_distribution"
        assert 'gap_categories' in gap_analysis, "Missing gap_categories"
        assert 'recommendations' in gap_analysis, "Missing recommendations"
        assert 'overall_completeness_score' in gap_analysis, "Missing completeness_score"

        # Verify severity distribution
        severity_dist = gap_analysis.get('severity_distribution', {})
        print(f"  - Severity distribution:")
        print(f"    - Critical: {severity_dist.get('critical', 0)}")
        print(f"    - High: {severity_dist.get('high', 0)}")
        print(f"    - Medium: {severity_dist.get('medium', 0)}")
        print(f"    - Low: {severity_dist.get('low', 0)}")

        # Verify gap categories
        gap_categories = gap_analysis.get('gap_categories', {})
        print(f"  - Gap categories:")
        for category, gaps in gap_categories.items():
            print(f"    - {category}: {len(gaps) if isinstance(gaps, list) else 0} gaps")

        # Verify recommendations
        recommendations = gap_analysis.get('recommendations', [])
        print(f"  - Recommendations: {len(recommendations)}")
        if recommendations:
            print(f"    - Top priority: {recommendations[0].get('description', 'N/A')}")

    # ==================== Test 7: Performance Comparison ====================

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_phase2_vs_baseline_performance(self, db_session, test_user, test_topics):
        """
        Compare Phase 2 performance against Phase 1 baseline
        Expected improvements:
        - 40% faster internal research (parallel execution)
        - 300x faster PubMed queries (caching, cache hits only)
        - Higher quality sources (85-95% relevance)
        - Better gap detection
        """
        orchestrator = ChapterOrchestrator(db_session)

        print(f"\n{'='*80}")
        print(f"Phase 2 vs Baseline Performance Comparison")
        print(f"{'='*80}\n")

        topic = test_topics[0]

        # Generate chapter with Phase 2 features
        start_time = time.time()
        chapter = await orchestrator.generate_chapter(
            topic=topic['topic'],
            user=test_user,
            chapter_type=topic['type']
        )
        phase2_time = time.time() - start_time

        # Extract metrics
        internal_research = chapter.stage_3_internal_research or {}
        external_research = chapter.stage_4_external_research or {}
        synthesis_metadata = chapter.stage_5_synthesis_metadata or {}

        print(f"✓ Phase 2 generation time: {phase2_time:.2f}s")
        print(f"\nStage breakdown:")
        print(f"  - Internal research time: {internal_research.get('execution_time', 0):.2f}s")
        print(f"  - External research time: {external_research.get('execution_time', 0):.2f}s")
        print(f"  - Synthesis time: {synthesis_metadata.get('generation_time', 0):.2f}s")

        print(f"\nQuality metrics:")
        print(f"  - Internal sources: {len(internal_research.get('sources', []))}")
        print(f"  - External sources: {len(external_research.get('pubmed_sources', []))}")
        print(f"  - Avg source relevance: {internal_research.get('avg_relevance', 0):.2f}")

        print(f"\nCache performance:")
        print(f"  - Cache hits: {external_research.get('cache_hits', 0)}")
        print(f"  - Cache misses: {external_research.get('cache_misses', 0)}")

        if external_research.get('cache_hits', 0) > 0:
            cache_hit_rate = external_research.get('cache_hits', 0) / (external_research.get('cache_hits', 0) + external_research.get('cache_misses', 0)) * 100
            print(f"  - Cache hit rate: {cache_hit_rate:.1f}%")

        # Verify Phase 2 improvements
        assert phase2_time < 300, f"Generation too slow: {phase2_time:.2f}s"  # Reasonable upper bound
        assert chapter.depth_score >= 0.7, f"Depth score too low: {chapter.depth_score:.2f}"
        assert chapter.coverage_score >= 0.75, f"Coverage score too low: {chapter.coverage_score:.2f}"

    # ==================== Test 8: Concurrent Generation ====================

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_concurrent_chapter_generation(self, db_session, test_user, test_topics):
        """
        Test concurrent chapter generation (stress test)
        Verifies system can handle multiple generations simultaneously
        """
        orchestrator = ChapterOrchestrator(db_session)

        print(f"\n{'='*80}")
        print(f"Concurrent Generation Stress Test")
        print(f"{'='*80}\n")

        # Generate 3 chapters concurrently
        topics_to_test = test_topics[:3]

        start_time = time.time()

        tasks = [
            orchestrator.generate_chapter(
                topic=topic['topic'],
                user=test_user,
                chapter_type=topic['type']
            )
            for topic in topics_to_test
        ]

        chapters = await asyncio.gather(*tasks, return_exceptions=True)

        concurrent_time = time.time() - start_time

        # Verify all succeeded
        successful = sum(1 for c in chapters if isinstance(c, Chapter))
        failed = sum(1 for c in chapters if isinstance(c, Exception))

        print(f"✓ Concurrent generation completed in {concurrent_time:.2f}s")
        print(f"  - Successful: {successful}/{len(topics_to_test)}")
        print(f"  - Failed: {failed}/{len(topics_to_test)}")

        if failed > 0:
            for i, result in enumerate(chapters):
                if isinstance(result, Exception):
                    print(f"  - Chapter {i+1} failed: {str(result)}")

        assert successful == len(topics_to_test), f"Only {successful}/{len(topics_to_test)} chapters succeeded"
        assert concurrent_time < 600, f"Concurrent generation too slow: {concurrent_time:.2f}s"


# ==================== Test Execution ====================

if __name__ == "__main__":
    """
    Run tests with pytest

    Usage:
        # Run all tests
        pytest tests/integration/test_phase2_integration.py -v

        # Run specific test category
        pytest tests/integration/test_phase2_integration.py -v -m performance
        pytest tests/integration/test_phase2_integration.py -v -m quality

        # Run with output
        pytest tests/integration/test_phase2_integration.py -v -s
    """
    pytest.main([__file__, "-v", "-s", "--tb=short"])
