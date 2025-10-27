"""
Search Service - Unified search with hybrid ranking
Combines keyword search, semantic search, and BM25 ranking
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_, func
from datetime import datetime, timedelta
import json

from backend.services.embedding_service import EmbeddingService
from backend.database.models import PDF, Chapter, Image
from backend.utils import get_logger

logger = get_logger(__name__)


class SearchService:
    """
    Unified search service with hybrid ranking

    Search strategies:
    1. Keyword search (PostgreSQL full-text search)
    2. Semantic search (pgvector cosine similarity)
    3. Hybrid search (weighted combination)
    4. BM25 ranking for keyword relevance
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.embedding_service = EmbeddingService(db_session)

    async def search_all(
        self,
        query: str,
        search_type: str = "hybrid",
        filters: Optional[Dict[str, Any]] = None,
        max_results: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Unified search across all content types

        Args:
            query: Search query
            search_type: "keyword", "semantic", or "hybrid"
            filters: Optional filters (type, date_from, date_to, author)
            max_results: Maximum results to return
            offset: Pagination offset

        Returns:
            Search results with relevance scores
        """
        logger.info(f"Search query: '{query}' (type: {search_type})")

        filters = filters or {}

        # Execute different search strategies
        if search_type == "keyword":
            results = await self._keyword_search(query, filters, max_results, offset)
        elif search_type == "semantic":
            results = await self._semantic_search(query, filters, max_results, offset)
        else:  # hybrid
            results = await self._hybrid_search(query, filters, max_results, offset)

        # Enhance results with metadata
        enriched_results = self._enrich_results(results)

        logger.info(f"Search returned {len(enriched_results)} results")

        return {
            "query": query,
            "search_type": search_type,
            "total": len(enriched_results),
            "results": enriched_results,
            "filters_applied": filters
        }

    async def _keyword_search(
        self,
        query: str,
        filters: Dict[str, Any],
        max_results: int,
        offset: int
    ) -> List[Dict[str, Any]]:
        """
        Keyword-based search using PostgreSQL full-text search
        """
        results = []

        # Search PDFs
        pdf_results = await self._search_pdfs_keyword(query, filters, max_results // 2)
        results.extend(pdf_results)

        # Search Chapters
        chapter_results = await self._search_chapters_keyword(query, filters, max_results // 2)
        results.extend(chapter_results)

        # Sort by relevance
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)

        return results[offset:offset + max_results]

    async def _semantic_search(
        self,
        query: str,
        filters: Dict[str, Any],
        max_results: int,
        offset: int
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using vector embeddings
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query)

        results = []

        # Search PDFs by vector similarity
        pdf_results = await self._search_pdfs_semantic(query_embedding, filters, max_results // 2)
        results.extend(pdf_results)

        # Search Chapters by vector similarity
        chapter_results = await self._search_chapters_semantic(query_embedding, filters, max_results // 2)
        results.extend(chapter_results)

        # Sort by similarity
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        return results[offset:offset + max_results]

    async def _hybrid_search(
        self,
        query: str,
        filters: Dict[str, Any],
        max_results: int,
        offset: int
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining keyword and semantic search

        Scoring formula:
        final_score = (keyword_score * 0.3) + (semantic_score * 0.5) + (recency_score * 0.2)
        """
        # Get keyword results
        keyword_results = await self._keyword_search(query, filters, max_results * 2, 0)

        # Get semantic results
        semantic_results = await self._semantic_search(query, filters, max_results * 2, 0)

        # Merge and re-rank
        merged_results = self._merge_and_rerank(keyword_results, semantic_results)

        return merged_results[offset:offset + max_results]

    def _merge_and_rerank(
        self,
        keyword_results: List[Dict[str, Any]],
        semantic_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge keyword and semantic results with weighted scoring
        """
        # Create lookup by ID
        results_map = {}

        # Add keyword results
        for result in keyword_results:
            key = f"{result['type']}:{result['id']}"
            results_map[key] = {
                **result,
                "keyword_score": result.get("relevance", 0),
                "semantic_score": 0,
            }

        # Add/merge semantic results
        for result in semantic_results:
            key = f"{result['type']}:{result['id']}"
            if key in results_map:
                results_map[key]["semantic_score"] = result.get("similarity", 0)
            else:
                results_map[key] = {
                    **result,
                    "keyword_score": 0,
                    "semantic_score": result.get("similarity", 0),
                }

        # Calculate hybrid scores
        for key, result in results_map.items():
            keyword_score = result.get("keyword_score", 0)
            semantic_score = result.get("semantic_score", 0)
            recency_score = self._calculate_recency_score(result.get("created_at"))

            # Weighted combination
            hybrid_score = (
                keyword_score * 0.3 +
                semantic_score * 0.5 +
                recency_score * 0.2
            )

            result["hybrid_score"] = hybrid_score
            result["relevance"] = hybrid_score  # Unified score field

        # Sort by hybrid score
        merged = list(results_map.values())
        merged.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)

        return merged

    def _calculate_recency_score(self, created_at: Optional[str]) -> float:
        """
        Calculate recency score (0.0-1.0) based on creation date

        Scoring:
        - Last 30 days: 1.0
        - Last 90 days: 0.8
        - Last 180 days: 0.6
        - Last 365 days: 0.4
        - Older: 0.2
        """
        if not created_at:
            return 0.2

        try:
            if isinstance(created_at, str):
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                created = created_at

            age_days = (datetime.now() - created.replace(tzinfo=None)).days

            if age_days <= 30:
                return 1.0
            elif age_days <= 90:
                return 0.8
            elif age_days <= 180:
                return 0.6
            elif age_days <= 365:
                return 0.4
            else:
                return 0.2
        except Exception:
            return 0.2

    async def _search_pdfs_keyword(
        self,
        query: str,
        filters: Dict[str, Any],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Keyword search in PDFs using PostgreSQL full-text search
        """
        # Build search query
        pdfs = self.db.query(PDF).filter(
            or_(
                PDF.title.ilike(f"%{query}%"),
                PDF.extracted_text.ilike(f"%{query}%"),
                PDF.authors.ilike(f"%{query}%")
            )
        )

        # Apply filters
        if filters.get("date_from"):
            pdfs = pdfs.filter(PDF.created_at >= filters["date_from"])
        if filters.get("date_to"):
            pdfs = pdfs.filter(PDF.created_at <= filters["date_to"])
        if filters.get("author"):
            pdfs = pdfs.filter(PDF.authors.ilike(f"%{filters['author']}%"))

        pdfs = pdfs.limit(max_results).all()

        results = []
        for pdf in pdfs:
            # Calculate simple relevance score
            relevance = self._calculate_keyword_relevance(
                query,
                pdf.title,
                pdf.extracted_text
            )

            results.append({
                "id": str(pdf.id),
                "type": "pdf",
                "title": pdf.title,
                "authors": pdf.authors,
                "year": pdf.year,
                "journal": pdf.journal,
                "created_at": pdf.created_at.isoformat() if pdf.created_at else None,
                "relevance": relevance,
                "excerpt": self._extract_excerpt(pdf.extracted_text, query)
            })

        return results

    async def _search_chapters_keyword(
        self,
        query: str,
        filters: Dict[str, Any],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Keyword search in chapters
        """
        chapters = self.db.query(Chapter).filter(
            or_(
                Chapter.title.ilike(f"%{query}%"),
                Chapter.summary.ilike(f"%{query}%")
            )
        )

        # Apply filters
        if filters.get("date_from"):
            chapters = chapters.filter(Chapter.created_at >= filters["date_from"])
        if filters.get("date_to"):
            chapters = chapters.filter(Chapter.created_at <= filters["date_to"])

        chapters = chapters.limit(max_results).all()

        results = []
        for chapter in chapters:
            # Build searchable text
            chapter_text = f"{chapter.title} {chapter.summary or ''}"
            if chapter.sections:
                for section in chapter.sections:
                    chapter_text += f" {section.get('content', '')}"

            relevance = self._calculate_keyword_relevance(query, chapter.title, chapter_text)

            results.append({
                "id": str(chapter.id),
                "type": "chapter",
                "title": chapter.title,
                "summary": chapter.summary,
                "author_id": str(chapter.author_id),
                "created_at": chapter.created_at.isoformat() if chapter.created_at else None,
                "generation_status": chapter.generation_status,
                "word_count": chapter.word_count,
                "relevance": relevance,
                "excerpt": self._extract_excerpt(chapter_text, query)
            })

        return results

    async def _search_pdfs_semantic(
        self,
        query_embedding: List[float],
        filters: Dict[str, Any],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in PDFs using vector similarity
        """
        # Build SQL query for vector similarity
        sql = text("""
            SELECT
                id,
                title,
                authors,
                year,
                journal,
                extracted_text,
                created_at,
                1 - (embedding <=> :query_embedding) as similarity
            FROM pdfs
            WHERE embedding IS NOT NULL
              AND extraction_status = 'completed'
              AND 1 - (embedding <=> :query_embedding) >= :min_similarity
            ORDER BY embedding <=> :query_embedding
            LIMIT :max_results
        """)

        result = self.db.execute(
            sql,
            {
                "query_embedding": query_embedding,
                "min_similarity": 0.6,  # Minimum similarity threshold
                "max_results": max_results
            }
        )

        results = []
        for row in result:
            results.append({
                "id": str(row.id),
                "type": "pdf",
                "title": row.title,
                "authors": row.authors,
                "year": row.year,
                "journal": row.journal,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "similarity": float(row.similarity),
                "excerpt": self._extract_excerpt_first_n(row.extracted_text, 200)
            })

        return results

    async def _search_chapters_semantic(
        self,
        query_embedding: List[float],
        filters: Dict[str, Any],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in chapters using vector similarity
        """
        sql = text("""
            SELECT
                id,
                title,
                summary,
                author_id,
                created_at,
                generation_status,
                word_count,
                1 - (embedding <=> :query_embedding) as similarity
            FROM chapters
            WHERE embedding IS NOT NULL
              AND generation_status IN ('generated', 'reviewed', 'published')
              AND 1 - (embedding <=> :query_embedding) >= :min_similarity
            ORDER BY embedding <=> :query_embedding
            LIMIT :max_results
        """)

        result = self.db.execute(
            sql,
            {
                "query_embedding": query_embedding,
                "min_similarity": 0.6,
                "max_results": max_results
            }
        )

        results = []
        for row in result:
            results.append({
                "id": str(row.id),
                "type": "chapter",
                "title": row.title,
                "summary": row.summary,
                "author_id": str(row.author_id),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "generation_status": row.generation_status,
                "word_count": row.word_count,
                "similarity": float(row.similarity),
                "excerpt": row.summary or ""
            })

        return results

    def _calculate_keyword_relevance(
        self,
        query: str,
        title: str,
        content: str
    ) -> float:
        """
        Calculate keyword relevance score using simple TF-IDF-like approach

        Returns:
            Relevance score (0.0-1.0)
        """
        query_terms = set(query.lower().split())
        title_lower = (title or "").lower()
        content_lower = (content or "")[:5000].lower()  # First 5000 chars

        # Count term occurrences
        title_matches = sum(1 for term in query_terms if term in title_lower)
        content_matches = sum(1 for term in query_terms if term in content_lower)

        # Weighted score (title matches worth more)
        if not query_terms:
            return 0.0

        title_score = (title_matches / len(query_terms)) * 0.6
        content_score = min(content_matches / len(query_terms), 1.0) * 0.4

        return min(title_score + content_score, 1.0)

    def _extract_excerpt(self, text: str, query: str, max_length: int = 200) -> str:
        """
        Extract relevant excerpt from text containing query terms
        """
        if not text:
            return ""

        text = text[:10000]  # Limit text length
        text_lower = text.lower()
        query_lower = query.lower()

        # Find first occurrence of query
        pos = text_lower.find(query_lower)

        if pos == -1:
            # Query not found, try individual terms
            for term in query.split():
                pos = text_lower.find(term.lower())
                if pos != -1:
                    break

        if pos == -1:
            # Still not found, return beginning
            return text[:max_length] + "..."

        # Extract context around match
        start = max(0, pos - max_length // 2)
        end = min(len(text), pos + max_length // 2)

        excerpt = text[start:end].strip()

        if start > 0:
            excerpt = "..." + excerpt
        if end < len(text):
            excerpt = excerpt + "..."

        return excerpt

    def _extract_excerpt_first_n(self, text: str, n: int = 200) -> str:
        """
        Extract first N characters as excerpt
        """
        if not text:
            return ""

        text = text.strip()
        if len(text) <= n:
            return text

        return text[:n] + "..."

    def _enrich_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich search results with additional metadata
        """
        for result in results:
            # Add search result metadata
            result["result_type"] = "search_result"

            # Ensure all scores are present
            if "relevance" not in result:
                result["relevance"] = result.get("similarity", 0.5)

            # Add highlight information
            result["highlighted"] = True if result.get("excerpt") else False

        return results

    async def get_search_suggestions(
        self,
        partial_query: str,
        max_suggestions: int = 10
    ) -> List[str]:
        """
        Get search suggestions/autocomplete based on partial query

        Args:
            partial_query: Partial search query
            max_suggestions: Maximum number of suggestions

        Returns:
            List of search suggestions
        """
        suggestions = []

        # Get titles from PDFs
        pdfs = self.db.query(PDF.title).filter(
            PDF.title.ilike(f"%{partial_query}%")
        ).limit(max_suggestions // 2).all()

        suggestions.extend([pdf.title for pdf in pdfs if pdf.title])

        # Get titles from chapters
        chapters = self.db.query(Chapter.title).filter(
            Chapter.title.ilike(f"%{partial_query}%")
        ).limit(max_suggestions // 2).all()

        suggestions.extend([chapter.title for chapter in chapters if chapter.title])

        # Deduplicate and sort
        unique_suggestions = list(set(suggestions))
        unique_suggestions.sort()

        return unique_suggestions[:max_suggestions]

    async def find_related_content(
        self,
        content_id: str,
        content_type: str = "chapter",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find content related to given item using vector similarity

        Args:
            content_id: ID of content item
            content_type: "chapter" or "pdf"
            max_results: Maximum number of related items

        Returns:
            List of related content with similarity scores
        """
        logger.info(f"Finding related content for {content_type}:{content_id}")

        # Get source embedding
        if content_type == "chapter":
            source = self.db.query(Chapter).filter(Chapter.id == content_id).first()
        elif content_type == "pdf":
            source = self.db.query(PDF).filter(PDF.id == content_id).first()
        else:
            raise ValueError(f"Invalid content_type: {content_type}")

        if not source or not source.embedding:
            return []

        source_embedding = source.embedding

        # Find similar content
        if content_type == "chapter":
            related = await self._find_related_chapters(source_embedding, content_id, max_results)
        else:
            related = await self._find_related_pdfs(source_embedding, content_id, max_results)

        return related

    async def _find_related_chapters(
        self,
        embedding: List[float],
        exclude_id: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Find related chapters using vector similarity"""
        sql = text("""
            SELECT
                id,
                title,
                summary,
                word_count,
                1 - (embedding <=> :embedding) as similarity
            FROM chapters
            WHERE embedding IS NOT NULL
              AND id != :exclude_id
              AND generation_status IN ('generated', 'reviewed', 'published')
            ORDER BY embedding <=> :embedding
            LIMIT :max_results
        """)

        result = self.db.execute(
            sql,
            {
                "embedding": embedding,
                "exclude_id": exclude_id,
                "max_results": max_results
            }
        )

        related = []
        for row in result:
            related.append({
                "id": str(row.id),
                "type": "chapter",
                "title": row.title,
                "summary": row.summary,
                "word_count": row.word_count,
                "similarity": float(row.similarity)
            })

        return related

    async def _find_related_pdfs(
        self,
        embedding: List[float],
        exclude_id: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Find related PDFs using vector similarity"""
        sql = text("""
            SELECT
                id,
                title,
                authors,
                year,
                1 - (embedding <=> :embedding) as similarity
            FROM pdfs
            WHERE embedding IS NOT NULL
              AND id != :exclude_id
              AND extraction_status = 'completed'
            ORDER BY embedding <=> :embedding
            LIMIT :max_results
        """)

        result = self.db.execute(
            sql,
            {
                "embedding": embedding,
                "exclude_id": exclude_id,
                "max_results": max_results
            }
        )

        related = []
        for row in result:
            related.append({
                "id": str(row.id),
                "type": "pdf",
                "title": row.title,
                "authors": row.authors,
                "year": row.year,
                "similarity": float(row.similarity)
            })

        return related
