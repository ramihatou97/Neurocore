"""
Research Service - Internal and external research for chapter generation
Handles vector search, PubMed queries, and source ranking
"""

import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database.models import PDF, Image, Chapter
from backend.services.ai_provider_service import AIProviderService
from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class ResearchService:
    """
    Service for research operations

    Internal Research:
    - Vector similarity search on indexed PDFs
    - Image search with semantic matching
    - Citation network traversal

    External Research:
    - PubMed API queries
    - arXiv API queries (future)
    - Recent paper discovery
    """

    def __init__(self, db_session: Session):
        """
        Initialize research service

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.ai_service = AIProviderService()

    async def internal_research(
        self,
        query: str,
        max_results: int = 10,
        min_relevance: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search internal database for relevant content

        Args:
            query: Search query
            max_results: Maximum number of results
            min_relevance: Minimum relevance score (0-1)

        Returns:
            List of relevant PDFs with metadata and relevance scores
        """
        logger.info(f"Internal research: '{query}' (max: {max_results})")

        # Generate query embedding
        embedding_result = await self.ai_service.generate_embedding(query)
        query_embedding = embedding_result["embedding"]

        # Vector similarity search using pgvector
        # Note: This requires PDFs to have embeddings generated (Phase 3 extension)
        # For now, we'll do a simpler text search

        # Search PDFs by title, authors, and metadata
        pdfs = self.db.query(PDF).filter(
            PDF.text_extracted == True
        ).all()

        results = []

        for pdf in pdfs[:max_results]:
            # Simple relevance scoring based on text matching
            # In production, use vector similarity
            relevance = self._calculate_text_relevance(query, pdf)

            if relevance >= min_relevance:
                results.append({
                    "pdf_id": str(pdf.id),
                    "title": pdf.title or pdf.filename,
                    "authors": pdf.authors or [],
                    "year": pdf.publication_year,
                    "journal": pdf.journal,
                    "doi": pdf.doi,
                    "pmid": pdf.pmid,
                    "relevance_score": relevance,
                    "total_pages": pdf.total_pages,
                    "total_words": pdf.total_words,
                    "file_path": pdf.file_path
                })

        # Sort by relevance
        results.sort(key=lambda x: x["relevance_score"], reverse=True)

        logger.info(f"Internal research found {len(results)} relevant sources")

        return results

    def _calculate_text_relevance(self, query: str, pdf: PDF) -> float:
        """
        Calculate simple text-based relevance score

        Args:
            query: Search query
            pdf: PDF object

        Returns:
            Relevance score (0-1)
        """
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        score = 0.0
        max_score = 0.0

        # Title matching (weight: 0.4)
        if pdf.title:
            title_lower = pdf.title.lower()
            title_terms = set(title_lower.split())
            title_overlap = len(query_terms & title_terms) / len(query_terms) if query_terms else 0
            score += title_overlap * 0.4
        max_score += 0.4

        # Authors matching (weight: 0.2)
        if pdf.authors:
            authors_text = " ".join(pdf.authors).lower()
            if any(term in authors_text for term in query_terms):
                score += 0.2
        max_score += 0.2

        # Journal matching (weight: 0.2)
        if pdf.journal:
            journal_lower = pdf.journal.lower()
            if any(term in journal_lower for term in query_terms):
                score += 0.2
        max_score += 0.2

        # Filename matching (weight: 0.2)
        filename_lower = pdf.filename.lower()
        if any(term in filename_lower for term in query_terms):
            score += 0.2
        max_score += 0.2

        return score / max_score if max_score > 0 else 0.0

    async def external_research_pubmed(
        self,
        query: str,
        max_results: int = 10,
        recent_years: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search PubMed for recent papers

        Args:
            query: Search query
            max_results: Maximum number of results
            recent_years: Only include papers from last N years

        Returns:
            List of PubMed papers with metadata
        """
        logger.info(f"PubMed research: '{query}' (max: {max_results})")

        results = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Search PubMed to get PMIDs
                search_params = {
                    "db": "pubmed",
                    "term": query,
                    "retmax": max_results,
                    "retmode": "json",
                    "sort": "date",
                    "reldate": recent_years * 365  # Days
                }

                search_response = await client.get(
                    settings.PUBMED_BASE_URL,
                    params=search_params
                )
                search_response.raise_for_status()
                search_data = search_response.json()

                pmids = search_data.get("esearchresult", {}).get("idlist", [])

                if not pmids:
                    logger.info("No PubMed results found")
                    return []

                # Step 2: Fetch details for each PMID
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(pmids),
                    "retmode": "xml"
                }

                fetch_response = await client.get(
                    settings.PUBMED_EFETCH_URL,
                    params=fetch_params
                )
                fetch_response.raise_for_status()

                # Parse XML response
                root = ET.fromstring(fetch_response.text)

                for article in root.findall(".//PubmedArticle"):
                    try:
                        paper = self._parse_pubmed_article(article)
                        if paper:
                            results.append(paper)
                    except Exception as e:
                        logger.warning(f"Failed to parse PubMed article: {str(e)}")
                        continue

                logger.info(f"PubMed research found {len(results)} papers")

        except Exception as e:
            logger.error(f"PubMed research failed: {str(e)}", exc_info=True)

        return results

    def _parse_pubmed_article(self, article_xml) -> Optional[Dict[str, Any]]:
        """
        Parse PubMed article XML

        Args:
            article_xml: XML element

        Returns:
            Dictionary with paper metadata
        """
        try:
            # Extract PMID
            pmid_elem = article_xml.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else None

            # Extract title
            title_elem = article_xml.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else None

            # Extract abstract
            abstract_texts = article_xml.findall(".//AbstractText")
            abstract = " ".join([a.text for a in abstract_texts if a.text]) if abstract_texts else None

            # Extract authors
            authors = []
            for author in article_xml.findall(".//Author"):
                lastname = author.find("LastName")
                forename = author.find("ForeName")
                if lastname is not None:
                    name = f"{forename.text} {lastname.text}" if forename is not None else lastname.text
                    authors.append(name)

            # Extract journal
            journal_elem = article_xml.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else None

            # Extract year
            year_elem = article_xml.find(".//PubDate/Year")
            year = int(year_elem.text) if year_elem is not None and year_elem.text else None

            # Extract DOI
            doi = None
            for article_id in article_xml.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text
                    break

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "year": year,
                "doi": doi,
                "source": "pubmed"
            }

        except Exception as e:
            logger.warning(f"Failed to parse article: {str(e)}")
            return None

    async def search_images(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant images in indexed PDFs

        Args:
            query: Search query
            max_results: Maximum number of images

        Returns:
            List of relevant images with metadata
        """
        logger.info(f"Image search: '{query}' (max: {max_results})")

        # For now, return images from indexed PDFs
        # In production, use vector similarity on image embeddings

        images = self.db.query(Image).filter(
            Image.ai_description.isnot(None)
        ).limit(max_results).all()

        results = []
        for img in images:
            # Simple text matching on AI description
            relevance = 0.5  # Default relevance
            if img.ai_description:
                query_lower = query.lower()
                desc_lower = img.ai_description.lower()
                if any(term in desc_lower for term in query_lower.split()):
                    relevance = 0.8

            results.append({
                "image_id": str(img.id),
                "pdf_id": str(img.pdf_id),
                "page_number": img.page_number,
                "file_path": img.file_path,
                "thumbnail_path": img.thumbnail_path,
                "description": img.ai_description,
                "image_type": img.image_type,
                "quality_score": img.quality_score,
                "relevance": relevance
            })

        logger.info(f"Image search found {len(results)} images")

        return results

    async def rank_sources(
        self,
        sources: List[Dict[str, Any]],
        query: str,
        criteria: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank sources by multiple criteria

        Args:
            sources: List of sources to rank
            query: Original query
            criteria: Optional custom ranking criteria weights

        Returns:
            Ranked list of sources
        """
        if not criteria:
            criteria = {
                "relevance": 0.4,
                "recency": 0.3,
                "quality": 0.2,
                "citation_count": 0.1
            }

        for source in sources:
            score = 0.0

            # Relevance score
            if "relevance_score" in source:
                score += source["relevance_score"] * criteria.get("relevance", 0.4)

            # Recency score (prefer recent papers)
            if "year" in source and source["year"]:
                current_year = 2025
                years_old = current_year - source["year"]
                recency_score = max(0, 1 - (years_old / 10))  # Decay over 10 years
                score += recency_score * criteria.get("recency", 0.3)

            # Quality score (journal reputation, etc.)
            # Placeholder - would integrate with journal impact factors
            quality_score = 0.5
            score += quality_score * criteria.get("quality", 0.2)

            source["final_score"] = score

        # Sort by final score
        sources.sort(key=lambda x: x.get("final_score", 0), reverse=True)

        return sources
