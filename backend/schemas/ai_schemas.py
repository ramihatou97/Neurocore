"""
AI JSON Schemas for Structured Outputs

This module contains all JSON schemas used with GPT-4o's structured outputs feature.
These schemas guarantee valid, type-safe responses from the AI with zero parsing errors.

Usage:
    from backend.schemas.ai_schemas import CHAPTER_ANALYSIS_SCHEMA

    result = await ai_service.generate_text_with_schema(
        prompt=prompt,
        schema=CHAPTER_ANALYSIS_SCHEMA,
        task=AITask.METADATA_EXTRACTION
    )

    # result['data'] is guaranteed to match the schema
    analysis = result['data']
    chapter_type = analysis['chapter_type']  # Always valid, no try/catch needed
"""

from typing import Dict, Any


# ============================================================================
# CHAPTER ANALYSIS SCHEMA (Stage 1: Input Validation)
# ============================================================================

CHAPTER_ANALYSIS_SCHEMA = {
    "name": "chapter_analysis",
    "strict": True,  # Enforce strict schema validation
    "schema": {
        "type": "object",
        "properties": {
            "primary_concepts": {
                "type": "array",
                "description": "Main neurosurgical concepts covered in this chapter",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 10
            },
            "chapter_type": {
                "type": "string",
                "description": "Classification of chapter content type",
                "enum": ["surgical_disease", "pure_anatomy", "surgical_technique"]
            },
            "keywords": {
                "type": "array",
                "description": "Medical keywords and terms for indexing",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 20
            },
            "complexity": {
                "type": "string",
                "description": "Target audience complexity level",
                "enum": ["beginner", "intermediate", "advanced", "expert"]
            },
            "anatomical_regions": {
                "type": "array",
                "description": "Brain regions or anatomical areas involved",
                "items": {"type": "string"}
            },
            "surgical_approaches": {
                "type": "array",
                "description": "Surgical approaches or techniques mentioned",
                "items": {"type": "string"}
            },
            "estimated_section_count": {
                "type": "integer",
                "description": "Recommended number of sections for this chapter",
                "minimum": 10,
                "maximum": 150
            },
            "analysis_confidence": {
                "type": "number",
                "description": "Confidence in the chapter analysis and classification (0-1)",
                "minimum": 0,
                "maximum": 1
            }
        },
        "required": [
            "primary_concepts",
            "chapter_type",
            "keywords",
            "complexity",
            "anatomical_regions",
            "surgical_approaches",
            "estimated_section_count",
            "analysis_confidence"
        ],
        "additionalProperties": False
    }
}


# ============================================================================
# CONTEXT BUILDING SCHEMA (Stage 2: Research Context)
# ============================================================================

CONTEXT_BUILDING_SCHEMA = {
    "name": "research_context",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "research_gaps": {
                "type": "array",
                "description": "Identified gaps in current research or knowledge",
                "items": {
                    "type": "object",
                    "properties": {
                        "gap_description": {"type": "string"},
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "affected_sections": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["gap_description", "severity", "affected_sections"],
                    "additionalProperties": False
                }
            },
            "key_references": {
                "type": "array",
                "description": "Most important reference sources identified",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
                        "key_findings": {"type": "string"},
                        "pmid": {"type": "string"}
                    },
                    "required": ["title", "relevance_score", "key_findings", "pmid"],
                    "additionalProperties": False
                },
                "maxItems": 20
            },
            "content_categories": {
                "type": "object",
                "description": "Categorization of available content by type",
                "properties": {
                    "clinical_studies": {"type": "integer", "minimum": 0},
                    "case_reports": {"type": "integer", "minimum": 0},
                    "review_articles": {"type": "integer", "minimum": 0},
                    "basic_science": {"type": "integer", "minimum": 0},
                    "imaging_data": {"type": "integer", "minimum": 0}
                },
                "required": ["clinical_studies", "case_reports", "review_articles", "basic_science", "imaging_data"],
                "additionalProperties": False
            },
            "temporal_coverage": {
                "type": "object",
                "description": "Time range of research sources",
                "properties": {
                    "oldest_year": {"type": "integer", "minimum": 1900, "maximum": 2030},
                    "newest_year": {"type": "integer", "minimum": 1900, "maximum": 2030},
                    "median_year": {"type": "integer", "minimum": 1900, "maximum": 2030}
                },
                "required": ["oldest_year", "newest_year", "median_year"],
                "additionalProperties": False
            },
            "confidence_assessment": {
                "type": "object",
                "description": "Overall confidence in available research",
                "properties": {
                    "overall_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "evidence_quality": {"type": "string", "enum": ["high", "moderate", "low", "very_low"]},
                    "completeness": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["overall_confidence", "evidence_quality", "completeness"],
                "additionalProperties": False
            }
        },
        "required": [
            "research_gaps",
            "key_references",
            "content_categories",
            "temporal_coverage",
            "confidence_assessment"
        ],
        "additionalProperties": False
    }
}


