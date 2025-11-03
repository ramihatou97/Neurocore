"""
Flexible Chapter Template Guidance System

IMPORTANT PHILOSOPHY:
This module provides SUGGESTIONS, not rigid requirements. The templates are meant to:
1. Guide AI in organizing knowledge intelligently
2. Suggest standard section types where appropriate
3. Adapt based on available knowledge pool
4. NEVER lose content to fit a template
5. Enhance organization without constraining content

The AI should analyze sources FIRST, then use these templates to organize the
knowledge in the most logical way - not force content into predefined boxes.
"""

from typing import Dict, List, Optional, Any
from enum import Enum


class ChapterType(str, Enum):
    """Chapter types with different organizational emphases"""
    SURGICAL_DISEASE = "surgical_disease"
    PURE_ANATOMY = "pure_anatomy"
    SURGICAL_TECHNIQUE = "surgical_technique"


class SectionType(str, Enum):
    """
    Standard section types for neurosurgical chapters.
    These are SUGGESTIONS - AI can use, adapt, or create custom sections.
    """
    INTRODUCTION = "introduction"
    EPIDEMIOLOGY = "epidemiology"
    PATHOPHYSIOLOGY = "pathophysiology"
    CLINICAL_PRESENTATION = "clinical_presentation"
    DIAGNOSTIC_EVALUATION = "diagnostic_evaluation"
    DIFFERENTIAL_DIAGNOSIS = "differential_diagnosis"
    TREATMENT_OPTIONS = "treatment_options"
    SURGICAL_TECHNIQUE = "surgical_technique"
    POSTOPERATIVE_MANAGEMENT = "postoperative_management"
    COMPLICATIONS = "complications"
    OUTCOMES = "outcomes"
    FUTURE_DIRECTIONS = "future_directions"
    CUSTOM = "custom"  # For content that doesn't fit standard types


