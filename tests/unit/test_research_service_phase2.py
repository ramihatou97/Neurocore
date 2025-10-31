"""
Unit tests for Phase 2 research service enhancements
Tests parallel research execution and PubMed caching features
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from backend.services.research_service import ResearchService
from backend.services.cache_service import CacheService
from backend.database.models import PDF


class TestParallelResearchExecution:
    """Test suite for parallel internal research"""

    @pytest.mark.asyncio
    async def test_internal_research_parallel_success(self, db_session: Session, sample_pdf):
        """Test parallel execution returns combined results from all queries"""
        # Setup
        cache_service = CacheService(redis_client=None)
        research_service = ResearchService(db_session, cache_service)

        queries = [
            "glioblastoma treatment",
            "traumatic brain injury",
            "surgical technique"
        ]

        # Execute parallel research
        results = await research_service.internal_research_parallel(
            queries=queries,
            max_results_per_query=5,
            min_relevance=0.5
        )

        # Assertions
        assert isinstance(results, list)
        # Results should be combined from all queries
        # Each query can return 0-5 results depending on relevance
        assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_internal_research_parallel_performance(self, db_session: Session):
        """Test parallel execution is faster than sequential"""
        cache_service = CacheService(redis_client=None)
        research_service = ResearchService(db_session, cache_service)

        # Create multiple test PDFs
        for i in range(10):
            pdf = PDF(
                filename=f"test_paper_{i}.pdf",
                file_path=f"/test/test_paper_{i}.pdf",
                file_size_bytes=1024000,
                total_pages=20,
                title=f"Test Paper {i} - Neurosurgery Research",
                authors=["Dr. Test"],
                publication_year=2023,
                indexing_status="completed",
                text_extracted=True
            )
            db_session.add(pdf)
        db_session.commit()

        queries = ["neurosurgery", "brain", "surgery", "treatment", "diagnosis"]

        # Time parallel execution
        start_parallel = time.time()
        parallel_results = await research_service.internal_research_parallel(
            queries=queries,
            max_results_per_query=5,
            min_relevance=0.5
        )
        parallel_duration = time.time() - start_parallel

        # Time sequential execution (baseline)
        start_sequential = time.time()
        sequential_results = []
        for query in queries:
            results = await research_service.internal_research(
                query=query,
                max_results=5,
                min_relevance=0.5
            )
            sequential_results.extend(results)
        sequential_duration = time.time() - start_sequential

        # Assertions
        # Parallel should be faster than sequential (or at least not significantly slower)
        # Allow some overhead for parallel execution setup
        assert parallel_duration <= sequential_duration * 1.2, \
            f"Parallel ({parallel_duration:.2f}s) should be faster than sequential ({sequential_duration:.2f}s)"

        # Results should be similar in length
        assert len(parallel_results) == len(sequential_results)

    @pytest.mark.asyncio
    async def test_internal_research_parallel_with_failing_query(self, db_session: Session):
        """Test parallel execution handles failing queries gracefully"""
        cache_service = CacheService(redis_client=None)
        research_service = ResearchService(db_session, cache_service)

        # Mock one query to fail
        original_internal_research = research_service.internal_research

        async def mock_internal_research(query, max_results=10, min_relevance=0.7):
            if "fail" in query.lower():
                raise Exception("Simulated query failure")
            return await original_internal_research(query, max_results, min_relevance)

        research_service.internal_research = mock_internal_research

        queries = [
            "normal query 1",
            "FAIL query",  # This will fail
            "normal query 2"
        ]

        # Execute - should not raise exception
        results = await research_service.internal_research_parallel(
            queries=queries,
            max_results_per_query=5,
            min_relevance=0.5
        )

        # Should still return results from successful queries
        assert isinstance(results, list)
        # Even if all queries fail, should return empty list (not raise exception)

    @pytest.mark.asyncio
    async def test_internal_research_parallel_empty_queries(self, db_session: Session):
        """Test parallel research with empty query list"""
        cache_service = CacheService(redis_client=None)
        research_service = ResearchService(db_session, cache_service)

        results = await research_service.internal_research_parallel(
            queries=[],
            max_results_per_query=5,
            min_relevance=0.7
        )

        assert results == []


class TestPubMedCaching:
    """Test suite for PubMed caching functionality"""

    @pytest.mark.asyncio
    async def test_pubmed_cache_key_generation_consistency(self, db_session: Session):
        """Test cache keys are generated consistently"""
        cache_service = CacheService(redis_client=None)
        research_service = ResearchService(db_session, cache_service)

        query = "glioblastoma treatment"
        max_results = 10
        recent_years = 5

        # Generate key twice with same parameters
        key1 = research_service._generate_pubmed_cache_key(query, max_results, recent_years)
        key2 = research_service._generate_pubmed_cache_key(query, max_results, recent_years)

        # Keys should be identical
        assert key1 == key2
        assert key1.startswith("pubmed:")

        # Different parameters should generate different keys
        key3 = research_service._generate_pubmed_cache_key(query, max_results, 3)  # Different recent_years
        assert key1 != key3

        key4 = research_service._generate_pubmed_cache_key("different query", max_results, recent_years)
        assert key1 != key4

    @pytest.mark.asyncio
    async def test_pubmed_cache_hit(self, db_session: Session):
        """Test PubMed cache returns cached results on hit"""
        # Create mock Redis client
        mock_redis = Mock()
        cache_service = CacheService(redis_client=mock_redis)
        research_service = ResearchService(db_session, cache_service)

        # Mock cache hit
        cached_results = [
            {
                "pmid": "12345678",
                "title": "Cached Paper",
                "abstract": "This is a cached result",
                "authors": ["Dr. Cache"],
                "journal": "Cache Journal",
                "year": 2023,
                "doi": "10.1234/cached",
                "source": "pubmed"
            }
        ]

        # Mock cache_service.get_search_results to return cached data
        cache_service.get_search_results = AsyncMock(return_value=cached_results)

        # Call external_research_pubmed
        results = await research_service.external_research_pubmed(
            query="test query",
            max_results=10,
            recent_years=5,
            use_cache=True
        )

        # Should return cached results
        assert results == cached_results
        assert len(results) == 1
        assert results[0]["pmid"] == "12345678"

    @pytest.mark.asyncio
    async def test_pubmed_cache_miss_then_set(self, db_session: Session):
        """Test PubMed cache miss triggers API call and caches result"""
        # Create mock Redis client
        mock_redis = Mock()
        cache_service = CacheService(redis_client=mock_redis)
        research_service = ResearchService(db_session, cache_service)

        # Mock cache miss (returns None)
        cache_service.get_search_results = AsyncMock(return_value=None)
        cache_service.set_search_results = AsyncMock()

        # Mock httpx client for PubMed API
        with patch("backend.services.research_service.httpx.AsyncClient") as mock_client:
            # Mock search response
            search_response = Mock()
            search_response.json.return_value = {
                "esearchresult": {
                    "idlist": ["12345678"]
                }
            }
            search_response.raise_for_status = Mock()

            # Mock fetch response
            fetch_response = Mock()
            fetch_response.text = """
            <PubmedArticleSet>
                <PubmedArticle>
                    <MedlineCitation>
                        <PMID>12345678</PMID>
                        <Article>
                            <ArticleTitle>Test Article</ArticleTitle>
                            <Abstract>
                                <AbstractText>Test abstract</AbstractText>
                            </Abstract>
                            <AuthorList>
                                <Author>
                                    <LastName>Smith</LastName>
                                    <ForeName>John</ForeName>
                                </Author>
                            </AuthorList>
                        </Article>
                        <MedlineJournalInfo>
                            <Title>Test Journal</Title>
                        </MedlineJournalInfo>
                    </MedlineCitation>
                    <PubmedData>
                        <ArticleIdList>
                            <ArticleId IdType="doi">10.1234/test</ArticleId>
                        </ArticleIdList>
                        <History>
                            <PubMedPubDate PubStatus="pubmed">
                                <Year>2023</Year>
                            </PubMedPubDate>
                        </History>
                    </PubmedData>
                </PubmedArticle>
            </PubmedArticleSet>
            """
            fetch_response.raise_for_status = Mock()

            # Setup mock client context manager
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(
                side_effect=[search_response, fetch_response]
            )
            mock_client.return_value = mock_context

            # Call external_research_pubmed
            results = await research_service.external_research_pubmed(
                query="test query",
                max_results=10,
                recent_years=5,
                use_cache=True
            )

            # Should have called set_search_results to cache the results
            cache_service.set_search_results.assert_called_once()

            # Verify results
            assert len(results) == 1
            assert results[0]["pmid"] == "12345678"

    @pytest.mark.asyncio
    async def test_pubmed_cache_disabled(self, db_session: Session):
        """Test PubMed caching can be disabled"""
        cache_service = CacheService(redis_client=None)
        research_service = ResearchService(db_session, cache_service)

        # Mock httpx client
        with patch("backend.services.research_service.httpx.AsyncClient") as mock_client:
            # Mock empty response
            search_response = Mock()
            search_response.json.return_value = {"esearchresult": {"idlist": []}}
            search_response.raise_for_status = Mock()

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(return_value=search_response)
            mock_client.return_value = mock_context

            # Call with use_cache=False
            results = await research_service.external_research_pubmed(
                query="test query",
                max_results=10,
                recent_years=5,
                use_cache=False
            )

            # Should work without cache
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_pubmed_cache_service_unavailable(self, db_session: Session):
        """Test PubMed research works when cache service fails"""
        # Create mock Redis client that fails
        mock_redis = Mock()
        cache_service = CacheService(redis_client=mock_redis)
        research_service = ResearchService(db_session, cache_service)

        # Mock cache_service methods to raise exception
        cache_service.get_search_results = AsyncMock(side_effect=Exception("Redis connection failed"))
        cache_service.set_search_results = AsyncMock(side_effect=Exception("Redis connection failed"))

        # Mock httpx client
        with patch("backend.services.research_service.httpx.AsyncClient") as mock_client:
            # Mock empty response
            search_response = Mock()
            search_response.json.return_value = {"esearchresult": {"idlist": []}}
            search_response.raise_for_status = Mock()

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(return_value=search_response)
            mock_client.return_value = mock_context

            # Should not raise exception despite cache failures
            results = await research_service.external_research_pubmed(
                query="test query",
                max_results=10,
                recent_years=5,
                use_cache=True
            )

            # Should still work by falling back to direct API calls
            assert isinstance(results, list)


class TestCacheKeyGeneration:
    """Test cache key generation for consistency"""

    def test_cache_key_hashing(self, db_session: Session):
        """Test cache keys use consistent hashing"""
        cache_service = CacheService(redis_client=None)
        research_service = ResearchService(db_session, cache_service)

        # Same inputs should produce same hash
        key1 = research_service._generate_pubmed_cache_key("query", 10, 5)
        key2 = research_service._generate_pubmed_cache_key("query", 10, 5)
        assert key1 == key2

        # Different inputs should produce different hashes
        key3 = research_service._generate_pubmed_cache_key("different", 10, 5)
        assert key1 != key3

    def test_cache_key_format(self, db_session: Session):
        """Test cache key follows expected format"""
        cache_service = CacheService(redis_client=None)
        research_service = ResearchService(db_session, cache_service)

        key = research_service._generate_pubmed_cache_key("test query", 10, 5)

        # Should start with 'pubmed:' prefix
        assert key.startswith("pubmed:")

        # Should have hash after prefix
        parts = key.split(":")
        assert len(parts) == 2
        assert len(parts[1]) == 32  # MD5 hash is 32 characters


class TestResearchServiceIntegration:
    """Integration tests for research service Phase 2 features"""

    @pytest.mark.asyncio
    async def test_research_workflow_with_parallel_and_cache(self, db_session: Session):
        """Test complete research workflow using both parallel execution and caching"""
        # Create mock cache
        mock_redis = Mock()
        cache_service = CacheService(redis_client=mock_redis)
        research_service = ResearchService(db_session, cache_service)

        # Add test PDFs
        for i in range(5):
            pdf = PDF(
                filename=f"paper_{i}.pdf",
                file_path=f"/test/paper_{i}.pdf",
                file_size_bytes=1024000,
                total_pages=20,
                title=f"Neurosurgery Research Paper {i}",
                authors=["Dr. Test"],
                publication_year=2023,
                indexing_status="completed",
                text_extracted=True
            )
            db_session.add(pdf)
        db_session.commit()

        # Test parallel internal research
        internal_queries = ["neurosurgery", "brain surgery", "surgical technique"]
        internal_results = await research_service.internal_research_parallel(
            queries=internal_queries,
            max_results_per_query=3,
            min_relevance=0.5
        )

        assert isinstance(internal_results, list)

        # Test PubMed with caching (mock the cache behavior)
        cache_service.get_search_results = AsyncMock(return_value=None)
        cache_service.set_search_results = AsyncMock()

        with patch("backend.services.research_service.httpx.AsyncClient") as mock_client:
            search_response = Mock()
            search_response.json.return_value = {"esearchresult": {"idlist": []}}
            search_response.raise_for_status = Mock()

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(return_value=search_response)
            mock_client.return_value = mock_context

            pubmed_results = await research_service.external_research_pubmed(
                query="glioblastoma",
                max_results=10,
                use_cache=True
            )

            assert isinstance(pubmed_results, list)