# ============================================================================
# FACT-CHECKING SCHEMA (Stage 10: Medical Verification)
# ============================================================================

FACT_CHECK_SCHEMA = {
    "name": "fact_check_results",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "description": "Individual medical claims and their verification status",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {
                            "type": "string",
                            "description": "The specific medical claim being verified"
                        },
                        "verified": {
                            "type": "boolean",
                            "description": "Whether the claim is verified by sources"
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Confidence level in verification (0-1)",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "source_pmid": {
                            "type": "string",
                            "description": "PubMed ID of supporting source, if available"
                        },
                        "source_citation": {
                            "type": "string",
                            "description": "Citation of the supporting source"
                        },
                        "category": {
                            "type": "string",
                            "description": "Type of medical claim",
                            "enum": [
                                "anatomy",
                                "pathophysiology",
                                "diagnosis",
                                "treatment",
                                "prognosis",
                                "epidemiology",
                                "surgical_technique",
                                "complications"
                            ]
                        },
                        "severity_if_wrong": {
                            "type": "string",
                            "description": "Impact if this claim is incorrect",
                            "enum": ["critical", "high", "medium", "low"]
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes or context about verification"
                        }
                    },
                    "required": [
                        "claim",
                        "verified",
                        "confidence",
                        "source_pmid",
                        "source_citation",
                        "category",
                        "severity_if_wrong",
                        "notes"
                    ],
                    "additionalProperties": False
                },
                "minItems": 1
            },
            "overall_accuracy": {
                "type": "number",
                "description": "Overall accuracy score (0-1) based on all claims",
                "minimum": 0,
                "maximum": 1
            },
            "unverified_count": {
                "type": "integer",
                "description": "Number of claims that could not be verified",
                "minimum": 0
            },
            "critical_issues": {
                "type": "array",
                "description": "List of critical issues that need immediate attention",
                "items": {"type": "string"}
            },
            "recommendations": {
                "type": "array",
                "description": "Recommendations for improving accuracy",
                "items": {"type": "string"}
            }
        },
        "required": [
            "claims",
            "overall_accuracy",
            "unverified_count",
            "critical_issues",
            "recommendations"
        ],
        "additionalProperties": False
    }
}


# ============================================================================
# METADATA EXTRACTION SCHEMA (General Purpose)
# ============================================================================

METADATA_EXTRACTION_SCHEMA = {
    "name": "metadata_extraction",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title or main topic"
            },
            "authors": {
                "type": "array",
                "description": "List of authors if applicable",
                "items": {"type": "string"}
            },
            "publication_date": {
                "type": "string",
                "description": "Publication date (ISO format or year)"
            },
            "key_points": {
                "type": "array",
                "description": "Main points or findings",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 10
            },
            "medical_concepts": {
                "type": "array",
                "description": "Medical concepts or terms",
                "items": {"type": "string"}
            },
            "relevance_score": {
                "type": "number",
                "description": "Relevance to neurosurgery (0-1)",
                "minimum": 0,
                "maximum": 1
            },
            "study_type": {
                "type": "string",
                "description": "Type of study or content",
                "enum": [
                    "clinical_trial",
                    "case_series",
                    "case_report",
                    "review",
                    "meta_analysis",
                    "basic_science",
                    "editorial",
                    "other"
                ]
            }
        },
        "required": [
            "title",
            "key_points",
            "relevance_score"
        ],
        "additionalProperties": False
    }
}


# ============================================================================
# SOURCE RELEVANCE SCHEMA (Research Filtering)
# ============================================================================

SOURCE_RELEVANCE_SCHEMA = {
    "name": "source_relevance",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "is_relevant": {
                "type": "boolean",
                "description": "Whether source is relevant to the topic"
            },
            "relevance_score": {
                "type": "number",
                "description": "Relevance score (0-1)",
                "minimum": 0,
                "maximum": 1
            },
            "reason": {
                "type": "string",
                "description": "Brief explanation of relevance assessment"
            },
            "key_concepts_matched": {
                "type": "array",
                "description": "Concepts from source that match topic",
                "items": {"type": "string"}
            },
            "priority": {
                "type": "string",
                "description": "Priority level for inclusion",
                "enum": ["high", "medium", "low", "exclude"]
            }
        },
        "required": [
            "is_relevant",
            "relevance_score",
            "reason",
            "priority"
        ],
        "additionalProperties": False
    }
}


# ============================================================================
# IMAGE ANALYSIS SCHEMA (Vision)
# ============================================================================

