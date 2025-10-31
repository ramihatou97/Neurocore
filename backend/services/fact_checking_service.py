"""
Medical Fact-Checking Service
Uses GPT-4o with structured outputs to verify medical claims against sources

This service provides:
- Individual claim verification with confidence scores
- Cross-referencing with PubMed sources
- Categorization by claim type (anatomy, diagnosis, treatment, etc.)
- Severity assessment for incorrect claims
- Overall accuracy scoring
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.services.ai_provider_service import AIProviderService, AITask
from backend.schemas.ai_schemas import FACT_CHECK_SCHEMA
from backend.utils import get_logger

logger = get_logger(__name__)


class FactCheckingService:
    """
    Medical fact-checking service using GPT-4o structured outputs

    Ensures medical accuracy by:
    1. Extracting specific claims from generated content
    2. Cross-referencing with provided sources
    3. Assigning confidence scores and verification status
    4. Identifying critical issues requiring attention
    5. Providing actionable recommendations
    """

    def __init__(self):
        """Initialize fact-checking service"""
        self.ai_service = AIProviderService()

    async def fact_check_section(
        self,
        section_content: str,
        sources: List[Dict[str, Any]],
        chapter_title: str,
        section_title: str
    ) -> Dict[str, Any]:
        """
        Fact-check a single section against available sources

        Args:
            section_content: The section text to verify
            sources: List of research sources for verification
            chapter_title: Title of the chapter for context
            section_title: Title of the section being checked

        Returns:
            Dictionary with fact-check results matching FACT_CHECK_SCHEMA
        """
        logger.info(f"Fact-checking section: {section_title}")

        # Build source summary for AI
        source_summary = self._build_source_summary(sources)

        # Create fact-checking prompt
        prompt = f"""
        You are a medical fact-checker specializing in neurosurgery. Your task is to verify
        medical claims in the following content against the provided research sources.

        **Chapter**: {chapter_title}
        **Section**: {section_title}

        **Content to Verify**:
        {section_content}

        **Available Research Sources**:
        {source_summary}

        **Your Task**:
        1. Identify specific medical claims in the content (anatomy, pathophysiology, diagnosis, treatment, etc.)
        2. Verify each claim against the provided sources
        3. Assign a confidence score (0-1) to each verification
        4. Categorize each claim by type
        5. Assess the severity if a claim is wrong (critical, high, medium, low)
        6. Provide source citations (PubMed ID if available)
        7. Flag critical issues that need immediate attention
        8. Provide recommendations for improving accuracy

        **Important**:
        - Be rigorous and evidence-based
        - If a claim cannot be verified with the sources, mark verified=false
        - Critical severity: Patient safety impact or fundamental medical errors
        - High severity: Significant clinical implications
        - Medium severity: Important but not immediately dangerous
        - Low severity: Minor details or non-critical information

        Extract and verify all significant medical claims in the content.
        """

        try:
            # Use structured outputs for guaranteed valid response
            response = await self.ai_service.generate_text_with_schema(
                prompt=prompt,
                schema=FACT_CHECK_SCHEMA,
                task=AITask.FACT_CHECKING,
                max_tokens=3000,
                temperature=0.2  # Low temperature for factual verification
            )

            fact_check_results = response["data"]

            # Add metadata
            fact_check_results["section_title"] = section_title
            fact_check_results["checked_at"] = datetime.utcnow().isoformat()
            fact_check_results["ai_model"] = response["model"]
            fact_check_results["ai_provider"] = response["provider"]
            fact_check_results["ai_cost_usd"] = response["cost_usd"]
            fact_check_results["sources_used_count"] = len(sources)

            # Log summary
            verified_count = sum(1 for c in fact_check_results["claims"] if c["verified"])
            total_claims = len(fact_check_results["claims"])
            critical_count = len(fact_check_results["critical_issues"])

            logger.info(
                f"Fact-check complete: {verified_count}/{total_claims} verified, "
                f"{critical_count} critical issues, "
                f"accuracy: {fact_check_results['overall_accuracy']:.2f}"
            )

            return fact_check_results

        except Exception as e:
            logger.error(f"Fact-checking failed: {str(e)}", exc_info=True)
            raise

    async def fact_check_chapter(
        self,
        sections: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        chapter_title: str
    ) -> Dict[str, Any]:
        """
        Fact-check an entire chapter (all sections)

        Args:
            sections: List of section dictionaries with 'title' and 'content'
            sources: List of research sources for verification
            chapter_title: Title of the chapter

        Returns:
            Aggregated fact-check results for entire chapter
        """
        logger.info(f"Fact-checking entire chapter: {chapter_title} ({len(sections)} sections)")

        section_results = []
        total_cost = 0.0
        all_claims = []
        all_critical_issues = []

        # Fact-check each section
        for idx, section in enumerate(sections):
            section_title = section.get("title", f"Section {idx + 1}")
            section_content = section.get("content", "")

            if not section_content:
                logger.warning(f"Skipping empty section: {section_title}")
                continue

            try:
                result = await self.fact_check_section(
                    section_content=section_content,
                    sources=sources,
                    chapter_title=chapter_title,
                    section_title=section_title
                )

                section_results.append(result)
                total_cost += result.get("ai_cost_usd", 0.0)
                all_claims.extend(result["claims"])
                all_critical_issues.extend(result["critical_issues"])

            except Exception as e:
                logger.error(f"Failed to fact-check section {section_title}: {str(e)}")
                continue

        # Calculate aggregate metrics
        total_claims = len(all_claims)
        verified_claims = sum(1 for c in all_claims if c["verified"])
        overall_accuracy = verified_claims / total_claims if total_claims > 0 else 0.0

        # Count claims by severity
        critical_severity_count = sum(
            1 for c in all_claims
            if not c["verified"] and c["severity_if_wrong"] == "critical"
        )
        high_severity_count = sum(
            1 for c in all_claims
            if not c["verified"] and c["severity_if_wrong"] == "high"
        )

        # Aggregate results
        aggregate_results = {
            "chapter_title": chapter_title,
            "sections_checked": len(section_results),
            "total_claims": total_claims,
            "verified_claims": verified_claims,
            "unverified_claims": total_claims - verified_claims,
            "overall_accuracy": overall_accuracy,
            "critical_issues_count": len(all_critical_issues),
            "critical_severity_claims": critical_severity_count,
            "high_severity_claims": high_severity_count,
            "all_critical_issues": all_critical_issues,
            "section_results": section_results,
            "total_cost_usd": total_cost,
            "checked_at": datetime.utcnow().isoformat()
        }

        logger.info(
            f"Chapter fact-check complete: {verified_claims}/{total_claims} verified "
            f"({overall_accuracy:.1%} accuracy), ${total_cost:.4f}"
        )

        return aggregate_results

    async def verify_single_claim(
        self,
        claim: str,
        sources: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify a single medical claim against sources

        Useful for:
        - Quick claim verification
        - User-submitted fact-checks
        - Real-time verification during editing

        Args:
            claim: The medical claim to verify
            sources: List of sources for verification
            context: Optional context about the claim

        Returns:
            Verification result with confidence and sources
        """
        logger.info(f"Verifying single claim: {claim[:60]}...")

        source_summary = self._build_source_summary(sources)

        prompt = f"""
        Verify this specific medical claim against the provided sources:

        **Claim**: {claim}
        """

        if context:
            prompt += f"\n**Context**: {context}"

        prompt += f"""

        **Available Sources**:
        {source_summary}

        Verify whether this claim is supported by the sources. Provide:
        1. Verification status (verified or not)
        2. Confidence score (0-1)
        3. Supporting source citation
        4. Claim category
        5. Severity if wrong
        6. Explanation notes
        """

        try:
            response = await self.ai_service.generate_text_with_schema(
                prompt=prompt,
                schema=FACT_CHECK_SCHEMA,
                task=AITask.FACT_CHECKING,
                max_tokens=800,
                temperature=0.2
            )

            result = response["data"]

            # Extract first claim (should only be one)
            if result["claims"]:
                claim_result = result["claims"][0]
                claim_result["ai_cost_usd"] = response["cost_usd"]
                claim_result["verified_at"] = datetime.utcnow().isoformat()
                return claim_result
            else:
                raise ValueError("No claim verification returned")

        except Exception as e:
            logger.error(f"Single claim verification failed: {str(e)}", exc_info=True)
            raise

    def _build_source_summary(
        self,
        sources: List[Dict[str, Any]],
        max_sources: int = 20
    ) -> str:
        """
        Build a formatted summary of sources for AI prompts

        Args:
            sources: List of source dictionaries
            max_sources: Maximum number of sources to include

        Returns:
            Formatted string of sources
        """
        if not sources:
            return "No sources available for verification."

        summary_lines = []
        for i, source in enumerate(sources[:max_sources], 1):
            title = source.get("title", "Unknown Title")
            authors = source.get("authors", [])
            year = source.get("year", "N/A")
            pmid = source.get("pmid", "")
            journal = source.get("journal", "")

            author_str = ", ".join(authors[:3]) if authors else "Unknown"
            if len(authors) > 3:
                author_str += " et al."

            source_line = f"{i}. {title}"
            if author_str:
                source_line += f" - {author_str}"
            if year:
                source_line += f" ({year})"
            if journal:
                source_line += f" - {journal}"
            if pmid:
                source_line += f" [PMID: {pmid}]"

            # Add abstract if available (truncated)
            abstract = source.get("abstract", "")
            if abstract:
                abstract_preview = abstract[:200] + "..." if len(abstract) > 200 else abstract
                source_line += f"\n   Abstract: {abstract_preview}"

            summary_lines.append(source_line)

        return "\n".join(summary_lines)

    def get_verification_summary(
        self,
        fact_check_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a human-readable summary of fact-check results

        Args:
            fact_check_results: Results from fact_check_section or fact_check_chapter

        Returns:
            Summary dictionary with key metrics and recommendations
        """
        claims = fact_check_results.get("claims", [])

        verified_count = sum(1 for c in claims if c["verified"])
        total_count = len(claims)
        accuracy = verified_count / total_count if total_count > 0 else 0.0

        # Group by category
        by_category = {}
        for claim in claims:
            category = claim.get("category", "other")
            if category not in by_category:
                by_category[category] = {"verified": 0, "unverified": 0}

            if claim["verified"]:
                by_category[category]["verified"] += 1
            else:
                by_category[category]["unverified"] += 1

        # Group unverified by severity
        unverified_by_severity = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        for claim in claims:
            if not claim["verified"]:
                severity = claim.get("severity_if_wrong", "low")
                unverified_by_severity[severity] += 1

        return {
            "total_claims": total_count,
            "verified": verified_count,
            "unverified": total_count - verified_count,
            "accuracy_percentage": accuracy * 100,
            "accuracy_grade": self._get_accuracy_grade(accuracy),
            "by_category": by_category,
            "unverified_by_severity": unverified_by_severity,
            "critical_issues": fact_check_results.get("critical_issues", []),
            "recommendations": fact_check_results.get("recommendations", []),
            "requires_attention": unverified_by_severity["critical"] > 0 or unverified_by_severity["high"] > 0
        }

    def _get_accuracy_grade(self, accuracy: float) -> str:
        """Convert accuracy score to letter grade"""
        if accuracy >= 0.95:
            return "A (Excellent)"
        elif accuracy >= 0.90:
            return "B (Good)"
        elif accuracy >= 0.80:
            return "C (Acceptable)"
        elif accuracy >= 0.70:
            return "D (Needs Improvement)"
        else:
            return "F (Poor - Requires Major Revision)"
