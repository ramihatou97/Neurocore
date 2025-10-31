"""
Gap Analyzer Service - Identifies missing or incomplete content in generated chapters

Phase 2 Week 5: Gap Analysis Feature
Analyzes chapters against research sources and identified gaps to ensure comprehensive coverage
Provides actionable recommendations for improvement
"""

import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from collections import defaultdict

from backend.services.ai_provider_service import AIProviderService, AITask
from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class GapAnalyzer:
    """
    Service for analyzing content gaps in generated chapters

    Analysis Categories:
    1. Content Completeness - Missing key concepts from Stage 2 context
    2. Source Coverage - Unused high-value research sources
    3. Section Balance - Uneven depth across sections
    4. Temporal Coverage - Missing recent developments
    5. Critical Information - Missing essential clinical/surgical details
    """

    def __init__(self):
        """Initialize gap analyzer"""
        self.ai_service = AIProviderService()

    async def analyze_chapter_gaps(
        self,
        chapter: Dict[str, Any],
        internal_sources: List[Dict[str, Any]],
        external_sources: List[Dict[str, Any]],
        stage_2_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comprehensive gap analysis for a chapter

        Phase 2 Week 5: Multi-dimensional gap detection

        Args:
            chapter: Chapter data with sections and metadata
            internal_sources: Internal research sources
            external_sources: External research sources
            stage_2_context: Context from Stage 2 (research gaps, key references)

        Returns:
            Comprehensive gap analysis results with recommendations
        """
        logger.info(f"Analyzing gaps for chapter: {chapter.get('title', 'N/A')}")

        # Initialize gap analysis results
        gap_analysis = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "chapter_title": chapter.get("title"),
            "total_sections": len(chapter.get("sections", [])),
            "gaps_identified": [],
            "recommendations": [],
            "severity_distribution": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "gap_categories": {
                "content_completeness": [],
                "source_coverage": [],
                "section_balance": [],
                "temporal_coverage": [],
                "critical_information": []
            },
            "overall_completeness_score": 0.0,
            "requires_revision": False
        }

        # Run all gap detection analyses in parallel
        analyses = await asyncio.gather(
            self._analyze_content_completeness(chapter, stage_2_context),
            self._analyze_source_coverage(chapter, internal_sources, external_sources),
            self._analyze_section_balance(chapter),
            self._analyze_temporal_coverage(chapter, external_sources),
            self._analyze_critical_information(chapter, stage_2_context),
            return_exceptions=True
        )

        # Merge results from all analyses
        all_gaps = []

        for i, analysis in enumerate(analyses):
            if isinstance(analysis, Exception):
                logger.error(f"Gap analysis {i} failed: {analysis}")
                continue

            if analysis and "gaps" in analysis:
                all_gaps.extend(analysis["gaps"])
                category = analysis.get("category", "unknown")
                gap_analysis["gap_categories"][category] = analysis["gaps"]

        # Sort gaps by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_gaps.sort(key=lambda x: severity_order.get(x["severity"], 4))

        # Update severity distribution
        for gap in all_gaps:
            severity = gap["severity"]
            gap_analysis["severity_distribution"][severity] += 1

        gap_analysis["gaps_identified"] = all_gaps
        gap_analysis["total_gaps"] = len(all_gaps)

        # Generate AI-powered recommendations
        recommendations = await self._generate_recommendations(chapter, all_gaps, stage_2_context)
        gap_analysis["recommendations"] = recommendations

        # Calculate overall completeness score (0-1)
        completeness_score = self._calculate_completeness_score(all_gaps, chapter)
        gap_analysis["overall_completeness_score"] = completeness_score

        # Determine if revision is required
        critical_gaps = gap_analysis["severity_distribution"]["critical"]
        high_gaps = gap_analysis["severity_distribution"]["high"]
        gap_analysis["requires_revision"] = (
            critical_gaps > 0 or
            high_gaps > 2 or
            completeness_score < 0.75
        )

        logger.info(
            f"Gap analysis complete: {len(all_gaps)} gaps identified "
            f"(Critical: {critical_gaps}, High: {high_gaps}), "
            f"Completeness: {completeness_score:.1%}"
        )

        return gap_analysis

    async def _analyze_content_completeness(
        self,
        chapter: Dict[str, Any],
        stage_2_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze if all key concepts from Stage 2 are covered

        Compares chapter content against:
        - Research gaps identified in Stage 2
        - Key references expected
        - Primary concepts

        Returns:
            Analysis results with identified gaps
        """
        logger.debug("Analyzing content completeness...")

        gaps = []
        context = stage_2_context.get("context", {})
        research_gaps = context.get("research_gaps", [])
        key_references = context.get("key_references", [])

        sections = chapter.get("sections", [])
        section_text = " ".join([s.get("content", "") for s in sections]).lower()

        # Check if research gaps were addressed
        for gap in research_gaps:
            gap_topic = gap.get("gap_description", "").lower()
            gap_severity = gap.get("severity", "medium")

            # Simple check: is gap topic mentioned in chapter?
            # In production, use semantic similarity
            key_terms = [term.strip() for term in gap_topic.split() if len(term) > 4][:3]

            if key_terms and not any(term in section_text for term in key_terms):
                gaps.append({
                    "type": "missing_research_gap",
                    "severity": self._map_gap_severity_to_analysis(gap_severity),
                    "description": f"Research gap not addressed: {gap.get('gap_description', 'Unknown gap')[:100]}",
                    "affected_sections": gap.get("affected_sections", []),
                    "recommendation": f"Add content addressing: {gap_topic[:100]}"
                })

        # Check key references coverage
        missing_refs_count = 0
        for ref in key_references:
            ref_topic = ref.get("reference_topic", "").lower()
            key_findings = ref.get("key_findings", "").lower()

            # Check if reference topic or findings are discussed
            if ref_topic and len(ref_topic) > 4:
                if ref_topic not in section_text and (not key_findings or key_findings not in section_text):
                    missing_refs_count += 1

        if missing_refs_count > 0:
            severity = "high" if missing_refs_count > 3 else "medium"
            gaps.append({
                "type": "missing_key_references",
                "severity": severity,
                "description": f"{missing_refs_count} key references not adequately covered",
                "recommendation": "Incorporate findings from missing key references"
            })

        return {
            "category": "content_completeness",
            "gaps": gaps
        }

    async def _analyze_source_coverage(
        self,
        chapter: Dict[str, Any],
        internal_sources: List[Dict[str, Any]],
        external_sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze if high-value sources were adequately used

        Identifies:
        - High-relevance sources not cited
        - Recent high-impact papers not mentioned
        - Imbalanced source usage

        Returns:
            Analysis results with source coverage gaps
        """
        logger.debug("Analyzing source coverage...")

        gaps = []
        sections = chapter.get("sections", [])
        section_text = " ".join([s.get("content", "") for s in sections]).lower()

        # Combine all sources
        all_sources = internal_sources + external_sources

        # Find high-value sources not used
        unused_high_value = []

        for source in all_sources:
            # High-value criteria
            relevance = source.get("relevance_score", 0) or source.get("ai_relevance_score", 0)

            if relevance and relevance > 0.85:
                # Check if source is cited (look for title keywords, DOI, or PMID)
                title = source.get("title", "").lower()
                doi = source.get("doi", "")
                pmid = source.get("pmid", "")

                # Simple citation check
                title_words = [w for w in title.split() if len(w) > 4][:3]
                is_cited = (
                    any(word in section_text for word in title_words) or
                    (doi and doi in section_text) or
                    (pmid and str(pmid) in section_text)
                )

                if not is_cited:
                    unused_high_value.append(source)

        # Report unused high-value sources
        if len(unused_high_value) > 0:
            # Take top 5 most relevant
            unused_high_value.sort(key=lambda x: x.get("relevance_score", 0) or x.get("ai_relevance_score", 0), reverse=True)
            top_unused = unused_high_value[:5]

            severity = "high" if len(unused_high_value) > 5 else "medium"

            for source in top_unused:
                gaps.append({
                    "type": "unused_high_value_source",
                    "severity": severity,
                    "description": f"High-relevance source not cited: {source.get('title', 'Unknown')[:80]}",
                    "source_id": source.get("pdf_id") or source.get("pmid"),
                    "relevance_score": source.get("relevance_score") or source.get("ai_relevance_score"),
                    "recommendation": f"Consider citing: {source.get('title', '')[:100]}"
                })

        # Check source diversity (internal vs external balance)
        if len(all_sources) > 0:
            external_ratio = len(external_sources) / len(all_sources)

            if external_ratio < 0.2:
                gaps.append({
                    "type": "low_external_sources",
                    "severity": "medium",
                    "description": f"Only {external_ratio:.0%} external sources - may lack recent research",
                    "recommendation": "Incorporate more recent PubMed research"
                })
            elif external_ratio > 0.8:
                gaps.append({
                    "type": "low_internal_sources",
                    "severity": "low",
                    "description": f"Only {100-external_ratio*100:.0%} internal sources - may lack depth",
                    "recommendation": "Consider referencing more indexed literature"
                })

        return {
            "category": "source_coverage",
            "gaps": gaps
        }

    async def _analyze_section_balance(
        self,
        chapter: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze section depth balance

        Identifies:
        - Sections that are too short/long
        - Uneven depth distribution
        - Missing critical sections

        Returns:
            Analysis results with balance gaps
        """
        logger.debug("Analyzing section balance...")

        gaps = []
        sections = chapter.get("sections", [])

        if not sections:
            return {"category": "section_balance", "gaps": []}

        # Calculate word counts
        word_counts = [s.get("word_count", len(s.get("content", "").split())) for s in sections]

        if not word_counts:
            return {"category": "section_balance", "gaps": []}

        avg_words = sum(word_counts) / len(word_counts)
        min_words = min(word_counts)
        max_words = max(word_counts)

        # Find very short sections (< 40% of average)
        short_threshold = avg_words * 0.4
        short_sections = [(i, count) for i, count in enumerate(word_counts) if count < short_threshold]

        if short_sections:
            for section_num, word_count in short_sections:
                section_title = sections[section_num].get("title", f"Section {section_num+1}")
                gaps.append({
                    "type": "underdeveloped_section",
                    "severity": "medium",
                    "description": f"Section '{section_title}' is underdeveloped ({word_count} words vs {avg_words:.0f} avg)",
                    "section_number": section_num + 1,
                    "recommendation": f"Expand section '{section_title}' with more detail"
                })

        # Find very long sections (> 250% of average)
        long_threshold = avg_words * 2.5
        long_sections = [(i, count) for i, count in enumerate(word_counts) if count > long_threshold]

        if long_sections:
            for section_num, word_count in long_sections:
                section_title = sections[section_num].get("title", f"Section {section_num+1}")
                gaps.append({
                    "type": "oversized_section",
                    "severity": "low",
                    "description": f"Section '{section_title}' may be too long ({word_count} words vs {avg_words:.0f} avg)",
                    "section_number": section_num + 1,
                    "recommendation": f"Consider splitting '{section_title}' into subsections"
                })

        # Check for very high variance (uneven balance)
        if len(word_counts) > 2:
            variance = sum((x - avg_words) ** 2 for x in word_counts) / len(word_counts)
            std_dev = variance ** 0.5
            coefficient_of_variation = std_dev / avg_words if avg_words > 0 else 0

            if coefficient_of_variation > 0.6:  # High variability
                gaps.append({
                    "type": "uneven_section_balance",
                    "severity": "medium",
                    "description": f"High variability in section lengths (CV: {coefficient_of_variation:.2f})",
                    "recommendation": "Rebalance sections for more consistent depth"
                })

        return {
            "category": "section_balance",
            "gaps": gaps
        }

    async def _analyze_temporal_coverage(
        self,
        chapter: Dict[str, Any],
        external_sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze temporal coverage of sources

        Identifies:
        - Missing recent developments (last 1-2 years)
        - Over-reliance on outdated sources
        - Gaps in temporal distribution

        Returns:
            Analysis results with temporal gaps
        """
        logger.debug("Analyzing temporal coverage...")

        gaps = []
        current_year = datetime.now().year

        if not external_sources:
            gaps.append({
                "type": "no_recent_sources",
                "severity": "high",
                "description": "No external sources available for temporal analysis",
                "recommendation": "Add recent PubMed research"
            })
            return {"category": "temporal_coverage", "gaps": gaps}

        # Analyze year distribution
        years = [s.get("year") for s in external_sources if s.get("year")]

        if not years:
            gaps.append({
                "type": "no_year_data",
                "severity": "medium",
                "description": "Source publication years not available",
                "recommendation": "Verify source metadata includes publication years"
            })
            return {"category": "temporal_coverage", "gaps": gaps}

        most_recent = max(years)
        oldest = min(years)

        # Check for recent sources (last 2 years)
        recent_sources = [y for y in years if y >= current_year - 2]

        if len(recent_sources) == 0:
            gaps.append({
                "type": "no_recent_sources",
                "severity": "high",
                "description": f"No sources from last 2 years (most recent: {most_recent})",
                "recommendation": "Add recent research from 2023-2025"
            })
        elif len(recent_sources) < len(years) * 0.2:  # Less than 20% are recent
            gaps.append({
                "type": "insufficient_recent_sources",
                "severity": "medium",
                "description": f"Only {len(recent_sources)} sources from last 2 years ({len(recent_sources)/len(years)*100:.0f}%)",
                "recommendation": "Increase proportion of recent research"
            })

        # Check for outdated sources (> 10 years old)
        outdated_threshold = current_year - 10
        outdated_sources = [y for y in years if y < outdated_threshold]

        if len(outdated_sources) > len(years) * 0.5:  # More than 50% outdated
            gaps.append({
                "type": "outdated_sources_dominant",
                "severity": "medium",
                "description": f"{len(outdated_sources)} sources older than 10 years ({len(outdated_sources)/len(years)*100:.0f}%)",
                "recommendation": "Update with more recent literature"
            })

        return {
            "category": "temporal_coverage",
            "gaps": gaps
        }

    async def _analyze_critical_information(
        self,
        chapter: Dict[str, Any],
        stage_2_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze presence of critical clinical/surgical information

        Uses AI to identify missing essential content based on chapter type

        Returns:
            Analysis results with critical information gaps
        """
        logger.debug("Analyzing critical information coverage...")

        gaps = []
        chapter_type = chapter.get("chapter_type", "surgical_disease")
        chapter_title = chapter.get("title", "")
        sections = chapter.get("sections", [])

        if not sections:
            return {"category": "critical_information", "gaps": []}

        # Build content summary
        content_summary = "\n".join([
            f"{s.get('title', 'Untitled')}: {s.get('content', '')[:200]}..."
            for s in sections[:10]  # First 10 sections
        ])

        # Use AI to identify missing critical information
        prompt = f"""Analyze this neurosurgery chapter for missing critical information.

Chapter Title: "{chapter_title}"
Chapter Type: {chapter_type}
Number of Sections: {len(sections)}

Section Summary:
{content_summary}

Task: Identify any CRITICAL information that appears to be missing based on the chapter type and topic.

For {chapter_type} chapters on "{chapter_title}", essential content typically includes:
- Anatomical considerations (if applicable)
- Pathophysiology (for disease chapters)
- Diagnostic criteria
- Treatment options/surgical techniques
- Complications and management
- Outcomes and prognosis

List ONLY truly critical gaps (3-5 maximum). For each gap:
1. What critical information is missing
2. Why it's essential for this chapter type
3. Which section should include it

Format as JSON array:
[{{"gap": "description", "severity": "critical/high", "missing_topic": "topic", "should_be_in": "section name"}}]

Return ONLY the JSON array, no other text.
"""

        try:
            response = await self.ai_service.generate_text(
                prompt=prompt,
                max_tokens=800,
                temperature=0.2,
                model_type="fast"
            )

            # Parse AI response
            import json
            ai_gaps = json.loads(response["content"].strip())

            for ai_gap in ai_gaps:
                gaps.append({
                    "type": "missing_critical_information",
                    "severity": ai_gap.get("severity", "high"),
                    "description": ai_gap.get("gap", "Unknown gap"),
                    "missing_topic": ai_gap.get("missing_topic", ""),
                    "should_be_in": ai_gap.get("should_be_in", ""),
                    "recommendation": f"Add content about: {ai_gap.get('missing_topic', '')}"
                })

        except Exception as e:
            logger.warning(f"AI critical information analysis failed: {e}")
            # Fallback: basic checks
            content_lower = content_summary.lower()

            if chapter_type == "surgical_disease":
                if "complication" not in content_lower:
                    gaps.append({
                        "type": "missing_critical_information",
                        "severity": "high",
                        "description": "Complications section may be missing or incomplete",
                        "recommendation": "Add comprehensive complications coverage"
                    })

        return {
            "category": "critical_information",
            "gaps": gaps
        }

    async def _generate_recommendations(
        self,
        chapter: Dict[str, Any],
        gaps: List[Dict[str, Any]],
        stage_2_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate actionable recommendations based on identified gaps

        Returns:
            List of prioritized recommendations
        """
        recommendations = []

        # Group gaps by severity
        critical_gaps = [g for g in gaps if g["severity"] == "critical"]
        high_gaps = [g for g in gaps if g["severity"] == "high"]

        # Priority 1: Address critical gaps
        if critical_gaps:
            recommendations.append({
                "priority": 1,
                "action": "address_critical_gaps",
                "description": f"Immediately address {len(critical_gaps)} critical gaps",
                "gaps_count": len(critical_gaps),
                "estimated_effort": "high",
                "affected_sections": list(set([
                    g.get("section_number", 0)
                    for g in critical_gaps
                    if g.get("section_number")
                ]))
            })

        # Priority 2: Add missing high-value sources
        unused_sources = [g for g in gaps if g["type"] == "unused_high_value_source"]
        if unused_sources:
            recommendations.append({
                "priority": 2,
                "action": "cite_missing_sources",
                "description": f"Cite {len(unused_sources)} high-relevance sources",
                "sources_to_add": [g.get("source_id") for g in unused_sources if g.get("source_id")],
                "estimated_effort": "medium"
            })

        # Priority 3: Expand underdeveloped sections
        short_sections = [g for g in gaps if g["type"] == "underdeveloped_section"]
        if short_sections:
            recommendations.append({
                "priority": 3,
                "action": "expand_sections",
                "description": f"Expand {len(short_sections)} underdeveloped sections",
                "sections_to_expand": [g.get("section_number") for g in short_sections],
                "estimated_effort": "medium"
            })

        # Priority 4: Update with recent research
        temporal_gaps = [g for g in gaps if "recent" in g["type"].lower()]
        if temporal_gaps:
            recommendations.append({
                "priority": 4,
                "action": "add_recent_research",
                "description": "Incorporate recent research (2023-2025)",
                "estimated_effort": "low"
            })

        return recommendations

    def _calculate_completeness_score(
        self,
        gaps: List[Dict[str, Any]],
        chapter: Dict[str, Any]
    ) -> float:
        """
        Calculate overall completeness score (0-1)

        Weighted by gap severity:
        - Critical: -0.15
        - High: -0.08
        - Medium: -0.04
        - Low: -0.02

        Returns:
            Completeness score (0-1, higher is better)
        """
        base_score = 1.0

        severity_weights = {
            "critical": 0.15,
            "high": 0.08,
            "medium": 0.04,
            "low": 0.02
        }

        for gap in gaps:
            severity = gap.get("severity", "low")
            weight = severity_weights.get(severity, 0.02)
            base_score -= weight

        # Clamp to [0, 1]
        return max(0.0, min(1.0, base_score))

    def _map_gap_severity_to_analysis(self, gap_severity: str) -> str:
        """Map Stage 2 gap severity to analysis severity"""
        severity_map = {
            "high": "critical",
            "medium": "high",
            "low": "medium"
        }
        return severity_map.get(gap_severity.lower(), "medium")

    def get_gap_summary(self, gap_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a concise summary of gap analysis results

        Args:
            gap_analysis: Full gap analysis results

        Returns:
            Concise summary dictionary
        """
        return {
            "total_gaps": gap_analysis.get("total_gaps", 0),
            "critical_gaps": gap_analysis.get("severity_distribution", {}).get("critical", 0),
            "high_gaps": gap_analysis.get("severity_distribution", {}).get("high", 0),
            "completeness_score": gap_analysis.get("overall_completeness_score", 0.0),
            "requires_revision": gap_analysis.get("requires_revision", False),
            "top_recommendations": gap_analysis.get("recommendations", [])[:3],
            "analyzed_at": gap_analysis.get("analyzed_at")
        }