class ChapterTemplateGuidance:
    """
    Provides flexible template guidance for chapter structure.

    Key Principles:
    - Templates are suggestions, not requirements
    - Structure adapts to available knowledge
    - Content preservation > Template adherence
    - Support 4-level hierarchy WHERE APPROPRIATE (not forced)
    - Allow custom sections for unique content
    """

    @staticmethod
    def get_section_type_hints(section_type: SectionType) -> Dict[str, Any]:
        """
        Get helpful hints for generating a specific section type.

        These hints guide content generation but don't constrain it.
        The AI can adapt or ignore based on available sources.

        Args:
            section_type: The type of section being generated

        Returns:
            Dictionary with generation hints and typical content patterns
        """
        hints = {
            SectionType.INTRODUCTION: {
                "description": "Overview and context for the chapter topic",
                "typical_content": [
                    "Definition and clinical significance",
                    "Historical context (if relevant)",
                    "Scope of the chapter",
                    "Key concepts overview"
                ],
                "typical_depth": "2-3 paragraphs",
                "subsection_suggestions": [],  # Usually flat
                "adaptable": True,
                "keywords": ["overview", "definition", "significance", "context"]
            },

            SectionType.EPIDEMIOLOGY: {
                "description": "Incidence, prevalence, and population patterns",
                "typical_content": [
                    "Incidence and prevalence data",
                    "Age and gender distribution",
                    "Geographic variations",
                    "Risk factors and populations affected"
                ],
                "typical_depth": "1-2 paragraphs per subsection",
                "subsection_suggestions": [
                    "Incidence and Prevalence",
                    "Demographics",
                    "Risk Factors"
                ],
                "adaptable": True,
                "keywords": ["incidence", "prevalence", "demographics", "risk factors"]
            },

            SectionType.PATHOPHYSIOLOGY: {
                "description": "Underlying mechanisms and biological processes",
                "typical_content": [
                    "Molecular and cellular mechanisms",
                    "Anatomical changes",
                    "Disease progression pathways",
                    "Pathological features"
                ],
                "typical_depth": "2-4 paragraphs per mechanism",
                "subsection_suggestions": [
                    "Molecular Mechanisms",
                    "Anatomical Pathology",
                    "Disease Progression"
                ],
                "adaptable": True,
                "keywords": ["mechanism", "pathology", "cellular", "molecular", "progression"]
            },

            SectionType.CLINICAL_PRESENTATION: {
                "description": "Signs, symptoms, and clinical features",
                "typical_content": [
                    "Common presenting symptoms",
                    "Physical examination findings",
                    "Neurological signs",
                    "Clinical patterns and variations"
                ],
                "typical_depth": "1-3 paragraphs per presentation type",
                "subsection_suggestions": [
                    "Symptoms",
                    "Physical Findings",
                    "Neurological Examination",
                    "Clinical Variants"
                ],
                "adaptable": True,
                "keywords": ["symptoms", "signs", "presentation", "examination", "findings"]
            },

            SectionType.DIAGNOSTIC_EVALUATION: {
                "description": "Diagnostic approaches and investigations",
                "typical_content": [
                    "Clinical assessment",
                    "Imaging modalities (CT, MRI, angio)",
                    "Laboratory tests",
                    "Specialized diagnostics",
                    "Diagnostic algorithms"
                ],
                "typical_depth": "2-3 paragraphs per modality",
                "subsection_suggestions": [
                    "Clinical Assessment",
                    "Neuroimaging",
                    "Laboratory Studies",
                    "Diagnostic Approach"
                ],
                "adaptable": True,
                "keywords": ["imaging", "MRI", "CT", "diagnostic", "evaluation", "workup"]
            },

            SectionType.DIFFERENTIAL_DIAGNOSIS: {
                "description": "Alternative diagnoses to consider",
                "typical_content": [
                    "Similar conditions",
                    "Distinguishing features",
                    "Diagnostic pitfalls",
                    "Decision-making approach"
                ],
                "typical_depth": "1-2 paragraphs per differential",
                "subsection_suggestions": [],  # Often flat or by category
                "adaptable": True,
                "keywords": ["differential", "similar", "distinguish", "alternative"]
            },

            SectionType.TREATMENT_OPTIONS: {
                "description": "Available treatment modalities",
                "typical_content": [
                    "Conservative management",
                    "Medical therapy",
                    "Surgical indications",
                    "Treatment algorithms",
                    "Evidence-based recommendations"
                ],
                "typical_depth": "2-4 paragraphs per modality",
                "subsection_suggestions": [
                    "Conservative Management",
                    "Medical Therapy",
                    "Surgical Indications",
                    "Treatment Algorithm"
                ],
                "adaptable": True,
                "keywords": ["treatment", "management", "therapy", "conservative", "surgical"]
            },

            SectionType.SURGICAL_TECHNIQUE: {
                "description": "Detailed surgical procedure description",
                "typical_content": [
                    "Patient positioning",
                    "Surgical approach and exposure",
                    "Step-by-step procedure",
                    "Technical considerations",
                    "Closure and wound management",
                    "Alternative techniques"
                ],
                "typical_depth": "3-5 paragraphs per major step",
                "subsection_suggestions": [
                    "Preoperative Planning",
                    "Positioning and Preparation",
                    "Surgical Approach",
                    "Procedure Steps",
                    "Closure",
                    "Technical Pearls"
                ],
                "adaptable": True,
                "keywords": ["technique", "approach", "procedure", "steps", "positioning"]
            },

            SectionType.POSTOPERATIVE_MANAGEMENT: {
                "description": "Post-surgical care and monitoring",
                "typical_content": [
                    "Immediate postoperative care",
                    "ICU management",
                    "Monitoring parameters",
                    "Early mobilization",
                    "Discharge planning",
                    "Follow-up protocols"
                ],
                "typical_depth": "2-3 paragraphs per phase",
                "subsection_suggestions": [
                    "Immediate Postoperative Care",
                    "ICU Management",
                    "Ward Care",
                    "Rehabilitation",
                    "Follow-up"
                ],
                "adaptable": True,
                "keywords": ["postoperative", "recovery", "monitoring", "follow-up", "ICU"]
            },

            SectionType.COMPLICATIONS: {
                "description": "Potential adverse events and management",
                "typical_content": [
                    "Common complications",
                    "Serious adverse events",
                    "Recognition and prevention",
                    "Management strategies",
                    "Risk mitigation"
                ],
                "typical_depth": "1-2 paragraphs per complication",
                "subsection_suggestions": [
                    "Intraoperative Complications",
                    "Early Postoperative Complications",
                    "Late Complications",
                    "Prevention Strategies"
                ],
                "adaptable": True,
                "keywords": ["complications", "adverse", "risks", "prevention", "management"]
            },

            SectionType.OUTCOMES: {
                "description": "Treatment results and prognosis",
                "typical_content": [
                    "Functional outcomes",
                    "Survival data",
                    "Quality of life measures",
                    "Prognostic factors",
                    "Long-term results",
                    "Comparative outcomes"
                ],
                "typical_depth": "2-3 paragraphs per outcome type",
                "subsection_suggestions": [
                    "Functional Outcomes",
                    "Survival and Prognosis",
                    "Quality of Life",
                    "Prognostic Factors"
                ],
                "adaptable": True,
                "keywords": ["outcomes", "prognosis", "survival", "functional", "results"]
            },

            SectionType.FUTURE_DIRECTIONS: {
                "description": "Emerging research and future developments",
                "typical_content": [
                    "Ongoing research",
                    "Novel therapies",
                    "Technological advances",
                    "Unresolved questions",
                    "Future perspectives"
                ],
                "typical_depth": "1-2 paragraphs per direction",
                "subsection_suggestions": [],  # Usually flat
                "adaptable": True,
                "keywords": ["future", "research", "emerging", "novel", "advances"]
            },

            SectionType.CUSTOM: {
                "description": "Custom section for unique content",
                "typical_content": [],
                "typical_depth": "Varies based on content",
                "subsection_suggestions": [],
                "adaptable": True,
                "keywords": []
            }
        }

        return hints.get(section_type, hints[SectionType.CUSTOM])

    @staticmethod
    def get_chapter_type_emphasis(chapter_type: ChapterType) -> Dict[str, Any]:
        """
        Get organizational emphasis for different chapter types.

        These are suggestions for which sections to emphasize,
        not rigid requirements about what must be included.

        Args:
            chapter_type: The type of chapter being generated

        Returns:
            Dictionary with recommended section emphasis
        """
        emphasis = {
            ChapterType.SURGICAL_DISEASE: {
                "description": "Comprehensive disease coverage with surgical focus",
                "high_priority_sections": [
                    SectionType.PATHOPHYSIOLOGY,
                    SectionType.CLINICAL_PRESENTATION,
                    SectionType.DIAGNOSTIC_EVALUATION,
                    SectionType.TREATMENT_OPTIONS,
                    SectionType.SURGICAL_TECHNIQUE,
                    SectionType.OUTCOMES
                ],
                "moderate_priority_sections": [
                    SectionType.INTRODUCTION,
                    SectionType.EPIDEMIOLOGY,
                    SectionType.DIFFERENTIAL_DIAGNOSIS,
                    SectionType.POSTOPERATIVE_MANAGEMENT,
                    SectionType.COMPLICATIONS
                ],
                "optional_sections": [
                    SectionType.FUTURE_DIRECTIONS
                ],
                "typical_depth_multiplier": 1.0
            },

            ChapterType.PURE_ANATOMY: {
                "description": "Anatomical structures and relationships",
                "high_priority_sections": [
                    SectionType.INTRODUCTION,
                    # Custom anatomy sections (boundaries, relations, vessels, nerves)
                ],
                "moderate_priority_sections": [
                    SectionType.CLINICAL_PRESENTATION,  # Clinical relevance
                    SectionType.DIAGNOSTIC_EVALUATION,  # Imaging anatomy
                ],
                "optional_sections": [
                    SectionType.SURGICAL_TECHNIQUE,  # Surgical approaches
                    SectionType.FUTURE_DIRECTIONS
                ],
                "typical_depth_multiplier": 0.8,
                "custom_sections_encouraged": True,
                "custom_section_suggestions": [
                    "Gross Anatomy",
                    "Boundaries and Relations",
                    "Vascular Supply",
                    "Innervation",
                    "Imaging Anatomy",
                    "Surgical Approaches",
                    "Clinical Relevance"
                ]
            },

            ChapterType.SURGICAL_TECHNIQUE: {
                "description": "Detailed procedural guidance",
                "high_priority_sections": [
                    SectionType.INTRODUCTION,
                    SectionType.SURGICAL_TECHNIQUE,
                    SectionType.POSTOPERATIVE_MANAGEMENT,
                    SectionType.COMPLICATIONS
                ],
                "moderate_priority_sections": [
                    SectionType.TREATMENT_OPTIONS,  # Indications
                    SectionType.DIAGNOSTIC_EVALUATION,  # Preoperative workup
                    SectionType.OUTCOMES
                ],
                "optional_sections": [
                    SectionType.PATHOPHYSIOLOGY,
                    SectionType.EPIDEMIOLOGY,
                    SectionType.FUTURE_DIRECTIONS
                ],
                "typical_depth_multiplier": 1.2,
                "surgical_technique_extra_detail": True
            }
        }

        return emphasis.get(chapter_type, emphasis[ChapterType.SURGICAL_DISEASE])

    @staticmethod
    def suggest_structure_from_knowledge(
        available_sources: List[Dict[str, Any]],
        chapter_type: ChapterType,
        topic: str
    ) -> Dict[str, Any]:
        """
        Suggest chapter structure based on available knowledge.

        KNOWLEDGE-FIRST APPROACH:
        1. Analyze what knowledge is actually available
        2. Identify natural content clusters
        3. Map to standard sections WHERE APPROPRIATE
        4. Create custom sections for unique content
        5. Never discard content because it doesn't fit

        Args:
            available_sources: List of research sources with content
            chapter_type: Type of chapter being generated
            topic: Chapter topic/title

        Returns:
            Suggested structure with flexible section recommendations
        """
        # This returns a structure suggestion, not a rigid template
        # AI will use this in Stage 5 to guide synthesis planning

        type_emphasis = ChapterTemplateGuidance.get_chapter_type_emphasis(chapter_type)

        return {
            "philosophy": "Knowledge-first adaptive structure",
            "approach": "Analyze sources → Identify themes → Organize intelligently",
            "flexibility_level": "high",

            "chapter_type": chapter_type.value,
            "chapter_type_emphasis": type_emphasis,

            "recommended_sections": {
                "high_priority": [s.value for s in type_emphasis["high_priority_sections"]],
                "moderate_priority": [s.value for s in type_emphasis["moderate_priority_sections"]],
                "optional": [s.value for s in type_emphasis.get("optional_sections", [])]
            },

            "custom_sections_encouraged": type_emphasis.get("custom_sections_encouraged", False),
            "custom_section_suggestions": type_emphasis.get("custom_section_suggestions", []),

            "hierarchy_guidelines": {
                "max_depth": 4,  # Chapter → Section → Subsection → Sub-subsection
                "adapt_depth_to_content": True,
                "not_all_sections_need_subsections": True,
                "some_sections_may_be_deeper_than_others": True
            },

            "content_preservation_rules": [
                "NEVER discard knowledge to fit template",
                "Create custom sections for content that doesn't fit standard types",
                "Adapt section titles to match actual content",
                "Merge sections if content is limited",
                "Split sections if content is extensive",
                "Use subsections only where they enhance organization"
            ],

            "knowledge_mapping_hints": {
                "analyze_sources_first": True,
                "identify_natural_clusters": True,
                "map_clusters_to_sections": "flexible",
                "allow_cross_section_content": True,
                "prioritize_logical_flow": True
            },

            "section_type_hints": {
                section_type.value: ChapterTemplateGuidance.get_section_type_hints(section_type)
                for section_type in type_emphasis["high_priority_sections"] +
                                   type_emphasis["moderate_priority_sections"]
            }
        }

    @staticmethod
    def validate_structure_flexibility(proposed_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that a proposed structure maintains flexibility principles.

        This is NOT a rigid validation - it checks that the structure
        is reasonable and preserves knowledge, but doesn't enforce templates.

        Args:
            proposed_structure: The structure proposed by AI

        Returns:
            Validation result with suggestions (not requirements)
        """
        issues = []
        suggestions = []

        sections = proposed_structure.get("sections", [])

        # Check for reasonable section count (not a hard limit)
        if len(sections) < 3:
            suggestions.append("Consider if more sections would improve organization")
        elif len(sections) > 15:
            suggestions.append("Many sections - consider if some could be merged for better flow")

        # Check for hierarchy depth (flexible guideline)
        max_depth = 0
        for section in sections:
            depth = ChapterTemplateGuidance._calculate_section_depth(section)
            max_depth = max(max_depth, depth)

        if max_depth > 4:
            suggestions.append(f"Deep nesting detected ({max_depth} levels) - consider flattening for readability")

        # Check for empty sections (potential issue)
        empty_sections = [s.get("title") for s in sections if not s.get("content_plan")]
        if empty_sections:
            issues.append(f"Sections without content plan: {', '.join(empty_sections)}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "philosophy_adherence": {
                "knowledge_preserved": True,  # Assume true unless proven otherwise
                "structure_adaptive": True,
                "templates_flexible": True
            }
        }

    @staticmethod
    def _calculate_section_depth(section: Dict[str, Any], current_depth: int = 1) -> int:
        """Recursively calculate maximum depth of section hierarchy"""
        subsections = section.get("subsections", [])
        if not subsections:
            return current_depth

        max_child_depth = current_depth
        for subsection in subsections:
            child_depth = ChapterTemplateGuidance._calculate_section_depth(subsection, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth
