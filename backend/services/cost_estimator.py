"""
Cost Estimator Service
Estimates generation costs before creating a chapter
"""

import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CostEstimator:
    """
    Estimates chapter generation costs based on topic complexity and chapter type
    """

    # OpenAI GPT-4o pricing (as of 2025)
    GPT4O_INPUT_COST_PER_1K = 0.005  # $0.005 per 1K input tokens
    GPT4O_OUTPUT_COST_PER_1K = 0.015  # $0.015 per 1K output tokens

    # PubMed API is free
    PUBMED_COST = 0.0

    # Embedding costs (text-embedding-3-large)
    EMBEDDING_COST_PER_1K = 0.00013  # $0.00013 per 1K tokens

    # Stage-specific estimates (based on Phase 20 analytics)
    STAGE_TOKEN_ESTIMATES = {
        # Analysis stages
        "stage_1_analysis": {"input": 500, "output": 800},  # Topic analysis
        "stage_2_context": {"input": 2000, "output": 1500},  # Context building

        # Research stages
        "stage_3_internal": {"input": 1000, "output": 500},  # Internal search
        "stage_4_pubmed": {"input": 800, "output": 600},  # PubMed search
        "stage_4_ai_research": {"input": 1500, "output": 1200},  # AI research

        # Planning stage
        "stage_5_synthesis": {"input": 3000, "output": 2000},  # Synthesis planning

        # Content generation (per section)
        "stage_6_section": {"input": 2500, "output": 2000},  # Section generation

        # Enhancement stages
        "stage_7_images": {"input": 500, "output": 300},  # Image integration
        "stage_8_citations": {"input": 1000, "output": 800},  # Citation network
        "stage_9_qa": {"input": 2000, "output": 1500},  # Quality assurance
        "stage_10_fact_check": {"input": 3000, "output": 2500},  # Fact-checking

        # Finalization stages
        "stage_11_formatting": {"input": 1500, "output": 1000},  # Formatting
        "stage_12_review": {"input": 2500, "output": 2000},  # Review
        "stage_13_finalization": {"input": 1000, "output": 500},  # Finalization
    }

    # Chapter type complexity multipliers
    COMPLEXITY_MULTIPLIERS = {
        "surgical_disease": 1.0,  # Baseline
        "pure_anatomy": 0.8,  # Simpler, more standardized
        "surgical_technique": 1.2,  # More detailed, step-by-step
        "pathophysiology": 1.1,  # Complex mechanisms
        "clinical_case": 0.9,  # Structured format
        "review": 1.3,  # Comprehensive, many sources
    }

    # Expected section counts by chapter type
    EXPECTED_SECTIONS = {
        "surgical_disease": 7,  # Introduction, Epidemiology, Pathophysiology, Clinical, Diagnosis, Treatment, Outcomes
        "pure_anatomy": 5,  # Overview, Structure, Relations, Variations, Clinical
        "surgical_technique": 6,  # Indications, Preparation, Steps, Complications, Outcomes, Alternatives
        "pathophysiology": 6,  # Introduction, Mechanisms, Manifestations, Diagnosis, Treatment, Summary
        "clinical_case": 4,  # Presentation, Workup, Management, Outcome
        "review": 8,  # Multiple comprehensive sections
    }

    def estimate_cost(
        self,
        topic: str,
        chapter_type: Optional[str] = None
    ) -> Dict:
        """
        Estimate generation cost for a chapter

        Args:
            topic: Chapter topic
            chapter_type: Type of chapter (surgical_disease, pure_anatomy, etc.)

        Returns:
            Dictionary with cost estimate and breakdown
        """
        logger.info(f"Estimating cost for topic: {topic}, type: {chapter_type}")

        # Determine chapter type if not provided
        if not chapter_type:
            chapter_type = self._infer_chapter_type(topic)

        # Get complexity multiplier
        complexity = self.COMPLEXITY_MULTIPLIERS.get(chapter_type, 1.0)

        # Get expected section count
        section_count = self.EXPECTED_SECTIONS.get(chapter_type, 7)

        # Calculate stage costs
        stage_costs = {}

        # Analysis stages (fixed cost)
        stage_costs["analysis"] = self._calculate_stage_cost("stage_1_analysis", complexity)
        stage_costs["context_building"] = self._calculate_stage_cost("stage_2_context", complexity)

        # Research stages (fixed cost)
        stage_costs["internal_research"] = self._calculate_stage_cost("stage_3_internal", complexity)
        stage_costs["pubmed_research"] = self.PUBMED_COST  # Free
        stage_costs["ai_research"] = self._calculate_stage_cost("stage_4_ai_research", complexity)

        # Planning (fixed cost)
        stage_costs["synthesis_planning"] = self._calculate_stage_cost("stage_5_synthesis", complexity)

        # Content generation (scales with sections)
        section_cost = self._calculate_stage_cost("stage_6_section", complexity)
        stage_costs["content_generation"] = section_cost * section_count

        # Enhancement stages (fixed cost)
        stage_costs["image_integration"] = self._calculate_stage_cost("stage_7_images", complexity)
        stage_costs["citation_network"] = self._calculate_stage_cost("stage_8_citations", complexity)
        stage_costs["quality_assurance"] = self._calculate_stage_cost("stage_9_qa", complexity)
        stage_costs["fact_checking"] = self._calculate_stage_cost("stage_10_fact_check", complexity)

        # Finalization stages (fixed cost)
        stage_costs["formatting"] = self._calculate_stage_cost("stage_11_formatting", complexity)
        stage_costs["review_refinement"] = self._calculate_stage_cost("stage_12_review", complexity)
        stage_costs["finalization"] = self._calculate_stage_cost("stage_13_finalization", complexity)

        # Embedding costs (for vector search)
        stage_costs["embeddings"] = self._estimate_embedding_cost(section_count)

        # Calculate total
        total_cost = sum(stage_costs.values())

        # Estimate duration (based on analytics: average 120-180 seconds)
        base_duration = 150  # seconds
        duration_seconds = int(base_duration * complexity * (section_count / 7))

        # Add buffer for variability (10%)
        total_cost_with_buffer = total_cost * 1.1

        # Categorize costs
        categorized_costs = {
            "analysis_research": (
                stage_costs["analysis"] +
                stage_costs["context_building"] +
                stage_costs["internal_research"] +
                stage_costs["pubmed_research"] +
                stage_costs["ai_research"]
            ),
            "content_generation": stage_costs["content_generation"],
            "quality_enhancement": (
                stage_costs["quality_assurance"] +
                stage_costs["fact_checking"] +
                stage_costs["review_refinement"]
            ),
            "finalization": (
                stage_costs["synthesis_planning"] +
                stage_costs["image_integration"] +
                stage_costs["citation_network"] +
                stage_costs["formatting"] +
                stage_costs["finalization"] +
                stage_costs["embeddings"]
            )
        }

        result = {
            "estimated_cost_usd": round(total_cost_with_buffer, 4),
            "estimated_cost_base_usd": round(total_cost, 4),
            "buffer_percentage": 10,
            "breakdown_by_stage": {k: round(v, 4) for k, v in stage_costs.items()},
            "breakdown_by_category": {k: round(v, 4) for k, v in categorized_costs.items()},
            "estimated_duration_seconds": duration_seconds,
            "estimated_duration_minutes": round(duration_seconds / 60, 1),
            "chapter_type": chapter_type,
            "complexity_multiplier": complexity,
            "expected_sections": section_count,
            "topic": topic,
            "estimated_at": datetime.utcnow().isoformat(),
            "notes": [
                "Estimate includes 10% buffer for variability",
                "Actual cost may vary based on available research sources",
                f"Assumes {section_count} sections based on chapter type",
                "PubMed API is free (no cost)",
                "Duration assumes no API rate limiting"
            ]
        }

        logger.info(
            f"Cost estimate for '{topic}': ${total_cost_with_buffer:.4f} "
            f"({duration_seconds}s, {section_count} sections)"
        )

        return result

    def _calculate_stage_cost(self, stage_key: str, complexity: float) -> float:
        """
        Calculate cost for a single stage

        Args:
            stage_key: Stage identifier
            complexity: Complexity multiplier

        Returns:
            Estimated cost in USD
        """
        if stage_key not in self.STAGE_TOKEN_ESTIMATES:
            return 0.0

        estimates = self.STAGE_TOKEN_ESTIMATES[stage_key]
        input_tokens = estimates["input"] * complexity
        output_tokens = estimates["output"] * complexity

        input_cost = (input_tokens / 1000) * self.GPT4O_INPUT_COST_PER_1K
        output_cost = (output_tokens / 1000) * self.GPT4O_OUTPUT_COST_PER_1K

        return input_cost + output_cost

    def _estimate_embedding_cost(self, section_count: int) -> float:
        """
        Estimate embedding generation costs

        Args:
            section_count: Number of sections

        Returns:
            Estimated cost in USD
        """
        # Each section generates ~1 embedding
        # Average section length ~500 tokens
        tokens_per_section = 500
        total_tokens = tokens_per_section * section_count

        return (total_tokens / 1000) * self.EMBEDDING_COST_PER_1K

    def _infer_chapter_type(self, topic: str) -> str:
        """
        Infer chapter type from topic keywords

        Args:
            topic: Chapter topic string

        Returns:
            Inferred chapter type
        """
        topic_lower = topic.lower()

        # Keywords for each type
        if any(word in topic_lower for word in ["anatomy", "anatomical", "structure", "relations"]):
            return "pure_anatomy"
        elif any(word in topic_lower for word in ["technique", "procedure", "approach", "surgical method"]):
            return "surgical_technique"
        elif any(word in topic_lower for word in ["pathophysiology", "mechanism", "pathogenesis"]):
            return "pathophysiology"
        elif any(word in topic_lower for word in ["case", "patient", "presentation"]):
            return "clinical_case"
        elif any(word in topic_lower for word in ["review", "overview", "comprehensive"]):
            return "review"
        else:
            # Default to surgical_disease
            return "surgical_disease"

    def compare_costs(
        self,
        topic: str,
        chapter_types: Optional[list] = None
    ) -> Dict:
        """
        Compare costs across different chapter types

        Args:
            topic: Chapter topic
            chapter_types: List of chapter types to compare

        Returns:
            Dictionary with comparison data
        """
        if not chapter_types:
            chapter_types = list(self.COMPLEXITY_MULTIPLIERS.keys())

        comparisons = {}

        for chapter_type in chapter_types:
            estimate = self.estimate_cost(topic, chapter_type)
            comparisons[chapter_type] = {
                "cost": estimate["estimated_cost_usd"],
                "duration_minutes": estimate["estimated_duration_minutes"],
                "sections": estimate["expected_sections"],
                "complexity": estimate["complexity_multiplier"]
            }

        # Find cheapest and most expensive
        sorted_by_cost = sorted(comparisons.items(), key=lambda x: x[1]["cost"])

        return {
            "topic": topic,
            "comparisons": comparisons,
            "cheapest": {
                "type": sorted_by_cost[0][0],
                "cost": sorted_by_cost[0][1]["cost"]
            },
            "most_expensive": {
                "type": sorted_by_cost[-1][0],
                "cost": sorted_by_cost[-1][1]["cost"]
            },
            "cost_range": {
                "min_usd": sorted_by_cost[0][1]["cost"],
                "max_usd": sorted_by_cost[-1][1]["cost"],
                "difference_usd": round(sorted_by_cost[-1][1]["cost"] - sorted_by_cost[0][1]["cost"], 4)
            }
        }

    def get_pricing_info(self) -> Dict:
        """
        Get current pricing information

        Returns:
            Dictionary with pricing details
        """
        return {
            "model": "GPT-4o",
            "pricing": {
                "input_tokens_per_1k": f"${self.GPT4O_INPUT_COST_PER_1K}",
                "output_tokens_per_1k": f"${self.GPT4O_OUTPUT_COST_PER_1K}",
                "embeddings_per_1k": f"${self.EMBEDDING_COST_PER_1K}",
                "pubmed_api": "Free"
            },
            "typical_chapter_costs": {
                "simple_anatomy": "$0.25 - $0.35",
                "standard_disease": "$0.45 - $0.65",
                "complex_review": "$0.75 - $1.00",
                "surgical_technique": "$0.55 - $0.80"
            },
            "cost_factors": [
                "Chapter type and complexity",
                "Number of sections",
                "Available research sources",
                "Quality assurance depth",
                "Fact-checking thoroughness"
            ],
            "notes": [
                "Costs are estimates based on typical usage",
                "Actual costs may vary by ±20%",
                "PubMed research is free (no API costs)",
                "Internal PDF search is free (using pgvector)"
            ]
        }