IMAGE_ANALYSIS_SCHEMA = {
    "name": "image_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "image_type": {
                "type": "string",
                "description": "Type of medical image",
                "enum": [
                    "ct_scan",
                    "mri",
                    "xray",
                    "angiogram",
                    "diagram",
                    "surgical_photo",
                    "pathology",
                    "other"
                ]
            },
            "anatomical_structures": {
                "type": "array",
                "description": "Identified anatomical structures",
                "items": {
                    "type": "object",
                    "properties": {
                        "structure_name": {"type": "string"},
                        "location": {"type": "string"},
                        "abnormality": {"type": "boolean"}
                    },
                    "required": ["structure_name"],
                    "additionalProperties": False
                }
            },
            "pathology_identified": {
                "type": "array",
                "description": "Pathological findings",
                "items": {"type": "string"}
            },
            "clinical_significance": {
                "type": "string",
                "description": "Clinical relevance of findings"
            },
            "quality_assessment": {
                "type": "object",
                "description": "Image quality assessment",
                "properties": {
                    "quality": {"type": "string", "enum": ["excellent", "good", "fair", "poor"]},
                    "clarity": {"type": "number", "minimum": 0, "maximum": 1},
                    "diagnostic_value": {"type": "string", "enum": ["high", "moderate", "low"]}
                },
                "required": ["quality"],
                "additionalProperties": False
            },
            "confidence": {
                "type": "number",
                "description": "Confidence in analysis (0-1)",
                "minimum": 0,
                "maximum": 1
            }
        },
        "required": [
            "image_type",
            "anatomical_structures",
            "clinical_significance",
            "confidence"
        ],
        "additionalProperties": False
    }
}


# ============================================================================
# CHAPTER REVIEW SCHEMA (Stage 12: Quality Review & Refinement)
# ============================================================================

