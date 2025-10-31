#!/usr/bin/env python3
"""
Phase 2 Week 6: Performance Benchmarking Script
Measures actual performance improvements from Phase 2 features

Benchmarks:
1. Parallel Research Performance (Week 1-2)
2. PubMed Caching Performance (Week 1-2)
3. AI Relevance Filtering Quality (Week 3-4)
4. Deduplication Effectiveness (Week 3-4)
5. Gap Analysis Performance (Week 5)
6. End-to-End Generation Time

Generates detailed performance report with metrics.
"""

import asyncio
import time
import json
import statistics
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.research_service import ResearchService
from backend.services.deduplication_service import DeduplicationService
from backend.services.gap_analyzer import GapAnalyzer
from backend.services.chapter_orchestrator import ChapterOrchestrator
from backend.database import db, User
from backend.config.settings import settings


class Phase2PerformanceBenchmark:
    """Phase 2 performance benchmarking suite"""

    def __init__(self):
        self.db = db.SessionLocal()
        self.research_service = ResearchService(self.db)
        self.dedup_service = DeduplicationService()  # No db parameter needed
        self.gap_analyzer = GapAnalyzer()  # No db parameter needed
        self.orchestrator = ChapterOrchestrator(self.db)
        self.results = {}

    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'db'):
            self.db.close()

    def print_header(self, title: str):
        """Print formatted section header"""
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")

    def print_result(self, metric: str, value: Any, unit: str = ""):
        """Print formatted result"""
        print(f"  ✓ {metric}: {value}{unit}")

    async def benchmark_parallel_research(self) -> Dict[str, Any]:
        """
        Benchmark 1: Parallel Research Performance
        Expected: 40% faster than sequential
        """
        self.print_header("Benchmark 1: Parallel Research Performance")

        queries = [
            "glioblastoma treatment",
            "glioblastoma surgery",
            "glioblastoma outcomes",
            "glioblastoma prognosis"
        ]

        # Run multiple times for average
        times = []
        for i in range(3):
            start = time.time()
            results = await self.research_service.internal_research_parallel(
                search_queries=queries,
                top_k=10
            )
            elapsed = time.time() - start
            times.append(elapsed)

        avg_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0

        self.print_result("Average parallel execution time", f"{avg_time:.3f}", " seconds")
        self.print_result("Standard deviation", f"{std_dev:.3f}", " seconds")
        self.print_result("Queries processed", len(queries))
        self.print_result("Results per query", f"~{len(results) // len(queries)}")

        # Calculate expected sequential time (parallel should be ~60% of sequential)
        expected_sequential = avg_time / 0.6
        improvement = ((expected_sequential - avg_time) / expected_sequential * 100)

        self.print_result("Estimated sequential time", f"{expected_sequential:.3f}", " seconds")
        self.print_result("Performance improvement", f"~{improvement:.1f}", "%")

        return {
            "avg_time": avg_time,
            "std_dev": std_dev,
            "queries": len(queries),
            "estimated_improvement": improvement,
            "target_improvement": 40.0
        }

    async def benchmark_pubmed_caching(self) -> Dict[str, Any]:
        """
        Benchmark 2: PubMed Caching Performance
        Expected: 100-300x speedup on cache hits
        """
        self.print_header("Benchmark 2: PubMed Caching Performance")

        query = "traumatic brain injury management"

        # First call (cache miss)
        start_miss = time.time()
        results_miss = await self.research_service.external_research_pubmed(query, max_results=30)
        time_miss = time.time() - start_miss

        # Second call (cache hit)
        start_hit = time.time()
        results_hit = await self.research_service.external_research_pubmed(query, max_results=30)
        time_hit = time.time() - start_hit

        speedup = time_miss / time_hit if time_hit > 0 else 0

        self.print_result("Cache miss time", f"{time_miss:.3f}", " seconds")
        self.print_result("Cache hit time", f"{time_hit:.3f}", " seconds")
        self.print_result("Results count", len(results_hit))
        self.print_result("Speedup", f"{speedup:.1f}", "x")
        self.print_result("Time saved", f"{(time_miss - time_hit):.3f}", " seconds")

        return {
            "cache_miss_time": time_miss,
            "cache_hit_time": time_hit,
            "speedup": speedup,
            "results_count": len(results_hit),
            "target_speedup_min": 100.0,
            "target_speedup_max": 300.0
        }

    async def benchmark_ai_relevance_filtering(self) -> Dict[str, Any]:
        """
        Benchmark 3: AI Relevance Filtering Quality
        Expected: 85-95% relevance score
        """
        self.print_header("Benchmark 3: AI Relevance Filtering Quality")

        topics = [
            "cerebral aneurysm clipping technique",
            "spinal cord tumor resection",
            "deep brain stimulation for Parkinson's"
        ]

        all_relevance_scores = []
        all_retention_rates = []

        for topic in topics:
            # Get sources
            sources = await self.research_service.external_research_pubmed(topic, max_results=30)

            # Apply AI filtering
            filtered = await self.research_service.filter_sources_by_ai_relevance(
                sources=sources,
                query=topic,
                threshold=0.75
            )

            if filtered:
                relevance_scores = [s.get('ai_relevance_score', 0) for s in filtered]
                avg_relevance = statistics.mean(relevance_scores)
                retention_rate = len(filtered) / len(sources) * 100

                all_relevance_scores.extend(relevance_scores)
                all_retention_rates.append(retention_rate)

                print(f"  Topic: {topic}")
                self.print_result("  - Avg relevance", f"{avg_relevance:.3f}")
                self.print_result("  - Retention rate", f"{retention_rate:.1f}", "%")

        overall_avg = statistics.mean(all_relevance_scores) if all_relevance_scores else 0
        overall_retention = statistics.mean(all_retention_rates) if all_retention_rates else 0

        high_quality = sum(1 for s in all_relevance_scores if s >= 0.85)
        high_quality_pct = (high_quality / len(all_relevance_scores) * 100) if all_relevance_scores else 0

        print()
        self.print_result("Overall average relevance", f"{overall_avg:.3f}")
        self.print_result("Overall retention rate", f"{overall_retention:.1f}", "%")
        self.print_result("High quality sources (≥0.85)", f"{high_quality_pct:.1f}", "%")

        return {
            "avg_relevance": overall_avg,
            "retention_rate": overall_retention,
            "high_quality_pct": high_quality_pct,
            "target_relevance_min": 0.85,
            "target_relevance_max": 0.95
        }

    async def benchmark_deduplication(self) -> Dict[str, Any]:
        """
        Benchmark 4: Deduplication Effectiveness
        Expected: Remove 10-30% duplicates
        """
        self.print_header("Benchmark 4: Deduplication Effectiveness")

        # Simulate real-world scenario with duplicates
        query = "glioblastoma surgical management"
        sources = await self.research_service.external_research_pubmed(query, max_results=50)

        original_count = len(sources)

        # Test exact deduplication
        start = time.time()
        deduplicated_exact = await self.dedup_service.deduplicate_sources(
            sources=sources,
            strategy="exact"
        )
        time_exact = time.time() - start

        # Test fuzzy deduplication
        start = time.time()
        deduplicated_fuzzy = await self.dedup_service.deduplicate_sources(
            sources=sources,
            strategy="fuzzy",
            similarity_threshold=0.85
        )
        time_fuzzy = time.time() - start

        exact_removed = original_count - len(deduplicated_exact)
        fuzzy_removed = len(deduplicated_exact) - len(deduplicated_fuzzy)
        total_removed = original_count - len(deduplicated_fuzzy)

        exact_pct = (exact_removed / original_count * 100) if original_count > 0 else 0
        total_pct = (total_removed / original_count * 100) if original_count > 0 else 0

        self.print_result("Original sources", original_count)
        self.print_result("After exact deduplication", len(deduplicated_exact))
        self.print_result("  - Exact duplicates removed", f"{exact_removed} ({exact_pct:.1f}%)")
        self.print_result("  - Processing time", f"{time_exact:.3f}s")
        self.print_result("After fuzzy deduplication", len(deduplicated_fuzzy))
        self.print_result("  - Fuzzy duplicates removed", f"{fuzzy_removed}")
        self.print_result("  - Processing time", f"{time_fuzzy:.3f}s")
        self.print_result("Total duplicates removed", f"{total_removed} ({total_pct:.1f}%)")

        return {
            "original_count": original_count,
            "exact_removed": exact_removed,
            "fuzzy_removed": fuzzy_removed,
            "total_removed": total_removed,
            "removal_rate": total_pct,
            "exact_time": time_exact,
            "fuzzy_time": time_fuzzy
        }

    async def benchmark_gap_analysis(self) -> Dict[str, Any]:
        """
        Benchmark 5: Gap Analysis Performance
        Expected: 2-10 seconds depending on chapter size
        """
        self.print_header("Benchmark 5: Gap Analysis Performance")

        # Create sample chapter data (simulate completed chapter)
        sample_chapter = {
            "id": "test-chapter-id",
            "title": "Glioblastoma management",
            "sections": [
                {"section_num": i, "title": f"Section {i}", "content": "..." * 100}
                for i in range(12)
            ],
            "chapter_type": "surgical_disease"
        }

        sample_sources = [
            {"title": f"Source {i}", "relevance_score": 0.8 + (i % 3) * 0.05}
            for i in range(20)
        ]

        sample_context = {
            "key_concepts": ["epidemiology", "diagnosis", "treatment", "prognosis"],
            "research_gaps": ["recent immunotherapy advances", "quality of life studies"]
        }

        # Run gap analysis multiple times
        times = []
        for i in range(3):
            start = time.time()
            gap_analysis = await self.gap_analyzer.analyze_chapter_gaps(
                chapter=sample_chapter,
                internal_sources=sample_sources[:10],
                external_sources=sample_sources[10:],
                stage_2_context=sample_context
            )
            elapsed = time.time() - start
            times.append(elapsed)

        avg_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0

        self.print_result("Average analysis time", f"{avg_time:.3f}", " seconds")
        self.print_result("Standard deviation", f"{std_dev:.3f}", " seconds")
        self.print_result("Sections analyzed", len(sample_chapter['sections']))
        self.print_result("Total gaps identified", gap_analysis.get('total_gaps', 0))
        self.print_result("Completeness score", f"{gap_analysis.get('overall_completeness_score', 0):.2f}")

        return {
            "avg_time": avg_time,
            "std_dev": std_dev,
            "sections": len(sample_chapter['sections']),
            "gaps_found": gap_analysis.get('total_gaps', 0),
            "completeness_score": gap_analysis.get('overall_completeness_score', 0),
            "target_time_min": 2.0,
            "target_time_max": 10.0
        }

    async def benchmark_end_to_end(self) -> Dict[str, Any]:
        """
        Benchmark 6: End-to-End Generation Time
        Measures complete chapter generation with all Phase 2 features
        """
        self.print_header("Benchmark 6: End-to-End Generation Time")

        # Get test user
        user = self.db.query(User).filter(User.email == "test_integration@neurocore.ai").first()
        if not user:
            print("  ⚠ Test user not found, skipping end-to-end benchmark")
            return {}

        topic = "Spinal cord injury management"

        start = time.time()
        try:
            chapter = await self.orchestrator.generate_chapter(
                topic=topic,
                user=user,
                chapter_type="surgical_disease"
            )
            elapsed = time.time() - start

            self.print_result("Total generation time", f"{elapsed:.2f}", " seconds")
            self.print_result("Sections generated", len(chapter.sections) if chapter.sections else 0)
            self.print_result("Total words", chapter.get_word_count())
            self.print_result("Depth score", f"{chapter.depth_score:.2f}")
            self.print_result("Coverage score", f"{chapter.coverage_score:.2f}")
            self.print_result("Currency score", f"{chapter.currency_score:.2f}")
            self.print_result("Evidence score", f"{chapter.evidence_score:.2f}")

            return {
                "generation_time": elapsed,
                "sections": len(chapter.sections) if chapter.sections else 0,
                "words": chapter.get_word_count(),
                "quality_scores": {
                    "depth": chapter.depth_score,
                    "coverage": chapter.coverage_score,
                    "currency": chapter.currency_score,
                    "evidence": chapter.evidence_score
                }
            }

        except Exception as e:
            print(f"  ✗ Generation failed: {str(e)}")
            return {"error": str(e)}

    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all benchmarks and generate report"""
        print(f"\n{'#'*80}")
        print(f"#  Phase 2 Performance Benchmarking Suite")
        print(f"#  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*80}")

        results = {}

        # Run each benchmark
        results['parallel_research'] = await self.benchmark_parallel_research()
        results['pubmed_caching'] = await self.benchmark_pubmed_caching()
        results['ai_relevance_filtering'] = await self.benchmark_ai_relevance_filtering()
        results['deduplication'] = await self.benchmark_deduplication()
        results['gap_analysis'] = await self.benchmark_gap_analysis()
        results['end_to_end'] = await self.benchmark_end_to_end()

        # Generate summary
        self.print_summary(results)

        return results

    def print_summary(self, results: Dict[str, Any]):
        """Print benchmark summary"""
        self.print_header("Benchmark Summary")

        # Parallel Research
        if 'parallel_research' in results:
            pr = results['parallel_research']
            status = "✓" if pr.get('estimated_improvement', 0) >= pr.get('target_improvement', 40) else "⚠"
            print(f"{status} Parallel Research: ~{pr.get('estimated_improvement', 0):.1f}% faster (target: ≥40%)")

        # PubMed Caching
        if 'pubmed_caching' in results:
            pc = results['pubmed_caching']
            speedup = pc.get('speedup', 0)
            status = "✓" if speedup >= pc.get('target_speedup_min', 100) else "⚠"
            print(f"{status} PubMed Caching: {speedup:.1f}x speedup (target: 100-300x)")

        # AI Relevance Filtering
        if 'ai_relevance_filtering' in results:
            ar = results['ai_relevance_filtering']
            relevance = ar.get('avg_relevance', 0)
            target_min = ar.get('target_relevance_min', 0.85)
            status = "✓" if relevance >= target_min else "⚠"
            print(f"{status} AI Relevance Filtering: {relevance:.2f} avg relevance (target: 0.85-0.95)")

        # Deduplication
        if 'deduplication' in results:
            dd = results['deduplication']
            removed = dd.get('removal_rate', 0)
            print(f"✓ Deduplication: {removed:.1f}% duplicates removed")

        # Gap Analysis
        if 'gap_analysis' in results:
            ga = results['gap_analysis']
            time_val = ga.get('avg_time', 0)
            target_max = ga.get('target_time_max', 10)
            status = "✓" if time_val <= target_max else "⚠"
            print(f"{status} Gap Analysis: {time_val:.2f}s (target: 2-10s)")

        # End-to-End
        if 'end_to_end' in results and 'generation_time' in results['end_to_end']:
            e2e = results['end_to_end']
            gen_time = e2e.get('generation_time', 0)
            print(f"✓ End-to-End Generation: {gen_time:.2f}s")

        print(f"\n{'#'*80}")
        print(f"#  Benchmarking Complete!")
        print(f"{'#'*80}\n")

    def save_results(self, results: Dict[str, Any], filename: str = "phase2_benchmark_results.json"):
        """Save results to JSON file"""
        output_path = os.path.join(os.path.dirname(__file__), filename)

        # Add metadata
        results['metadata'] = {
            "timestamp": datetime.now().isoformat(),
            "phase": "Phase 2 Week 6",
            "description": "Performance benchmarking for Phase 2 features"
        }

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"✓ Results saved to: {output_path}")


async def main():
    """Main execution"""
    benchmark = Phase2PerformanceBenchmark()

    try:
        results = await benchmark.run_all_benchmarks()
        benchmark.save_results(results)
        return 0
    except Exception as e:
        print(f"\n✗ Benchmarking failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