CHAPTER_REVIEW_SCHEMA = {
    "name": "chapter_review",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "contradictions": {
                "type": "array",
                "description": "Internal contradictions found between sections",
                "items": {
                    "type": "object",
                    "properties": {
                        "section_1": {"type": "string", "description": "First section with contradiction"},
                        "section_2": {"type": "string", "description": "Second section with contradiction"},
                        "contradiction_description": {"type": "string", "description": "Description of the contradiction"},
                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "suggested_resolution": {"type": "string", "description": "How to resolve this contradiction"}
                    },
                    "required": ["section_1", "section_2", "contradiction_description", "severity", "suggested_resolution"],
                    "additionalProperties": False
                }
            },
            "readability_issues": {
                "type": "array",
                "description": "Readability problems identified",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string", "description": "Section with readability issue"},
                        "issue_type": {
                            "type": "string",
                            "enum": ["jargon_overuse", "unclear_explanation", "poor_flow", "missing_context", "too_technical", "too_simple"],
                            "description": "Type of readability issue"
                        },
                        "description": {"type": "string", "description": "Description of the issue"},
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "improvement_suggestion": {"type": "string", "description": "How to improve readability"}
                    },
                    "required": ["section", "issue_type", "description", "severity", "improvement_suggestion"],
                    "additionalProperties": False
                }
            },
            "missing_transitions": {
                "type": "array",
                "description": "Missing or weak transitions between sections",
                "items": {
                    "type": "object",
                    "properties": {
                        "from_section": {"type": "string", "description": "Section transitioning from"},
                        "to_section": {"type": "string", "description": "Section transitioning to"},
                        "issue": {"type": "string", "description": "Why the transition is missing or weak"},
                        "suggested_transition": {"type": "string", "description": "Suggested transition text"}
                    },
                    "required": ["from_section", "to_section", "issue", "suggested_transition"],
                    "additionalProperties": False
                }
            },
            "citation_issues": {
                "type": "array",
                "description": "Problems with citations and references",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string", "description": "Section with citation issue"},
                        "issue_type": {
                            "type": "string",
                            "enum": ["missing_citation", "outdated_citation", "citation_mismatch", "over_citation", "under_citation"],
                            "description": "Type of citation issue"
                        },
                        "description": {"type": "string", "description": "Description of citation issue"},
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "recommendation": {"type": "string", "description": "Recommended action"}
                    },
                    "required": ["section", "issue_type", "description", "severity", "recommendation"],
                    "additionalProperties": False
                }
            },
            "logical_flow_issues": {
                "type": "array",
                "description": "Problems with logical progression and structure",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string", "description": "Section with flow issue"},
                        "issue": {"type": "string", "description": "Description of logical flow problem"},
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "suggested_reordering": {"type": "string", "description": "Suggested reordering or restructuring"}
                    },
                    "required": ["section", "issue", "severity", "suggested_reordering"],
                    "additionalProperties": False
                }
            },
            "unclear_explanations": {
                "type": "array",
                "description": "Concepts or explanations that are unclear",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string", "description": "Section with unclear explanation"},
                        "concept": {"type": "string", "description": "The unclear concept"},
                        "why_unclear": {"type": "string", "description": "Why this explanation is unclear"},
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "clarification_suggestion": {"type": "string", "description": "How to clarify"}
                    },
                    "required": ["section", "concept", "why_unclear", "severity", "clarification_suggestion"],
                    "additionalProperties": False
                }
            },
            "overall_quality_assessment": {
                "type": "object",
                "description": "Overall quality assessment of the chapter",
                "properties": {
                    "clarity_score": {"type": "number", "minimum": 0, "maximum": 1, "description": "How clear the writing is (0-1)"},
                    "coherence_score": {"type": "number", "minimum": 0, "maximum": 1, "description": "How well sections flow together (0-1)"},
                    "consistency_score": {"type": "number", "minimum": 0, "maximum": 1, "description": "How consistent terminology and style is (0-1)"},
                    "completeness_score": {"type": "number", "minimum": 0, "maximum": 1, "description": "How complete the coverage is (0-1)"},
                    "readability_level": {
                        "type": "string",
                        "enum": ["excellent", "good", "fair", "poor"],
                        "description": "Overall readability level"
                    },
                    "target_audience_alignment": {
                        "type": "string",
                        "enum": ["excellent", "good", "fair", "poor"],
                        "description": "How well aligned with target audience (neurosurgery residents/fellows)"
                    }
                },
                "required": ["clarity_score", "coherence_score", "consistency_score", "completeness_score", "readability_level", "target_audience_alignment"],
                "additionalProperties": False
            },
            "strengths": {
                "type": "array",
                "description": "Identified strengths of the chapter",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 10
            },
            "priority_improvements": {
                "type": "array",
                "description": "Top priority improvements ranked by importance",
                "items": {
                    "type": "object",
                    "properties": {
                        "priority_rank": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Priority ranking (1=highest)"},
                        "category": {
                            "type": "string",
                            "enum": ["contradiction", "readability", "citation", "flow", "clarity", "completeness"],
                            "description": "Category of improvement"
                        },
                        "description": {"type": "string", "description": "What needs improvement"},
                        "impact": {"type": "string", "enum": ["critical", "high", "medium", "low"], "description": "Impact of this improvement"},
                        "effort_required": {"type": "string", "enum": ["low", "medium", "high"], "description": "Effort to implement"}
                    },
                    "required": ["priority_rank", "category", "description", "impact", "effort_required"],
                    "additionalProperties": False
                },
                "minItems": 0,
                "maxItems": 10
            },
            "overall_recommendation": {
                "type": "string",
                "enum": ["publish_as_is", "minor_revisions", "moderate_revisions", "major_revisions"],
                "description": "Overall recommendation for next steps"
            },
            "review_summary": {
                "type": "string",
                "description": "Brief summary of review findings (2-3 sentences)"
            }
        },
        "required": [
            "contradictions",
            "readability_issues",
            "missing_transitions",
            "citation_issues",
            "logical_flow_issues",
            "unclear_explanations",
            "overall_quality_assessment",
            "strengths",
            "priority_improvements",
            "overall_recommendation",
            "review_summary"
        ],
        "additionalProperties": False
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_schema_by_name(schema_name: str) -> Dict[str, Any]:
    """
    Get schema by name

    Args:
        schema_name: Name of schema (e.g., 'chapter_analysis', 'fact_check')

    Returns:
        Schema dictionary

    Raises:
        ValueError: If schema name not found
    """
    schemas = {
        "chapter_analysis": CHAPTER_ANALYSIS_SCHEMA,
        "research_context": CONTEXT_BUILDING_SCHEMA,
        "fact_check": FACT_CHECK_SCHEMA,
        "metadata_extraction": METADATA_EXTRACTION_SCHEMA,
        "source_relevance": SOURCE_RELEVANCE_SCHEMA,
        "image_analysis": IMAGE_ANALYSIS_SCHEMA,
        "chapter_review": CHAPTER_REVIEW_SCHEMA,
    }

    if schema_name not in schemas:
        raise ValueError(
            f"Unknown schema '{schema_name}'. Available: {', '.join(schemas.keys())}"
        )

    return schemas[schema_name]


def validate_schema_response(data: Dict[str, Any], schema_name: str) -> bool:
    """
    Validate that response data matches schema

    Note: With GPT-4o structured outputs, this should always pass.
    This function is for additional validation/debugging.

    Args:
        data: Response data to validate
        schema_name: Name of schema to validate against

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails
    """
    schema = get_schema_by_name(schema_name)
    required_fields = schema["schema"].get("required", [])

    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in {schema_name} response")

    return True
