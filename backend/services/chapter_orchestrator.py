"""
Chapter Orchestrator - 14-Stage Workflow Manager
Coordinates the complete "Alive Chapter" generation pipeline
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.database.models import Chapter, User
from backend.services.ai_provider_service import AIProviderService, AITask
from backend.services.research_service import ResearchService
from backend.services.deduplication_service import DeduplicationService  # Phase 2 Week 3-4
from backend.services.fact_checking_service import FactCheckingService  # Phase 3: GPT-4o Fact-Checking
from backend.services.templates.chapter_template_guidance import ChapterTemplateGuidance, ChapterType  # Phase 22: Flexible Templates
from backend.schemas.ai_schemas import CHAPTER_ANALYSIS_SCHEMA, CONTEXT_BUILDING_SCHEMA
from backend.config import settings
from backend.utils import get_logger
from backend.utils.websocket_emitter import emitter
from backend.utils.events import ChapterStage

logger = get_logger(__name__)


class ChapterOrchestrator:
    """
    Orchestrates the 14-stage chapter generation workflow

    Stage Breakdown:
    1. Topic Input & Validation - Parse and validate user query
    2. Context Building - Extract entities and build search context
    3. Internal Research - Search indexed PDFs with vector similarity
    4. External Research - Query PubMed for recent papers
    5. Content Synthesis Planning - Plan chapter structure and sections
    6. Section Generation - Generate each section with AI (iterative)
    7. Image Integration - Select and integrate relevant images
    8. Citation Network - Build citation links and references
    9. Quality Assurance - Check completeness and calculate scores
    10. Fact-Checking - Cross-reference claims with sources
    11. Formatting & Structure - Apply consistent formatting
    12. Review & Refinement - AI-powered clarity review
    13. Finalization - Generate final output and metadata
    14. Delivery - Store and return completed chapter

    Progress Tracking:
    - Each stage updates Chapter.generation_status
    - Intermediate results stored in JSONB columns
    - Errors logged and recoverable
    """

    def __init__(self, db_session: Session):
        """
        Initialize chapter orchestrator

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.ai_service = AIProviderService()
        self.research_service = ResearchService(db_session)
        self.dedup_service = DeduplicationService()  # Phase 2 Week 3-4
        self.fact_check_service = FactCheckingService()  # Phase 3: GPT-4o Fact-Checking

    async def generate_chapter(
        self,
        topic: str,
        user: User,
        chapter_type: Optional[str] = None
    ) -> Chapter:
        """
        Main entry point for chapter generation

        Args:
            topic: Chapter topic/query
            user: User requesting the chapter
            chapter_type: Optional chapter type override

        Returns:
            Generated Chapter object
        """
        logger.info(f"Starting chapter generation: '{topic}' for user {user.email}")

        # Create initial chapter record
        chapter = Chapter(
            title=topic,
            author_id=user.id,
            generation_status="stage_1_input",
            chapter_type=chapter_type
        )
        self.db.add(chapter)
        self.db.commit()
        self.db.refresh(chapter)

        try:
            # Execute 14-stage workflow with WebSocket progress updates
            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_1_INPUT, 1, "Validating input and analyzing topic")
            await self._stage_1_input_validation(chapter, topic)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_2_CONTEXT, 2, "Building context and extracting entities")
            await self._stage_2_context_building(chapter, topic)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_3_RESEARCH_INTERNAL, 3, "Searching internal database for relevant sources")
            await self._stage_3_internal_research(chapter)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_4_RESEARCH_EXTERNAL, 4, "Querying PubMed for recent publications")
            await self._stage_4_external_research(chapter)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_5_PLANNING, 5, "Planning chapter structure and outline")
            await self._stage_5_synthesis_planning(chapter)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_6_GENERATION, 6, "Generating chapter sections with AI")
            await self._stage_6_section_generation(chapter)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_7_IMAGES, 7, "Integrating relevant images")
            await self._stage_7_image_integration(chapter)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_8_CITATIONS, 8, "Building citation network")
            await self._stage_8_citation_network(chapter)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_9_QA, 9, "Performing quality assurance checks")
            await self._stage_9_quality_assurance(chapter)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_10_FACT_CHECK, 10, "Fact-checking with sources")
            await self._stage_10_fact_checking(chapter)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_11_FORMATTING, 11, "Applying formatting and structure")
            await self._stage_11_formatting(chapter)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_12_REVIEW, 12, "Reviewing and refining content")
            await self._stage_12_review_refinement(chapter)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_13_FINALIZATION, 13, "Finalizing chapter metadata")
            await self._stage_13_finalization(chapter)

            await emitter.emit_chapter_progress(str(chapter.id), ChapterStage.STAGE_14_DELIVERY, 14, "Delivering final chapter")
            await self._stage_14_delivery(chapter)

            logger.info(f"Chapter generation completed: {chapter.id}")

            # Emit completion event
            await emitter.emit_chapter_completed(
                str(chapter.id),
                "Chapter generation completed successfully",
                {
                    "depth_score": chapter.depth_score,
                    "coverage_score": chapter.coverage_score,
                    "evidence_score": chapter.evidence_score,
                    "currency_score": chapter.currency_score
                }
            )

        except Exception as e:
            logger.error(f"Chapter generation failed at stage {chapter.generation_status}: {str(e)}", exc_info=True)
            chapter.generation_status = "failed"
            chapter.generation_error = str(e)
            self.db.commit()

            # Emit failure event
            await emitter.emit_chapter_failed(
                str(chapter.id),
                str(e),
                {"stage": chapter.generation_status}
            )

            raise

        return chapter

    async def _stage_1_input_validation(self, chapter: Chapter, topic: str) -> None:
        """
        Stage 1: Validate and parse input using GPT-4o Structured Outputs

        - Validate topic is not empty
        - Extract key medical terms with schema-validated AI analysis
        - Guaranteed valid JSON response (no try/catch needed)
        - Store in stage_1_input JSONB

        Uses: GPT-4o with CHAPTER_ANALYSIS_SCHEMA for 100% reliable parsing
        """
        logger.info(f"Stage 1: Input validation for chapter {chapter.id}")
        chapter.generation_status = "stage_1_input"
        self.db.commit()

        # Validate topic
        if not topic or len(topic.strip()) < 3:
            raise ValueError("Topic must be at least 3 characters")

        # Use GPT-4o with structured outputs to extract key concepts
        # This GUARANTEES valid JSON matching CHAPTER_ANALYSIS_SCHEMA
        prompt = f"""
        Analyze this neurosurgery topic query and extract structured metadata.

        Query: "{topic}"

        Extract:
        1. Primary neurosurgical concepts (anatomical structures, procedures, diseases, conditions)
        2. Chapter type classification (surgical_disease, pure_anatomy, or surgical_technique)
        3. Medical keywords and terms for database indexing and research
        4. Target audience complexity level (beginner, intermediate, advanced, or expert)
        5. Anatomical regions involved (if applicable)
        6. Surgical approaches or techniques (if applicable)
        7. Recommended number of sections for comprehensive coverage (10-150 sections)
        8. Analysis confidence: Your confidence in this classification and analysis (0.0-1.0)
           - 1.0 = Very clear, well-defined neurosurgical topic
           - 0.8-0.9 = Clear topic with minor ambiguities
           - 0.6-0.7 = Moderately clear, some interpretation needed
           - Below 0.6 = Ambiguous or unclear topic requiring assumptions

        Provide comprehensive, medically accurate analysis suitable for a neurosurgery knowledge base.
        """

        # Use structured outputs - response is GUARANTEED to match schema
        response = await self.ai_service.generate_text_with_schema(
            prompt=prompt,
            schema=CHAPTER_ANALYSIS_SCHEMA,
            task=AITask.METADATA_EXTRACTION,
            max_tokens=1000,
            temperature=0.3  # Lower temperature for structured data extraction
        )

        # No try/catch needed! response['data'] is guaranteed valid
        analysis = response["data"]

        # Store in database
        chapter.stage_1_input = {
            "original_topic": topic,
            "analysis": analysis,
            "validated_at": datetime.utcnow().isoformat(),
            "ai_model": response["model"],
            "ai_provider": response["provider"],
            "ai_cost_usd": response["cost_usd"],
            "schema_validated": True  # Flag indicating structured output was used
        }

        # Update chapter type if not set
        if not chapter.chapter_type:
            chapter.chapter_type = analysis.get("chapter_type", "surgical_disease")

        self.db.commit()
        logger.info(f"Stage 1 complete: Identified as {chapter.chapter_type} with {len(analysis.get('keywords', []))} keywords")

    async def _stage_2_context_building(self, chapter: Chapter, topic: str) -> None:
        """
        Stage 2: Build research context using GPT-4o Structured Outputs

        - Extract entities and research gaps with schema validation
        - Identify key references and content categories
        - Assess research confidence and evidence quality
        - Store in stage_2_context JSONB

        Uses: GPT-4o with CONTEXT_BUILDING_SCHEMA for reliable research planning
        """
        logger.info(f"Stage 2: Context building for chapter {chapter.id}")
        chapter.generation_status = "stage_2_context"
        self.db.commit()

        stage_1_data = chapter.stage_1_input or {}
        analysis = stage_1_data.get("analysis", {})

        # Build comprehensive research context with structured outputs
        # This schema ensures we capture research gaps, key references, and quality metrics
        prompt = f"""
        Build a comprehensive research context for this neurosurgery topic:

        Topic: "{topic}"
        Chapter Type: {chapter.chapter_type}
        Primary Concepts: {', '.join(analysis.get('primary_concepts', [topic]))}
        Keywords: {', '.join(analysis.get('keywords', []))}
        Complexity: {analysis.get('complexity', 'intermediate')}

        Analyze the research landscape for this topic and provide:

        1. Research Gaps: Identify areas where knowledge may be incomplete or emerging
           - Describe each gap
           - Assess severity (high, medium, low)
           - Note which sections might be affected

        2. Key References: Identify the types of sources that would be most valuable
           - Suggest reference titles/topics that would be important
           - Estimate relevance scores
           - Identify key findings that should be covered
           - Include PubMed IDs if you know them

        3. Content Categories: Estimate the expected distribution of source types
           - Clinical studies count
           - Case reports count
           - Review articles count
           - Basic science papers count
           - Imaging data count

        4. Temporal Coverage: Estimate appropriate time range for sources
           - Oldest relevant year (foundational work)
           - Most recent year (current knowledge)
           - Median year (bulk of evidence)

        5. Confidence Assessment: Evaluate expected research quality
           - Overall confidence in available literature (0-1 scale)
           - Evidence quality level (high, moderate, low, very_low)
           - Completeness of expected coverage (0-1 scale)

        Be realistic about what research exists and what gaps may exist in neurosurgical literature.
        """

        # Use structured outputs - response is GUARANTEED to match CONTEXT_BUILDING_SCHEMA
        response = await self.ai_service.generate_text_with_schema(
            prompt=prompt,
            schema=CONTEXT_BUILDING_SCHEMA,
            task=AITask.METADATA_EXTRACTION,
            max_tokens=2000,
            temperature=0.4  # Slightly higher for creative gap identification
        )

        # No try/catch needed! response['data'] is guaranteed valid
        context = response["data"]

        chapter.stage_2_context = {
            "context": context,
            "built_at": datetime.utcnow().isoformat(),
            "ai_model": response["model"],
            "ai_provider": response["provider"],
            "ai_cost_usd": response["cost_usd"],
            "schema_validated": True,
            "research_gaps_count": len(context.get("research_gaps", [])),
            "key_references_count": len(context.get("key_references", [])),
            "confidence_score": context.get("confidence_assessment", {}).get("overall_confidence", 0.7)
        }

        self.db.commit()

        gaps_count = len(context.get("research_gaps", []))
        refs_count = len(context.get("key_references", []))
        confidence = context.get("confidence_assessment", {}).get("overall_confidence", 0.7)

        logger.info(f"Stage 2 complete: Identified {gaps_count} research gaps, {refs_count} key references, confidence: {confidence:.2f}")

    async def _stage_3_internal_research(self, chapter: Chapter) -> None:
        """
        Stage 3: Internal database research

        - Search indexed PDFs using vector similarity
        - Find relevant images
        - Identify citation networks
        - Rank sources by relevance
        """
        logger.info(f"Stage 3: Internal research for chapter {chapter.id}")
        chapter.generation_status = "stage_3_research_internal"
        self.db.commit()

        stage_2_data = chapter.stage_2_context or {}
        context = stage_2_data.get("context", {})
        search_queries = context.get("search_queries", [chapter.title])

        # Phase 2: Execute queries in parallel (40% faster)
        # Old: 5 queries × 2s = 10s sequential
        # New: 5 queries in parallel = 3s
        all_sources = await self.research_service.internal_research_parallel(
            queries=search_queries[:5],
            max_results_per_query=5,
            min_relevance=0.6
        )

        # Phase 2 Week 3-4: Intelligent Deduplication
        unique_sources = await self._deduplicate_sources(all_sources)

        # Rank sources
        ranked_sources = await self.research_service.rank_sources(
            unique_sources,
            chapter.title
        )

        # Phase 2 Week 3-4: AI Relevance Filtering for internal sources
        from backend.config import settings
        if settings.AI_RELEVANCE_FILTERING_ENABLED:
            logger.info("Applying AI relevance filtering to internal sources...")
            ranked_sources = await self.research_service.filter_sources_by_ai_relevance(
                sources=ranked_sources[:20],  # Filter top 20 candidates
                query=chapter.title,
                threshold=settings.AI_RELEVANCE_THRESHOLD,
                use_ai_filtering=True
            )
            logger.info(f"AI filtering: {len(ranked_sources)} internal sources retained")

        # Search for relevant images
        images = await self.research_service.search_images(
            query=chapter.title,
            max_results=10
        )

        chapter.stage_3_internal_research = {
            "sources": ranked_sources[:20],  # Top 20 sources (after AI filtering)
            "images": images,
            "total_sources_found": len(all_sources),
            "unique_sources": len(unique_sources),
            "ai_filtered": settings.AI_RELEVANCE_FILTERING_ENABLED,
            "research_at": datetime.utcnow().isoformat()
        }

        self.db.commit()
        logger.info(f"Stage 3 complete: Found {len(ranked_sources)} internal sources")

    async def _stage_4_external_research(self, chapter: Chapter) -> None:
        """
        Stage 4: External research (Dual-Track: Evidence-Based + AI-Researched)

        TRACK 1 (Evidence-based): PubMed queries for peer-reviewed papers
        TRACK 2 (AI-researched): Perplexity/Gemini for neurosurgical expertise synthesis

        Both tracks run in PARALLEL for speed, then results are merged.
        Configurable: Can disable AI research to fall back to PubMed-only mode.
        """
        logger.info(f"Stage 4: Dual-track external research for chapter {chapter.id}")
        chapter.generation_status = "stage_4_research_external"
        self.db.commit()

        stage_2_data = chapter.stage_2_context or {}
        context = stage_2_data.get("context", {})
        search_queries = context.get("search_queries", [chapter.title])

        # Determine research methods based on configuration
        from backend.config import settings

        if settings.EXTERNAL_RESEARCH_STRATEGY == "evidence_only":
            research_methods = ["pubmed"]
        elif settings.EXTERNAL_RESEARCH_STRATEGY == "ai_only":
            research_methods = ["ai"]
        else:  # "hybrid" - default
            research_methods = ["pubmed"]
            if settings.EXTERNAL_RESEARCH_AI_ENABLED:
                research_methods.append("ai")

        logger.info(f"Research methods: {research_methods} (strategy: {settings.EXTERNAL_RESEARCH_STRATEGY})")

        # Execute dual-track parallel research
        if settings.EXTERNAL_RESEARCH_PARALLEL_EXECUTION and len(research_methods) > 1:
            # PARALLEL execution (faster)
            logger.info("Executing parallel dual-track research...")
            research_results = await self.research_service.external_research_parallel(
                queries=search_queries[:3],  # Limit to 3 queries
                methods=research_methods,
                max_results_per_query=5
            )
            pubmed_sources = research_results.get("pubmed", [])
            ai_sources = research_results.get("ai_research", [])
        else:
            # SEQUENTIAL execution (fallback)
            logger.info("Executing sequential research...")
            pubmed_sources = []
            ai_sources = []

            for query in search_queries[:3]:
                if "pubmed" in research_methods:
                    papers = await self.research_service.external_research_pubmed(
                        query=query,
                        max_results=5,
                        recent_years=5
                    )
                    pubmed_sources.extend(papers)

                if "ai" in research_methods:
                    # Use dual AI provider strategy (Gemini + Perplexity)
                    if settings.GEMINI_GROUNDING_ENABLED and settings.DUAL_AI_PROVIDER_STRATEGY:
                        dual_ai_result = await self.research_service.external_research_dual_ai(
                            query=query,
                            strategy=settings.DUAL_AI_PROVIDER_STRATEGY,
                            max_results=5
                        )
                        ai_results = dual_ai_result.get("sources", [])
                    else:
                        # Single provider (backward compatibility)
                        ai_results = await self.research_service.external_research_ai(
                            query=query,
                            max_results=5
                        )
                    ai_sources.extend(ai_results)

        # Add source_type metadata to all sources (if not already present)
        for source in pubmed_sources:
            if "source_type" not in source:
                source["source_type"] = "pubmed"
                source["research_method"] = "evidence_based"

        for source in ai_sources:
            if "source_type" not in source:
                source["source_type"] = "ai_research"
                # research_method already set by external_research_ai()

        # Combine all sources for deduplication
        all_external_sources = pubmed_sources + ai_sources

        # Intelligent Deduplication (preserves source type metadata)
        unique_external = await self._deduplicate_sources(all_external_sources)

        # AI Relevance Filtering (if enabled, applies to ALL sources)
        if settings.AI_RELEVANCE_FILTERING_ENABLED and unique_external:
            logger.info("Applying AI relevance filtering to all external sources...")
            unique_external = await self.research_service.filter_sources_by_ai_relevance(
                sources=unique_external[:20],  # Filter top 20 candidates
                query=chapter.title,
                threshold=settings.AI_RELEVANCE_THRESHOLD,
                use_ai_filtering=True
            )
            logger.info(f"AI filtering: {len(unique_external)} sources retained")

        # Separate sources by type for storage
        final_pubmed = [s for s in unique_external if s.get("source_type") == "pubmed"]
        final_ai = [s for s in unique_external if s.get("source_type") in ["ai_research", "ai_citation"]]

        # Store results with dual-track structure (Phase 2: Now includes dual AI providers)
        chapter.stage_4_external_research = {
            # Combined sources (for backward compatibility)
            "sources": unique_external[:15],  # Top 15 total

            # Separated by type
            "pubmed_sources": final_pubmed[:10],  # Top 10 PubMed
            "ai_researched_sources": final_ai[:10],  # Top 10 AI

            # Metadata
            "research_methods": research_methods,
            "total_found": len(all_external_sources),
            "unique_sources": len(unique_external),
            "sources_by_type": {
                "pubmed": len(final_pubmed),
                "ai_research": len(final_ai)
            },
            "ai_filtered": settings.AI_RELEVANCE_FILTERING_ENABLED,
            "parallel_execution": settings.EXTERNAL_RESEARCH_PARALLEL_EXECUTION,

            # Phase 2: Dual AI provider metadata
            "dual_ai_enabled": settings.GEMINI_GROUNDING_ENABLED,
            "dual_ai_strategy": settings.DUAL_AI_PROVIDER_STRATEGY if settings.GEMINI_GROUNDING_ENABLED else None,

            "researched_at": datetime.utcnow().isoformat()
        }

        self.db.commit()
        logger.info(
            f"Stage 4 complete: {len(final_pubmed)} PubMed + {len(final_ai)} AI = "
            f"{len(unique_external)} total sources"
        )

    async def _stage_5_synthesis_planning(self, chapter: Chapter) -> None:
        """
        Stage 5: Knowledge-First Adaptive Structure Planning (Phase 22 Enhanced)

        PHILOSOPHY: Analyze sources first, then suggest structure that organizes knowledge best.
        Templates are SUGGESTIONS that guide organization, never rigid requirements.

        Process:
        1. Gather all available sources (internal + external)
        2. Get flexible template guidance for chapter type
        3. Provide AI with knowledge-first instructions
        4. Let AI analyze sources and identify natural content clusters
        5. AI maps clusters to sections (standard or custom)
        6. Support hierarchical organization WHERE APPROPRIATE
        7. NEVER discard content to fit template

        Note: external_sources includes BOTH PubMed papers AND AI-researched sources.
        Source types are tracked internally but treated uniformly for seamless integration.
        """
        logger.info(f"Stage 5: Knowledge-first adaptive planning for chapter {chapter.id}")
        chapter.generation_status = "stage_5_planning"
        self.db.commit()

        # Gather all research (external_sources contains both PubMed AND AI sources)
        internal_sources = (chapter.stage_3_internal_research or {}).get("sources", [])
        external_sources = (chapter.stage_4_external_research or {}).get("sources", [])

        # Optional: Track source breakdown for analytics (internal use only)
        stage_4_data = chapter.stage_4_external_research or {}
        sources_by_type = stage_4_data.get("sources_by_type", {})
        if sources_by_type:
            logger.info(
                f"Source breakdown: {len(internal_sources)} internal, "
                f"{sources_by_type.get('pubmed', 0)} PubMed, "
                f"{sources_by_type.get('ai_research', 0)} AI-researched"
            )

        # Build source summary
        source_summary = self._summarize_sources(internal_sources, external_sources)

        # Get flexible template guidance based on chapter type
        try:
            chapter_type_enum = ChapterType(chapter.chapter_type)
        except (ValueError, TypeError):
            chapter_type_enum = ChapterType.SURGICAL_DISEASE  # Default

        template_guidance = ChapterTemplateGuidance.suggest_structure_from_knowledge(
            available_sources=internal_sources + external_sources,
            chapter_type=chapter_type_enum,
            topic=chapter.title
        )

        # Extract context for AI planning
        context_data = (chapter.stage_2_context or {}).get('context', {})

        # Knowledge-first adaptive planning prompt
        prompt = f"""
        KNOWLEDGE-FIRST CHAPTER STRUCTURE PLANNING

        Your task: Analyze available sources, identify natural content clusters, then organize them into a logical chapter structure.

        Topic: "{chapter.title}"
        Chapter Type: {chapter.chapter_type}

        Available Knowledge:
        - {len(internal_sources)} internal sources (from indexed neurosurgical library)
        - {len(external_sources)} external sources (PubMed + AI research)
        - Total: {len(internal_sources) + len(external_sources)} sources

        Context Intelligence:
        {json.dumps(context_data, indent=2)}

        Source Summary:
        {source_summary}

        TEMPLATE GUIDANCE (FLEXIBLE SUGGESTIONS - NOT RIGID REQUIREMENTS):
        {json.dumps(template_guidance, indent=2)}

        CRITICAL INSTRUCTIONS:

        1. KNOWLEDGE-FIRST APPROACH:
           - Analyze what knowledge is ACTUALLY available in the sources
           - Identify natural themes and content clusters
           - Let content guide structure, not templates
           - NEVER discard valuable content because it doesn't fit a template

        2. FLEXIBLE SECTION MAPPING:
           - Use suggested section types WHERE THEY FIT naturally
           - Create CUSTOM sections for unique content that doesn't fit standard types
           - Adapt section titles to match actual content
           - Merge sections if content is limited
           - Split sections if content is extensive

        3. HIERARCHICAL ORGANIZATION:
           - Support up to 4 levels: Chapter → Section → Subsection → Sub-subsection
           - Use subsections ONLY where they enhance clarity
           - Not all sections need subsections
           - Some sections may be deeper than others - adapt to content
           - Depth should match content complexity, not template

        4. CONTENT PRESERVATION:
           - Every piece of valuable knowledge must find a home
           - If content doesn't fit standard sections, create custom ones
           - Prioritize logical flow over template adherence
           - Quality of organization > conformity to template

        5. SECTION PLANNING:
           For each section, specify:
           - title: Clear, descriptive title
           - section_type: Use standard types where appropriate or "custom"
           - key_points: Main topics to cover (based on ACTUAL sources)
           - word_count_estimate: Realistic estimate based on available content
           - subsections: Array of subsections (if needed for organization)
           - source_allocation: Which sources are most relevant
           - image_suggestions: Where images would enhance understanding

        Return as JSON with this structure:
        {{
          "planning_approach": "Brief explanation of how you analyzed sources and chose structure",
          "content_clusters_identified": ["List of natural themes found in sources"],
          "sections": [
            {{
              "title": "Section Title",
              "section_type": "introduction|epidemiology|pathophysiology|...|custom",
              "rationale": "Why this section and structure",
              "key_points": ["Point 1", "Point 2", ...],
              "word_count_estimate": 500,
              "subsections": [
                {{
                  "title": "Subsection Title",
                  "key_points": ["Point 1", "Point 2"],
                  "word_count_estimate": 200
                }}
              ],
              "source_allocation": "Which sources best inform this section",
              "image_suggestions": ["Suggested image 1", ...]
            }}
          ],
          "custom_sections_rationale": "Explanation of any custom sections created",
          "template_adaptations": "How you adapted suggested templates to fit actual knowledge"
        }}

        Remember: Your goal is to organize ALL available knowledge in the most logical, clear, and comprehensive way.
        Templates guide you, but knowledge preservation and logical flow are paramount.
        """

        response = await self.ai_service.generate_text(
            prompt=prompt,
            task=AITask.CHAPTER_GENERATION,
            max_tokens=3000,  # Increased for detailed planning
            temperature=0.6  # Slight increase for adaptive creativity
        )

        try:
            outline = json.loads(response["text"])
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI outline response, using fallback structure")
            # Fallback structure
            outline = {
                "planning_approach": "Fallback structure due to parsing error",
                "sections": [
                    {"title": "Introduction", "section_type": "introduction", "key_points": [], "word_count_estimate": 300},
                    {"title": "Main Content", "section_type": "custom", "key_points": [], "word_count_estimate": 1000},
                    {"title": "Conclusion", "section_type": "custom", "key_points": [], "word_count_estimate": 200}
                ]
            }

        # Validate flexible structure (suggestions, not enforcement)
        validation = ChapterTemplateGuidance.validate_structure_flexibility(outline)
        if not validation["valid"]:
            logger.warning(f"Structure validation issues: {validation['issues']}")
        if validation["suggestions"]:
            logger.info(f"Structure suggestions: {validation['suggestions']}")

        # Store comprehensive planning metadata
        chapter.stage_5_synthesis_metadata = {
            "outline": outline,
            "template_guidance_used": template_guidance,
            "total_sections": len(outline.get("sections", [])),
            "estimated_total_words": sum(
                s.get("word_count_estimate", 0) for s in outline.get("sections", [])
            ),
            "structure_validation": validation,
            "planned_at": datetime.utcnow().isoformat(),
            "ai_cost_usd": response.get("cost_usd", 0.0),
            "knowledge_first_approach": True,
            "template_flexibility": "high"
        }

        # Also store simplified version in structure_metadata for backward compatibility
        chapter.structure_metadata = {
            "outline": outline,
            "total_sections": len(outline.get("sections", [])),
            "estimated_total_words": sum(
                s.get("word_count_estimate", 0) for s in outline.get("sections", [])
            ),
            "planned_at": datetime.utcnow().isoformat()
        }

        self.db.commit()
        logger.info(
            f"Stage 5 complete: Planned {len(outline.get('sections', []))} sections "
            f"using knowledge-first adaptive approach"
        )

    async def _stage_6_section_generation(self, chapter: Chapter) -> None:
        """
        Stage 6: Flexible Content Generation with Section-Type Awareness (Phase 22 Enhanced)

        PHILOSOPHY: Use section-type hints to guide generation, but maintain flexibility.
        Support hierarchical structure and track sources per section.

        PERFORMANCE: Parallel section generation (configurable batch size)
        - Sequential: 97 sections × 7s = ~11 minutes
        - Parallel (batch=5): 20 batches × 7s = ~2.3 minutes (4.8x faster)
        - Parallel (batch=10): 10 batches × 7s = ~1.2 minutes (9.2x faster)

        Process:
        1. Get section plan from Stage 5 (with section types and subsections)
        2. For each section, get type-specific generation hints (if available)
        3. Allocate relevant sources per section (intelligent matching)
        4. Generate main section content (PARALLEL if enabled)
        5. Generate subsections recursively (if present)
        6. Track which sources were actually used
        7. Preserve all content even if it doesn't fit perfectly

        Note: external_sources includes BOTH PubMed papers AND AI-researched sources.
        Source types are tracked internally for analytics but presented uniformly to the AI
        to ensure seamless integration and consistent citation style.
        """
        logger.info(f"Stage 6: Flexible section generation for chapter {chapter.id}")
        chapter.generation_status = "stage_6_generation"
        self.db.commit()

        # Get enhanced outline from Stage 5
        stage_5_metadata = chapter.stage_5_synthesis_metadata or {}
        outline = stage_5_metadata.get("outline", {})
        sections_plan = outline.get("sections", [])

        internal_sources = (chapter.stage_3_internal_research or {}).get("sources", [])
        external_sources = (chapter.stage_4_external_research or {}).get("sources", [])
        all_sources = internal_sources + external_sources

        # Track source breakdown for analytics (internal use only)
        stage_4_data = chapter.stage_4_external_research or {}
        sources_by_type = stage_4_data.get("sources_by_type", {})
        if sources_by_type:
            logger.info(
                f"Section generation sources: {len(internal_sources)} internal, "
                f"{sources_by_type.get('pubmed', 0)} PubMed, "
                f"{sources_by_type.get('ai_research', 0)} AI-researched"
            )

        # Choose parallel or sequential generation based on configuration
        if settings.PARALLEL_SECTION_GENERATION and len(sections_plan) > 1:
            logger.info(
                f"Using PARALLEL section generation: {len(sections_plan)} sections "
                f"in batches of {settings.SECTION_GENERATION_BATCH_SIZE}"
            )
            generated_sections, total_cost = await self._generate_sections_parallel(
                chapter=chapter,
                sections_plan=sections_plan,
                all_sources=all_sources
            )
        else:
            logger.info(f"Using SEQUENTIAL section generation: {len(sections_plan)} sections")
            generated_sections, total_cost = await self._generate_sections_sequential(
                chapter=chapter,
                sections_plan=sections_plan,
                all_sources=all_sources
            )

        # Store generated sections with hierarchical structure
        chapter.sections = generated_sections

        # Update stage 5 metadata with actual generation stats
        if chapter.stage_5_synthesis_metadata:
            chapter.stage_5_synthesis_metadata["generation_stats"] = {
                "total_sections_generated": len(generated_sections),
                "total_subsections_generated": sum(
                    len(s.get("subsections", [])) for s in generated_sections
                ),
                "total_cost_usd": total_cost,
                "generated_at": datetime.utcnow().isoformat(),
                "generation_mode": "parallel" if settings.PARALLEL_SECTION_GENERATION else "sequential"
            }

        self.db.commit()
        logger.info(
            f"Stage 6 complete: Generated {len(generated_sections)} sections "
            f"with hierarchical structure, ${total_cost:.4f}"
        )

        # Automatic Gap Analysis (if enabled)
        if settings.AUTO_GAP_ANALYSIS_ENABLED:
            await self._run_automatic_gap_analysis(chapter)

    async def _run_automatic_gap_analysis(self, chapter: Chapter) -> None:
        """
        Run automatic gap analysis after section generation

        Benefits:
        - Early detection of missing content
        - Identifies unused research sources
        - Flags unbalanced sections
        - Provides actionable recommendations

        Triggered: After Stage 6 (section generation)
        Configurable: AUTO_GAP_ANALYSIS_ENABLED setting
        """
        try:
            logger.info(f"Running automatic gap analysis for chapter {chapter.id}")

            from backend.services.gap_analyzer import GapAnalyzer

            # Prepare data for gap analyzer
            chapter_data = {
                "id": str(chapter.id),
                "title": chapter.title,
                "sections": chapter.sections or [],
                "chapter_type": chapter.chapter_type
            }

            internal_sources = (chapter.stage_3_internal_research or {}).get("sources", [])
            external_sources = (chapter.stage_4_external_research or {}).get("sources", [])
            stage_2_context = chapter.stage_2_context or {}

            # Run gap analysis
            analyzer = GapAnalyzer()
            gap_results = await analyzer.analyze_chapter_gaps(
                chapter=chapter_data,
                internal_sources=internal_sources,
                external_sources=external_sources,
                stage_2_context=stage_2_context
            )

            # Store gap analysis results
            chapter.gap_analysis = gap_results

            # Log results
            total_gaps = gap_results.get("total_gaps", 0)
            critical_gaps = gap_results["severity_distribution"]["critical"]
            high_gaps = gap_results["severity_distribution"]["high"]
            completeness = gap_results.get("overall_completeness_score", 0.0)
            requires_revision = gap_results.get("requires_revision", False)

            logger.info(
                f"Gap analysis complete: {total_gaps} gaps identified "
                f"(Critical: {critical_gaps}, High: {high_gaps}), "
                f"Completeness: {completeness:.1%}, "
                f"Requires revision: {requires_revision}"
            )

            # Handle critical gaps
            if critical_gaps > 0 and settings.HALT_ON_CRITICAL_GAPS:
                logger.error(
                    f"CRITICAL GAPS DETECTED: {critical_gaps} critical gaps found. "
                    f"Halting generation as per HALT_ON_CRITICAL_GAPS setting."
                )
                chapter.generation_status = "gaps_detected_critical"
                self.db.commit()

                # Emit WebSocket notification
                await self.emit_chapter_progress(
                    chapter_id=str(chapter.id),
                    stage="gap_analysis_critical",
                    stage_number=6,
                    message=f"Critical gaps detected: {critical_gaps} issues require review",
                    progress_percent=40
                )

                raise Exception(
                    f"Critical gaps detected: {critical_gaps} gaps require manual review. "
                    f"Recommendations: {gap_results.get('recommendations', [])[:3]}"
                )

            # Emit warning for non-critical gaps
            elif requires_revision:
                logger.warning(
                    f"Gap analysis recommends revision: "
                    f"{high_gaps} high-severity gaps, "
                    f"{completeness:.1%} completeness"
                )

                # Emit WebSocket notification (non-blocking)
                await self.emit_chapter_progress(
                    chapter_id=str(chapter.id),
                    stage="gap_analysis_warning",
                    stage_number=6,
                    message=f"Quality advisory: {total_gaps} gaps detected (review recommended)",
                    progress_percent=40
                )

            self.db.commit()

        except Exception as e:
            # Don't halt generation on gap analysis failure (non-critical)
            logger.error(
                f"Automatic gap analysis failed: {str(e)}. "
                f"Continuing with chapter generation.",
                exc_info=True
            )
            chapter.gap_analysis = {
                "error": str(e),
                "analyzed_at": datetime.utcnow().isoformat(),
                "status": "failed"
            }
            self.db.commit()

    async def _generate_sections_parallel(
        self,
        chapter: Chapter,
        sections_plan: List[Dict],
        all_sources: List[Dict]
    ) -> tuple[List[Dict], float]:
        """
        Generate sections in parallel batches for maximum performance

        Returns:
            Tuple of (generated_sections, total_cost)

        Performance Benefits:
            - 97 sections: 679s → 68s (10x faster)
            - Configurable batch size balances speed vs API limits
            - Error handling per section (failures don't abort entire batch)
        """
        import asyncio

        generated_sections = []
        total_cost = 0.0
        batch_size = settings.SECTION_GENERATION_BATCH_SIZE

        # Process sections in batches
        for batch_start in range(0, len(sections_plan), batch_size):
            batch_end = min(batch_start + batch_size, len(sections_plan))
            batch_sections = sections_plan[batch_start:batch_end]

            logger.info(
                f"Processing batch {batch_start//batch_size + 1}: "
                f"sections {batch_start+1}-{batch_end} of {len(sections_plan)}"
            )

            # Create tasks for parallel generation
            tasks = []
            for idx, section_plan in enumerate(batch_sections):
                actual_idx = batch_start + idx
                task = self._generate_single_section(
                    chapter=chapter,
                    section_plan=section_plan,
                    section_idx=actual_idx,
                    all_sources=all_sources
                )
                tasks.append(task)

            # Execute batch in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for idx, result in enumerate(batch_results):
                actual_idx = batch_start + idx

                if isinstance(result, Exception):
                    # Section generation failed - log error but continue
                    logger.error(
                        f"Section {actual_idx + 1} generation failed: {str(result)}",
                        exc_info=result
                    )
                    # Create placeholder section
                    section_data = {
                        "section_num": actual_idx + 1,
                        "title": batch_sections[idx].get('title', f'Section {actual_idx + 1}'),
                        "section_type": batch_sections[idx].get('section_type', 'custom'),
                        "content": f"<p><em>Error generating section: {str(result)[:200]}</em></p>",
                        "word_count": 0,
                        "sources_used": [],
                        "generated_at": datetime.utcnow().isoformat(),
                        "generation_error": str(result),
                        "ai_model": "error",
                        "ai_cost_usd": 0.0
                    }
                    generated_sections.append(section_data)
                else:
                    # Success
                    section_data, section_cost = result
                    generated_sections.append(section_data)
                    total_cost += section_cost

            # Emit batch progress
            progress_percent = int((batch_end / len(sections_plan)) * 60)  # Stage 6 is 35-60%
            await self.emit_chapter_progress(
                chapter_id=str(chapter.id),
                stage="stage_6_generation",
                stage_number=6,
                message=f"Generated {batch_end}/{len(sections_plan)} sections",
                progress_percent=35 + progress_percent
            )

        # Sort sections by section_num to ensure correct order
        generated_sections.sort(key=lambda s: s["section_num"])

        logger.info(
            f"Parallel generation complete: {len(generated_sections)} sections, "
            f"${total_cost:.4f}"
        )

        return generated_sections, total_cost

    async def _generate_sections_sequential(
        self,
        chapter: Chapter,
        sections_plan: List[Dict],
        all_sources: List[Dict]
    ) -> tuple[List[Dict], float]:
        """
        Generate sections sequentially (original implementation, fallback mode)

        Returns:
            Tuple of (generated_sections, total_cost)

        Use Cases:
            - Single section chapters
            - Debugging/testing
            - When PARALLEL_SECTION_GENERATION=False
        """
        generated_sections = []
        total_cost = 0.0

        for idx, section_plan in enumerate(sections_plan):
            logger.info(
                f"Generating section {idx + 1}/{len(sections_plan)}: "
                f"{section_plan.get('title', f'Section {idx + 1}')}"
            )

            try:
                section_data, section_cost = await self._generate_single_section(
                    chapter=chapter,
                    section_plan=section_plan,
                    section_idx=idx,
                    all_sources=all_sources
                )
                generated_sections.append(section_data)
                total_cost += section_cost

            except Exception as e:
                logger.error(
                    f"Section {idx + 1} generation failed: {str(e)}",
                    exc_info=e
                )
                # Create placeholder
                section_data = {
                    "section_num": idx + 1,
                    "title": section_plan.get('title', f'Section {idx + 1}'),
                    "section_type": section_plan.get('section_type', 'custom'),
                    "content": f"<p><em>Error generating section: {str(e)[:200]}</em></p>",
                    "word_count": 0,
                    "sources_used": [],
                    "generated_at": datetime.utcnow().isoformat(),
                    "generation_error": str(e),
                    "ai_model": "error",
                    "ai_cost_usd": 0.0
                }
                generated_sections.append(section_data)

            # Emit progress
            progress_percent = int(((idx + 1) / len(sections_plan)) * 60)
            await self.emit_chapter_progress(
                chapter_id=str(chapter.id),
                stage="stage_6_generation",
                stage_number=6,
                message=f"Generated {idx + 1}/{len(sections_plan)} sections",
                progress_percent=35 + progress_percent
            )

        logger.info(
            f"Sequential generation complete: {len(generated_sections)} sections, "
            f"${total_cost:.4f}"
        )

        return generated_sections, total_cost

    async def _generate_single_section(
        self,
        chapter: Chapter,
        section_plan: Dict,
        section_idx: int,
        all_sources: List[Dict]
    ) -> tuple[Dict, float]:
        """
        Generate a single section (main content + subsections)

        Returns:
            Tuple of (section_data_dict, section_cost)

        This method handles:
        - Section-type hints
        - Source allocation
        - Main section content generation
        - Subsection generation (sequential, as they depend on parent context)
        - Cost tracking
        """
        section_title = section_plan.get('title', f'Section {section_idx + 1}')
        section_type = section_plan.get('section_type', 'custom')

        # Get section-type specific hints
        section_hints = {}
        if section_type != 'custom':
            try:
                from backend.services.templates.chapter_template_guidance import SectionType, ChapterTemplateGuidance
                section_type_enum = SectionType(section_type)
                section_hints = ChapterTemplateGuidance.get_section_type_hints(section_type_enum)
            except (ValueError, ImportError):
                section_hints = {}

        # Allocate relevant sources
        source_allocation_hint = section_plan.get('source_allocation', '')
        relevant_sources = self._allocate_sources_for_section(
            section_plan=section_plan,
            all_sources=all_sources,
            allocation_hint=source_allocation_hint
        )

        # Generate main section content
        section_generation_result = await self._generate_section_content(
            chapter_title=chapter.title,
            section_plan=section_plan,
            section_hints=section_hints,
            relevant_sources=relevant_sources,
            section_num=section_idx + 1
        )

        section_content = section_generation_result["content"]
        word_count = section_generation_result["word_count"]
        sources_used = section_generation_result.get("sources_used", [])
        section_cost = section_generation_result["cost_usd"]

        # Build section structure
        section_data = {
            "section_num": section_idx + 1,
            "title": section_title,
            "section_type": section_type,
            "content": section_content,
            "word_count": word_count,
            "sources_used": sources_used,
            "generated_at": datetime.utcnow().isoformat(),
            "ai_model": section_generation_result["model"],
            "ai_cost_usd": section_generation_result["cost_usd"]
        }

        # Generate subsections if present (SEQUENTIAL - they depend on parent context)
        subsections = section_plan.get('subsections', [])
        if subsections:
            logger.debug(f"  Generating {len(subsections)} subsections for '{section_title}'")
            generated_subsections = []

            for sub_idx, subsection_plan in enumerate(subsections):
                subsection_result = await self._generate_subsection_content(
                    chapter_title=chapter.title,
                    parent_section_title=section_title,
                    subsection_plan=subsection_plan,
                    relevant_sources=relevant_sources,
                    subsection_num=sub_idx + 1
                )

                generated_subsections.append({
                    "subsection_num": sub_idx + 1,
                    "title": subsection_plan.get('title'),
                    "content": subsection_result["content"],
                    "word_count": subsection_result["word_count"],
                    "sources_used": subsection_result.get("sources_used", []),
                    "generated_at": datetime.utcnow().isoformat()
                })

                section_cost += subsection_result.get("cost_usd", 0.0)

            section_data["subsections"] = generated_subsections
            section_data["has_subsections"] = True

        return section_data, section_cost

    async def _stage_7_image_integration(self, chapter: Chapter) -> None:
        """
        Stage 7: Semantic Image Integration (Phase 22 Enhanced)

        PHILOSOPHY: Match images to sections based on content relevance,
        not linear distribution. Images should enhance understanding
        where they're most relevant.

        Process:
        1. Get available images from Stage 3 research
        2. For each section, analyze content and find most relevant images
        3. Match images semantically using keywords and content
        4. Allow multiple images per section if relevant
        5. Generate contextual captions for each image placement
        6. Track image usage to avoid duplication
        """
        logger.info(f"Stage 7: Semantic image integration for chapter {chapter.id}")
        chapter.generation_status = "stage_7_images"
        self.db.commit()

        images = (chapter.stage_3_internal_research or {}).get("images", [])
        sections = chapter.sections or []

        if not images:
            logger.info("No images available for integration")
            self.db.commit()
            return

        logger.info(f"Semantically matching {len(images)} images to {len(sections)} sections")

        # Track which images have been used
        used_image_ids = set()

        # Process each section (including subsections)
        for section_idx, section in enumerate(sections):
            section_title = section.get("title", "")
            section_content = section.get("content", "")
            section_type = section.get("section_type", "custom")

            # Find relevant images for this section
            relevant_images = self._match_images_to_content(
                section_title=section_title,
                section_content=section_content,
                section_type=section_type,
                available_images=images,
                used_image_ids=used_image_ids
            )

            # Generate contextual captions for matched images
            section_images_with_captions = []
            for image in relevant_images:
                caption = await self._generate_image_caption(
                    image=image,
                    section_title=section_title,
                    section_context=section_content[:500]  # First 500 chars for context
                )

                section_images_with_captions.append({
                    "image_id": image.get("id"),
                    "file_path": image.get("file_path"),
                    "caption": caption,
                    "relevance_score": image.get("_relevance_score", 0.0),
                    "source_pdf": image.get("source_pdf")
                })

                # Mark image as used
                image_id = image.get("id")
                if image_id:
                    used_image_ids.add(image_id)

            section["images"] = section_images_with_captions

            # Process subsections if present
            subsections = section.get("subsections", [])
            for subsection in subsections:
                subsection_title = subsection.get("title", "")
                subsection_content = subsection.get("content", "")

                # Find images for subsection
                subsection_images = self._match_images_to_content(
                    section_title=f"{section_title} - {subsection_title}",
                    section_content=subsection_content,
                    section_type=section_type,
                    available_images=images,
                    used_image_ids=used_image_ids,
                    max_images=2  # Limit subsections to 2 images each
                )

                subsection_images_with_captions = []
                for image in subsection_images:
                    caption = await self._generate_image_caption(
                        image=image,
                        section_title=subsection_title,
                        section_context=subsection_content[:300]
                    )

                    subsection_images_with_captions.append({
                        "image_id": image.get("id"),
                        "file_path": image.get("file_path"),
                        "caption": caption,
                        "relevance_score": image.get("_relevance_score", 0.0)
                    })

                    image_id = image.get("id")
                    if image_id:
                        used_image_ids.add(image_id)

                subsection["images"] = subsection_images_with_captions

        chapter.sections = sections

        self.db.commit()
        logger.info(
            f"Stage 7 complete: Semantically integrated {len(used_image_ids)}/{len(images)} images "
            f"across sections and subsections"
        )

    async def _stage_8_citation_network(self, chapter: Chapter) -> None:
        """
        Stage 8: Build citation network (Dual-Source Citations)

        - Extract citations from sections
        - Create reference list from all sources (internal PDFs, PubMed, AI-researched)
        - Link to source PDFs and external URLs
        - Preserve source type metadata for analytics (internal/pubmed/ai_research)

        Note: Source types are tracked internally but references are presented uniformly
        to maintain consistent citation style regardless of source origin.
        """
        logger.info(f"Stage 8: Citation network for chapter {chapter.id}")
        chapter.generation_status = "stage_8_citations"
        self.db.commit()

        internal_sources = (chapter.stage_3_internal_research or {}).get("sources", [])
        external_sources = (chapter.stage_4_external_research or {}).get("sources", [])

        all_sources = internal_sources + external_sources

        # Build reference list with source type tracking
        references = []
        for idx, source in enumerate(all_sources):
            ref = {
                "ref_num": idx + 1,
                "title": source.get("title"),
                "authors": source.get("authors", []),
                "year": source.get("year"),
                "journal": source.get("journal"),
                "doi": source.get("doi"),
                "pmid": source.get("pmid"),
                "pdf_id": source.get("pdf_id"),
                "source_type": source.get("source_type", "internal"),  # Track: internal/pubmed/ai_research
                "url": source.get("url")  # External URL for PubMed/AI citations
            }
            references.append(ref)

        chapter.references = references

        self.db.commit()
        logger.info(f"Stage 8 complete: Created {len(references)} references")

    async def _stage_9_quality_assurance(self, chapter: Chapter) -> None:
        """
        Stage 9: Quality assurance

        - Calculate quality scores (depth, coverage, currency, evidence)
        - Check completeness
        - Identify gaps
        """
        logger.info(f"Stage 9: Quality assurance for chapter {chapter.id}")
        chapter.generation_status = "stage_9_qa"
        self.db.commit()

        sections = chapter.sections or []
        total_words = sum(s.get("word_count", 0) for s in sections)
        references_count = len(chapter.references or [])

        # Calculate scores
        depth_score = min(1.0, total_words / 2000)  # Target: 2000 words
        coverage_score = min(1.0, len(sections) / 5)  # Target: 5 sections
        evidence_score = min(1.0, references_count / 15)  # Target: 15 references

        # Calculate currency score based on actual source publication years
        currency_score = self._calculate_currency_score(chapter)

        chapter.depth_score = depth_score
        chapter.coverage_score = coverage_score
        chapter.evidence_score = evidence_score
        chapter.currency_score = currency_score

        self.db.commit()
        logger.info(f"Stage 9 complete: Scores - Depth: {depth_score:.2f}, Coverage: {coverage_score:.2f}, Currency: {currency_score:.2f}")

    async def _stage_10_fact_checking(self, chapter: Chapter) -> None:
        """
        Stage 10: Medical fact-checking using GPT-4o

        - Uses FactCheckingService with structured outputs
        - Cross-references claims with research sources
        - Verifies anatomy, pathophysiology, diagnosis, treatment claims
        - Assigns confidence scores and severity assessments
        - Flags critical issues requiring attention
        - Stores detailed fact-check results in stage_10_fact_check JSONB

        Phase 3: Enhanced with GPT-4o structured outputs for reliable verification
        """
        logger.info(f"Stage 10: Medical fact-checking for chapter {chapter.id}")
        chapter.generation_status = "stage_10_fact_check"
        self.db.commit()

        # Gather all research sources for verification
        internal_sources = (chapter.stage_3_internal_research or {}).get("sources", [])
        external_sources = (chapter.stage_4_external_research or {}).get("sources", [])
        all_sources = internal_sources + external_sources

        if not all_sources:
            logger.warning(f"No sources available for fact-checking chapter {chapter.id}")
            # Still mark as checked but with low confidence
            chapter.fact_checked = True
            chapter.fact_check_passed = False
            chapter.stage_10_fact_check = {
                "status": "no_sources",
                "message": "Fact-checking skipped - no sources available",
                "checked_at": datetime.utcnow().isoformat()
            }
            self.db.commit()
            return

        sections = chapter.sections or []
        if not sections:
            logger.warning(f"No sections to fact-check for chapter {chapter.id}")
            chapter.fact_checked = True
            chapter.fact_check_passed = True
            self.db.commit()
            return

        try:
            # Use GPT-4o fact-checking service with structured outputs
            fact_check_results = await self.fact_check_service.fact_check_chapter(
                sections=sections,
                sources=all_sources,
                chapter_title=chapter.title
            )

            # Get verification summary for easy access
            summary = self.fact_check_service.get_verification_summary(fact_check_results)

            # Determine pass/fail based on accuracy and critical issues
            accuracy = fact_check_results["overall_accuracy"]
            critical_issues = fact_check_results["critical_issues_count"]
            critical_severity = fact_check_results["critical_severity_claims"]

            # Passing criteria:
            # - Accuracy >= 90% OR
            # - Accuracy >= 80% AND no critical severity issues
            # - AND no more than 2 critical issues overall
            passed = (
                (accuracy >= 0.90) or
                (accuracy >= 0.80 and critical_severity == 0)
            ) and critical_issues <= 2

            # Store comprehensive results
            chapter.fact_checked = True
            chapter.fact_check_passed = passed
            chapter.stage_10_fact_check = {
                "overall_accuracy": accuracy,
                "accuracy_percentage": accuracy * 100,
                "accuracy_grade": summary["accuracy_grade"],
                "total_claims": fact_check_results["total_claims"],
                "verified_claims": fact_check_results["verified_claims"],
                "unverified_claims": fact_check_results["unverified_claims"],
                "critical_issues": fact_check_results["all_critical_issues"],
                "critical_issues_count": critical_issues,
                "critical_severity_claims": critical_severity,
                "high_severity_claims": fact_check_results["high_severity_claims"],
                "sections_checked": fact_check_results["sections_checked"],
                "sources_used": len(all_sources),
                "by_category": summary["by_category"],
                "unverified_by_severity": summary["unverified_by_severity"],
                "requires_attention": summary["requires_attention"],
                "passed": passed,
                "ai_cost_usd": fact_check_results["total_cost_usd"],
                "checked_at": fact_check_results["checked_at"],
                "section_results": fact_check_results["section_results"]  # Detailed per-section results
            }

            self.db.commit()

            # Log comprehensive summary
            status = "PASSED ✓" if passed else "FAILED ✗"
            logger.info(
                f"Stage 10 complete: Fact-checking {status} - "
                f"{accuracy:.1%} accuracy, "
                f"{fact_check_results['verified_claims']}/{fact_check_results['total_claims']} verified, "
                f"{critical_issues} critical issues, "
                f"${fact_check_results['total_cost_usd']:.4f}"
            )

            if not passed:
                logger.warning(
                    f"Chapter {chapter.id} FAILED fact-check: "
                    f"Accuracy {accuracy:.1%}, {critical_issues} critical issues"
                )

        except Exception as e:
            logger.error(f"Fact-checking failed: {str(e)}", exc_info=True)
            # Mark as checked but failed
            chapter.fact_checked = True
            chapter.fact_check_passed = False
            chapter.stage_10_fact_check = {
                "status": "error",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
            self.db.commit()
            raise

    # ==================== Stage 11 Helper Methods ====================

    def _extract_all_headings(self, sections: List[Dict[str, Any]], parent_num: str = "") -> List[Dict[str, Any]]:
        """
        Recursively extract all headings from sections and subsections.

        Args:
            sections: List of section dictionaries
            parent_num: Parent section numbering (e.g., "1", "1.1")

        Returns:
            List of heading dictionaries with: level, title, anchor, numbering
        """
        headings = []

        for idx, section in enumerate(sections):
            section_num = f"{parent_num}{idx + 1}" if parent_num else str(idx + 1)
            title = section.get("title", f"Section {section_num}")

            # Create anchor (slugify title)
            anchor = title.lower().replace(" ", "-").replace("&", "and")
            anchor = "".join(c for c in anchor if c.isalnum() or c == "-")

            # Determine level based on nesting
            level = parent_num.count(".") + 1

            headings.append({
                "level": level,
                "title": title,
                "anchor": anchor,
                "numbering": section_num,
                "section_type": section.get("section_type", "custom")
            })

            # Recursively process subsections
            subsections = section.get("subsections", [])
            if subsections:
                child_headings = self._extract_all_headings(subsections, f"{section_num}.")
                headings.extend(child_headings)

        return headings

    def _generate_table_of_contents(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate hierarchical table of contents from sections.

        Args:
            sections: List of section dictionaries

        Returns:
            Dictionary with markdown TOC and structured data
        """
        headings = self._extract_all_headings(sections)

        if not headings:
            return {
                "markdown": "",
                "headings": [],
                "total_headings": 0
            }

        # Build markdown TOC
        toc_lines = ["## Table of Contents\n"]

        for heading in headings:
            level = heading["level"]
            title = heading["title"]
            anchor = heading["anchor"]
            numbering = heading["numbering"]

            # Indentation based on level (2 spaces per level)
            indent = "  " * (level - 1)

            # Format: "  1.1 [Title](#anchor)"
            toc_lines.append(f"{indent}{numbering}. [{title}](#{anchor})")

        markdown_toc = "\n".join(toc_lines)

        return {
            "markdown": markdown_toc,
            "headings": headings,
            "total_headings": len(headings),
            "max_depth": max(h["level"] for h in headings) if headings else 0
        }

    def _validate_markdown_structure(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate markdown structure with flexible, non-rigid checks.

        Philosophy: Provide helpful warnings, not strict failures.
        Supports knowledge-first approach - unusual structures may be valid.

        Args:
            sections: List of section dictionaries

        Returns:
            Validation results with issues categorized by severity
        """
        import re

        issues = []
        warnings = []
        statistics = {
            "total_sections": len(sections),
            "empty_sections": 0,
            "sections_with_subsections": 0,
            "total_images": 0,
            "broken_image_refs": 0,
            "citation_count": 0
        }

        def validate_section_recursive(section: Dict[str, Any], path: str = ""):
            """Recursively validate a section and its subsections"""
            title = section.get("title", "")
            content = section.get("content", "")
            section_type = section.get("section_type", "custom")

            # Check for empty content
            if not content or len(content.strip()) < 50:
                statistics["empty_sections"] += 1
                warnings.append({
                    "type": "empty_content",
                    "severity": "low",
                    "location": f"{path}{title}",
                    "message": f"Section has very little content ({len(content)} chars)"
                })

            # Validate image references
            images = section.get("images", [])
            statistics["total_images"] += len(images)

            for img in images:
                file_path = img.get("file_path", "")
                caption = img.get("caption", "")

                if not file_path:
                    statistics["broken_image_refs"] += 1
                    issues.append({
                        "type": "missing_image_path",
                        "severity": "medium",
                        "location": f"{path}{title}",
                        "message": "Image missing file_path"
                    })

                if not caption or len(caption) < 10:
                    warnings.append({
                        "type": "short_image_caption",
                        "severity": "low",
                        "location": f"{path}{title}",
                        "message": "Image has very short caption"
                    })

            # Check citation format (flexible matching)
            citation_pattern = r'\[([A-Za-z\s&]+,?\s*\d{4})\]'
            citations = re.findall(citation_pattern, content)
            statistics["citation_count"] += len(citations)

            # Validate heading hierarchy in content
            heading_matches = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
            if heading_matches:
                for i, (hashes, heading_text) in enumerate(heading_matches):
                    level = len(hashes)
                    # Subsections should use ## or ###
                    if level == 1:  # Single # is reserved for chapter title
                        warnings.append({
                            "type": "h1_in_section",
                            "severity": "low",
                            "location": f"{path}{title}",
                            "message": f"Found H1 heading '{heading_text}' - should use H2+ for sections"
                        })

            # Check subsections
            subsections = section.get("subsections", [])
            if subsections:
                statistics["sections_with_subsections"] += 1
                for idx, subsection in enumerate(subsections):
                    validate_section_recursive(subsection, f"{path}{title} > ")

        # Validate all top-level sections
        for section in sections:
            validate_section_recursive(section)

        # Summary assessment
        total_issues = len(issues) + len(warnings)
        severity_counts = {
            "critical": len([i for i in issues if i.get("severity") == "critical"]),
            "medium": len([i for i in issues if i.get("severity") == "medium"]),
            "low": len([i for i in issues + warnings if i.get("severity") == "low"])
        }

        return {
            "valid": severity_counts["critical"] == 0,  # Valid if no critical issues
            "issues": issues,
            "warnings": warnings,
            "total_issues": total_issues,
            "severity_counts": severity_counts,
            "statistics": statistics,
            "philosophy_note": "Flexible validation - warnings are suggestions, not requirements"
        }

    def _normalize_markdown_formatting(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply consistent markdown formatting to sections.

        Philosophy: Enhance readability without altering content meaning.

        Args:
            sections: List of section dictionaries

        Returns:
            Updated sections with normalized formatting
        """
        import re

        def normalize_content(content: str) -> str:
            """Normalize markdown content"""
            if not content:
                return content

            # Ensure consistent spacing after headers
            content = re.sub(r'(#{1,6}\s+.+)\n([^\n])', r'\1\n\n\2', content)

            # Ensure consistent spacing between paragraphs
            content = re.sub(r'\n{3,}', '\n\n', content)

            # Normalize citation format: ensure space before citation if missing
            content = re.sub(r'(\w)\[([A-Za-z])', r'\1 [\2', content)

            # Ensure line break after images
            content = re.sub(r'(!\[.+\]\(.+\))([^\n])', r'\1\n\n\2', content)

            # Remove trailing whitespace from lines
            content = '\n'.join(line.rstrip() for line in content.split('\n'))

            # Ensure content ends with single newline
            content = content.rstrip() + '\n'

            return content

        def normalize_section_recursive(section: Dict[str, Any]) -> Dict[str, Any]:
            """Recursively normalize a section"""
            # Normalize content
            if "content" in section:
                section["content"] = normalize_content(section["content"])

            # Normalize subsections
            if "subsections" in section and section["subsections"]:
                section["subsections"] = [
                    normalize_section_recursive(subsec)
                    for subsec in section["subsections"]
                ]

            return section

        # Normalize all sections
        normalized_sections = [normalize_section_recursive(sec.copy()) for sec in sections]

        return normalized_sections

    # ==================== Stage 11 Main Method ====================

    async def _stage_11_formatting(self, chapter: Chapter) -> None:
        """
        Stage 11: Markdown Validation, TOC Generation, and Formatting (Phase 22 Enhanced)

        Comprehensive formatting stage with:
        - Markdown structure validation (flexible, not rigid)
        - Table of contents generation (up to 4 levels)
        - Formatting normalization (spacing, citations, images)
        - Structure validation with helpful warnings

        Philosophy: Enhance readability and organization without constraining content.
        All validation is flexible - warnings guide improvements but don't block delivery.
        """
        logger.info(f"Stage 11: Formatting and validation for chapter {chapter.id}")
        chapter.generation_status = "stage_11_formatting"
        self.db.commit()

        sections = chapter.sections or []
        if not sections:
            logger.warning(f"Chapter {chapter.id} has no sections - skipping formatting")
            chapter.stage_11_formatting = {
                "skipped": True,
                "reason": "No sections available for formatting",
                "formatted_at": datetime.utcnow().isoformat()
            }
            self.db.commit()
            return

        try:
            # Step 1: Validate markdown structure
            logger.info("Validating markdown structure...")
            validation_results = self._validate_markdown_structure(sections)

            # Step 2: Generate table of contents
            logger.info("Generating table of contents...")
            toc = self._generate_table_of_contents(sections)

            # Step 3: Normalize markdown formatting
            logger.info("Normalizing markdown formatting...")
            formatted_sections = self._normalize_markdown_formatting(sections)

            # Step 4: Update chapter with formatted sections
            chapter.sections = formatted_sections

            # Step 5: Store comprehensive results
            chapter.stage_11_formatting = {
                "toc": toc,
                "validation": validation_results,
                "statistics": {
                    "total_sections": len(sections),
                    "total_headings": toc["total_headings"],
                    "max_depth": toc["max_depth"],
                    "total_issues": validation_results["total_issues"],
                    "critical_issues": validation_results["severity_counts"]["critical"],
                    "medium_issues": validation_results["severity_counts"]["medium"],
                    "low_warnings": validation_results["severity_counts"]["low"],
                    "empty_sections": validation_results["statistics"]["empty_sections"],
                    "sections_with_subsections": validation_results["statistics"]["sections_with_subsections"],
                    "total_images": validation_results["statistics"]["total_images"],
                    "citation_count": validation_results["statistics"]["citation_count"]
                },
                "formatted_at": datetime.utcnow().isoformat(),
                "philosophy": "Flexible validation and formatting - knowledge preservation first"
            }

            self.db.commit()

            # Log summary
            logger.info(
                f"Stage 11 complete: "
                f"TOC generated ({toc['total_headings']} headings, {toc['max_depth']} levels), "
                f"Validation: {validation_results['severity_counts']['critical']} critical, "
                f"{validation_results['severity_counts']['medium']} medium, "
                f"{validation_results['severity_counts']['low']} low issues"
            )

            # Emit WebSocket event for progress
            await emitter.emit_chapter_progress(
                chapter_id=str(chapter.id),
                stage=ChapterStage.STAGE_11_FORMATTING,
                stage_number=11,
                message=f"Formatting complete: {toc['total_headings']} headings, {validation_results['total_issues']} issues",
                details={
                    "toc_headings": toc["total_headings"],
                    "max_depth": toc["max_depth"],
                    "validation_status": "passed" if validation_results["valid"] else "warnings",
                    "total_issues": validation_results["total_issues"],
                    "critical_issues": validation_results["severity_counts"]["critical"],
                    "medium_issues": validation_results["severity_counts"]["medium"],
                    "low_warnings": validation_results["severity_counts"]["low"]
                }
            )

        except Exception as e:
            logger.error(f"Stage 11 formatting failed: {str(e)}", exc_info=True)
            chapter.stage_11_formatting = {
                "status": "error",
                "error": str(e),
                "formatted_at": datetime.utcnow().isoformat()
            }
            self.db.commit()
            raise

    async def _stage_12_review_refinement(self, chapter: Chapter) -> None:
        """
        Stage 12: Review and refine

        Comprehensive AI-powered quality review using GPT-4o structured outputs:
        - Internal contradictions between sections
        - Readability issues (medical jargon overuse, unclear explanations)
        - Missing transitions between sections
        - Citation consistency and quality
        - Logical flow problems
        - Overall quality assessment with actionable improvement suggestions

        This stage produces detailed, structured feedback that can be:
        1. Displayed to users for manual refinement
        2. Used to auto-apply minor fixes (future enhancement)
        3. Tracked over versions to measure quality improvement
        """
        logger.info(f"Stage 12: Review and refinement for chapter {chapter.id}")
        chapter.generation_status = "stage_12_review"
        self.db.commit()

        # Prepare chapter content for review
        sections = chapter.sections or []
        if not sections:
            logger.warning(f"Chapter {chapter.id} has no sections - skipping review")
            chapter.stage_12_review = {
                "skipped": True,
                "reason": "No sections available for review",
                "reviewed_at": datetime.utcnow().isoformat()
            }
            self.db.commit()
            logger.info("Stage 12 complete: Review skipped (no content)")
            return

        # Build comprehensive context for review
        section_summaries = []
        for i, section in enumerate(sections):
            section_title = section.get("title", f"Section {i+1}")
            section_content = section.get("content", "")
            word_count = section.get("word_count", 0)

            # Create brief preview (first 200 chars)
            content_preview = section_content[:200] + "..." if len(section_content) > 200 else section_content

            section_summaries.append(
                f"**{section_title}** ({word_count} words)\n{content_preview}"
            )

        # Get chapter metadata for context
        chapter_type = chapter.chapter_type or "general"
        title = chapter.title or "Untitled"

        # Get quality scores for additional context
        quality_context = ""
        if chapter.depth_score:
            quality_context = f"""
Current Quality Scores:
- Depth: {chapter.depth_score:.2f}
- Coverage: {chapter.coverage_score:.2f}
- Currency: {chapter.currency_score:.2f}
- Evidence: {chapter.evidence_score:.2f}
"""

        # Build the review prompt
        prompt = f"""Review this neurosurgery chapter for quality and provide detailed, actionable feedback.

**Chapter Title:** {title}
**Chapter Type:** {chapter_type}
**Total Sections:** {len(sections)}
**Total Words:** {sum(s.get('word_count', 0) for s in sections)}

{quality_context}

**Section Overview:**
{chr(10).join(section_summaries)}

**Full Chapter Content:**
{self._format_sections_for_review(sections)}

**Review Instructions:**
1. **Contradictions:** Check for internal contradictions between sections (e.g., one section says X, another says Y)
2. **Readability:** Identify jargon overuse, unclear explanations, poor flow within sections
3. **Transitions:** Find missing or weak transitions between sections that disrupt logical flow
4. **Citations:** Check for citation issues (missing where needed, outdated, inconsistencies)
5. **Logical Flow:** Assess overall structure and progression - does it build logically?
6. **Clarity:** Identify unclear concepts that need better explanation
7. **Quality Assessment:** Provide scores for clarity, coherence, consistency, completeness
8. **Strengths:** What does this chapter do well?
9. **Priority Improvements:** Top 5-10 improvements ranked by impact

**Target Audience:** Neurosurgery residents, fellows, and practicing neurosurgeons

**Medical Accuracy Standard:** All claims should be evidence-based and appropriately cited

Please provide a comprehensive, honest review that will help improve this chapter to the highest medical education standard.
"""

        # Call GPT-4o with structured output schema
        try:
            from backend.schemas.ai_schemas import CHAPTER_REVIEW_SCHEMA
            from backend.services.ai_provider_service import AITask

            logger.info(f"Calling AI for chapter review (Chapter {chapter.id})")
            response = await self.ai_service.generate_text_with_schema(
                prompt=prompt,
                schema=CHAPTER_REVIEW_SCHEMA,
                task=AITask.METADATA_EXTRACTION,  # Using metadata extraction task type
                max_tokens=4000,  # Large token limit for comprehensive review
                temperature=0.4  # Moderate temperature for balanced creativity and precision
            )

            # Extract review data - guaranteed to match schema
            review_data = response["data"]

            # Store comprehensive review results
            chapter.stage_12_review = {
                "review_data": review_data,
                "reviewed_at": datetime.utcnow().isoformat(),
                "ai_model": response["model"],
                "ai_provider": response["provider"],
                "ai_cost_usd": response["cost_usd"],
                "sections_reviewed": len(sections),
                "schema_validated": True,

                # Extract summary metrics for quick access
                "summary_metrics": {
                    "contradictions_found": len(review_data.get("contradictions", [])),
                    "critical_contradictions": len([c for c in review_data.get("contradictions", []) if c.get("severity") == "critical"]),
                    "readability_issues_found": len(review_data.get("readability_issues", [])),
                    "high_readability_issues": len([r for r in review_data.get("readability_issues", []) if r.get("severity") == "high"]),
                    "missing_transitions": len(review_data.get("missing_transitions", [])),
                    "citation_issues_found": len(review_data.get("citation_issues", [])),
                    "logical_flow_issues": len(review_data.get("logical_flow_issues", [])),
                    "unclear_explanations": len(review_data.get("unclear_explanations", [])),
                    "overall_recommendation": review_data.get("overall_recommendation", ""),
                    "clarity_score": review_data.get("overall_quality_assessment", {}).get("clarity_score", 0),
                    "coherence_score": review_data.get("overall_quality_assessment", {}).get("coherence_score", 0),
                    "consistency_score": review_data.get("overall_quality_assessment", {}).get("consistency_score", 0),
                    "completeness_score": review_data.get("overall_quality_assessment", {}).get("completeness_score", 0),
                    "readability_level": review_data.get("overall_quality_assessment", {}).get("readability_level", ""),
                    "target_audience_alignment": review_data.get("overall_quality_assessment", {}).get("target_audience_alignment", ""),
                    "total_issues": (
                        len(review_data.get("contradictions", [])) +
                        len(review_data.get("readability_issues", [])) +
                        len(review_data.get("missing_transitions", [])) +
                        len(review_data.get("citation_issues", [])) +
                        len(review_data.get("logical_flow_issues", [])) +
                        len(review_data.get("unclear_explanations", []))
                    )
                }
            }

            self.db.commit()

            # Log review summary
            metrics = chapter.stage_12_review["summary_metrics"]
            logger.info(
                f"Stage 12 complete: Review finished for chapter {chapter.id} - "
                f"{metrics['total_issues']} total issues found, "
                f"recommendation: {metrics['overall_recommendation']}, "
                f"clarity: {metrics['clarity_score']:.2f}, "
                f"coherence: {metrics['coherence_score']:.2f}"
            )

        except Exception as e:
            logger.error(f"Error in Stage 12 review for chapter {chapter.id}: {str(e)}", exc_info=True)
            chapter.stage_12_review = {
                "error": str(e),
                "reviewed_at": datetime.utcnow().isoformat(),
                "status": "failed"
            }
            self.db.commit()
            raise

    def _format_sections_for_review(self, sections: list) -> str:
        """
        Format chapter sections for AI review

        Args:
            sections: List of section dictionaries

        Returns:
            Formatted markdown string with all section content
        """
        formatted = []
        for i, section in enumerate(sections):
            section_title = section.get("title", f"Section {i+1}")
            section_content = section.get("content", "")

            formatted.append(f"## {section_title}\n\n{section_content}\n")

        return "\n".join(formatted)

    def _calculate_currency_score(self, chapter: Chapter) -> float:
        """
        Calculate currency score based on source publication years

        Currency measures how recent the literature cited is. More recent sources
        indicate the chapter reflects current medical knowledge.

        Algorithm:
        1. Extract publication years from all sources (internal + external)
        2. Calculate weighted recency score:
           - Sources from last 3 years: 1.0 weight
           - Sources from 3-5 years ago: 0.8 weight
           - Sources from 5-10 years ago: 0.5 weight
           - Sources older than 10 years: 0.2 weight
        3. Return weighted average capped at 1.0

        Args:
            chapter: Chapter object with research data

        Returns:
            Currency score from 0.0 to 1.0
        """
        from datetime import datetime
        import re

        current_year = datetime.now().year
        all_years = []

        # Extract years from internal research sources (Stage 3)
        if chapter.stage_3_internal_research:
            internal_sources = chapter.stage_3_internal_research.get("sources", [])
            for source in internal_sources:
                # Try to extract year from metadata
                year = source.get("year") or source.get("publication_year")
                if year:
                    try:
                        all_years.append(int(year))
                    except (ValueError, TypeError):
                        pass

        # Extract years from external research sources (Stage 4)
        if chapter.stage_4_external_research:
            # Track 1: PubMed papers
            pubmed_papers = chapter.stage_4_external_research.get("pubmed_sources", [])
            for paper in pubmed_papers:
                # PubMed date format: "2023-05-15" or "2023"
                pub_date = paper.get("publication_date") or paper.get("pub_date")
                if pub_date:
                    # Extract year from date string
                    year_match = re.search(r'(\d{4})', str(pub_date))
                    if year_match:
                        try:
                            all_years.append(int(year_match.group(1)))
                        except (ValueError, TypeError):
                            pass

            # Track 2: AI-researched sources
            ai_sources = chapter.stage_4_external_research.get("ai_researched_sources", [])
            for source in ai_sources:
                year = source.get("year") or source.get("publication_year")
                if year:
                    try:
                        all_years.append(int(year))
                    except (ValueError, TypeError):
                        pass

        # If no years found, return default score of 0.5 (neutral)
        if not all_years:
            logger.warning(f"No publication years found for chapter {chapter.id}, using default currency score of 0.5")
            return 0.5

        # Calculate weighted score based on recency
        weighted_scores = []
        for year in all_years:
            age = current_year - year

            if age < 0:
                # Future year (error) - treat as very recent
                weight = 1.0
            elif age <= 3:
                # Very recent (last 3 years)
                weight = 1.0
            elif age <= 5:
                # Recent (3-5 years ago)
                weight = 0.8
            elif age <= 10:
                # Moderately old (5-10 years ago)
                weight = 0.5
            else:
                # Old (>10 years ago)
                weight = 0.2

            weighted_scores.append(weight)

        # Calculate average weighted score
        currency_score = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.5

        # Log currency analysis
        recent_count = len([y for y in all_years if current_year - y <= 3])
        logger.info(
            f"Currency score for chapter {chapter.id}: {currency_score:.2f} "
            f"({len(all_years)} sources total, {recent_count} from last 3 years, "
            f"year range: {min(all_years)}-{max(all_years)})"
        )

        return min(1.0, currency_score)

    async def _stage_13_finalization(self, chapter: Chapter) -> None:
        """
        Stage 13: Finalize chapter

        - Generate metadata
        - Mark as current version
        - Calculate final statistics
        """
        logger.info(f"Stage 13: Finalization for chapter {chapter.id}")
        chapter.generation_status = "stage_13_finalization"
        self.db.commit()

        sections = chapter.sections or []
        total_words = sum(s.get("word_count", 0) for s in sections)

        chapter.version = "1.0"
        chapter.is_current_version = True
        chapter.total_words = total_words
        chapter.total_sections = len(sections)

        self.db.commit()
        logger.info("Stage 13 complete: Chapter finalized")

    async def _stage_14_delivery(self, chapter: Chapter) -> None:
        """
        Stage 14: Deliver chapter

        - Mark as completed
        - Store final timestamp (updated_at)
        - Ready for user retrieval
        """
        logger.info(f"Stage 14: Delivery for chapter {chapter.id}")
        chapter.generation_status = "completed"
        # updated_at will be automatically set by TimestampMixin

        self.db.commit()
        logger.info(f"Stage 14 complete: Chapter {chapter.id} delivered successfully")

    async def _deduplicate_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate sources using intelligent deduplication

        Phase 2 Week 3-4: Uses configurable strategy (exact, fuzzy, semantic)
        Preserves 30-70% more unique sources than simple exact matching

        Args:
            sources: List of sources to deduplicate

        Returns:
            Deduplicated sources list
        """
        if not sources:
            return []

        # Use configured deduplication strategy
        strategy = settings.DEDUPLICATION_STRATEGY
        threshold = settings.SEMANTIC_SIMILARITY_THRESHOLD

        logger.debug(f"Deduplicating {len(sources)} sources with strategy: {strategy}")

        unique_sources = await self.dedup_service.deduplicate_sources(
            sources=sources,
            strategy=strategy,
            similarity_threshold=threshold
        )

        # Log deduplication stats
        stats = self.dedup_service.get_deduplication_stats(unique_sources)
        logger.info(f"Deduplication stats: {stats['unique_sources']}/{stats['total_sources']} unique ({stats['retention_rate']:.1f}% retention)")

        return unique_sources

    def _allocate_sources_for_section(
        self,
        section_plan: Dict[str, Any],
        all_sources: List[Dict[str, Any]],
        allocation_hint: str
    ) -> List[Dict[str, Any]]:
        """
        Intelligently allocate sources for a specific section.

        Uses section title, key points, and allocation hints to find
        most relevant sources. Simple keyword matching for now.

        Args:
            section_plan: Section planning data from Stage 5
            all_sources: All available sources (internal + external)
            allocation_hint: Hint from Stage 5 about which sources to use

        Returns:
            List of most relevant sources for this section
        """
        if not all_sources:
            return []

        # Simple relevance scoring based on keyword overlap
        section_keywords = []

        # Extract keywords from section title
        title = section_plan.get('title', '').lower()
        section_keywords.extend(title.split())

        # Extract keywords from key points
        key_points = section_plan.get('key_points', [])
        for point in key_points:
            if isinstance(point, str):
                section_keywords.extend(point.lower().split())

        # Extract keywords from allocation hint
        if allocation_hint:
            section_keywords.extend(allocation_hint.lower().split())

        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        section_keywords = [k for k in section_keywords if k not in common_words and len(k) > 3]

        # Score each source
        scored_sources = []
        for source in all_sources:
            score = 0

            # Check title
            source_title = source.get('title', '').lower()
            for keyword in section_keywords:
                if keyword in source_title:
                    score += 2

            # Check abstract/summary
            source_abstract = source.get('abstract', '').lower()
            for keyword in section_keywords:
                if keyword in source_abstract:
                    score += 1

            scored_sources.append((score, source))

        # Sort by score and return top sources
        scored_sources.sort(key=lambda x: x[0], reverse=True)

        # Return top 10 most relevant sources (or all if less than 10)
        relevant_count = min(10, len(scored_sources))
        return [source for score, source in scored_sources[:relevant_count]]

    async def _generate_section_content(
        self,
        chapter_title: str,
        section_plan: Dict[str, Any],
        section_hints: Dict[str, Any],
        relevant_sources: List[Dict[str, Any]],
        section_num: int
    ) -> Dict[str, Any]:
        """
        Generate content for a single section using type-specific hints.

        Args:
            chapter_title: Chapter title
            section_plan: Section plan from Stage 5
            section_hints: Type-specific generation hints (if available)
            relevant_sources: Sources allocated for this section
            section_num: Section number

        Returns:
            Dictionary with content, word count, sources used, cost
        """
        section_title = section_plan.get('title', f'Section {section_num}')
        section_type = section_plan.get('section_type', 'custom')
        key_points = section_plan.get('key_points', [])
        word_count_estimate = section_plan.get('word_count_estimate', 500)

        # Build prompt with flexible section-type guidance
        prompt = f"""
Write a comprehensive neurosurgery section for:

Chapter: "{chapter_title}"
Section: "{section_title}"
Section Type: {section_type}

"""

        # Add section-type hints if available (guidance, not requirements)
        if section_hints:
            prompt += f"""
SECTION TYPE GUIDANCE (flexible suggestions to enhance organization):
- Description: {section_hints.get('description', 'N/A')}
- Typical content themes: {', '.join(section_hints.get('typical_content', []))}
- Keywords to consider: {', '.join(section_hints.get('keywords', []))}
- Suggested depth: {section_hints.get('typical_depth', 'standard')}

IMPORTANT: These are SUGGESTIONS to guide structure. Prioritize covering the key points below
and using available sources. Adapt the structure to fit actual knowledge, don't force it.

"""

        prompt += f"""
KEY POINTS TO COVER (based on available knowledge):
{json.dumps(key_points, indent=2)}

AVAILABLE SOURCES for this section (use for evidence and citations):
{json.dumps(relevant_sources, indent=2)}

REQUIREMENTS:
- Target word count: {word_count_estimate} words (flexible based on content)
- Medical accuracy is CRITICAL
- Cite sources using [Author, Year] format
- Use clear, professional medical writing
- Include relevant clinical pearls where appropriate
- Organize content logically (use subsection headings with ## if it helps clarity)
- COVER ALL key points - don't omit valuable information
- If sources provide additional relevant information not in key points, include it

Write the section content in markdown format.
Return ONLY the content (no meta-commentary).
"""

        response = await self.ai_service.generate_text(
            prompt=prompt,
            task=AITask.SECTION_WRITING,
            max_tokens=word_count_estimate * 2,  # 2 tokens per word approx
            temperature=0.6
        )

        section_content = response["text"]
        word_count = len(section_content.split())

        # Extract which sources were actually cited (simple heuristic)
        sources_used = []
        for source in relevant_sources:
            # Check if source title or author appears in content
            source_title = source.get('title', '')
            if source_title and source_title.lower() in section_content.lower():
                sources_used.append(source.get('id') or source.get('title'))

        return {
            "content": section_content,
            "word_count": word_count,
            "sources_used": sources_used,
            "cost_usd": response.get("cost_usd", 0.0),
            "model": response.get("model", "unknown")
        }

    async def _generate_subsection_content(
        self,
        chapter_title: str,
        parent_section_title: str,
        subsection_plan: Dict[str, Any],
        relevant_sources: List[Dict[str, Any]],
        subsection_num: int
    ) -> Dict[str, Any]:
        """
        Generate content for a subsection (hierarchical support).

        Similar to section generation but more focused and concise.

        Args:
            chapter_title: Chapter title
            parent_section_title: Parent section title
            subsection_plan: Subsection plan from Stage 5
            relevant_sources: Sources allocated for parent section
            subsection_num: Subsection number

        Returns:
            Dictionary with content, word count, sources used, cost
        """
        subsection_title = subsection_plan.get('title', f'Subsection {subsection_num}')
        key_points = subsection_plan.get('key_points', [])
        word_count_estimate = subsection_plan.get('word_count_estimate', 200)

        prompt = f"""
Write a focused subsection for:

Chapter: "{chapter_title}"
Section: "{parent_section_title}"
Subsection: "{subsection_title}"

KEY POINTS TO COVER:
{json.dumps(key_points, indent=2)}

AVAILABLE SOURCES:
{json.dumps(relevant_sources[:5], indent=2)}

REQUIREMENTS:
- Target word count: {word_count_estimate} words (concise and focused)
- Medical accuracy is CRITICAL
- Cite sources using [Author, Year] format
- Clear, professional writing
- This is a subsection, so be more focused than a full section
- Cover the key points thoroughly but concisely

Write the subsection content in markdown format.
Return ONLY the content.
"""

        response = await self.ai_service.generate_text(
            prompt=prompt,
            task=AITask.SECTION_WRITING,
            max_tokens=word_count_estimate * 2,
            temperature=0.6
        )

        subsection_content = response["text"]
        word_count = len(subsection_content.split())

        # Extract sources used
        sources_used = []
        for source in relevant_sources[:5]:
            source_title = source.get('title', '')
            if source_title and source_title.lower() in subsection_content.lower():
                sources_used.append(source.get('id') or source.get('title'))

        return {
            "content": subsection_content,
            "word_count": word_count,
            "sources_used": sources_used,
            "cost_usd": response.get("cost_usd", 0.0)
        }

    def _match_images_to_content(
        self,
        section_title: str,
        section_content: str,
        section_type: str,
        available_images: List[Dict[str, Any]],
        used_image_ids: set,
        max_images: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Semantically match images to section content.

        Uses keyword matching and content analysis to find most relevant images.

        Args:
            section_title: Section title
            section_content: Section content text
            section_type: Type of section (for relevance hints)
            available_images: All available images
            used_image_ids: Set of image IDs already used (to avoid duplication)
            max_images: Maximum images to return

        Returns:
            List of most relevant images with relevance scores
        """
        if not available_images:
            return []

        # Extract keywords from section
        section_keywords = []
        section_keywords.extend(section_title.lower().split())
        section_keywords.extend(section_content.lower().split()[:200])  # First 200 words

        # Remove common words
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'this', 'that', 'these',
            'those', 'can', 'will', 'should', 'may', 'also', 'such', 'which', 'from', 'not'
        }
        section_keywords = [k for k in section_keywords if k not in common_words and len(k) > 3]

        # Score each image
        scored_images = []
        for image in available_images:
            image_id = image.get("id")

            # Skip already used images
            if image_id and image_id in used_image_ids:
                continue

            score = 0.0

            # Match against image metadata
            image_caption = image.get("caption", "").lower()
            image_description = image.get("description", "").lower()
            image_keywords = image.get("keywords", [])

            # Score based on keyword matches
            for keyword in section_keywords:
                if keyword in image_caption:
                    score += 3.0
                if keyword in image_description:
                    score += 2.0
                if keyword in str(image_keywords).lower():
                    score += 1.5

            # Bonus for section type relevance
            if section_type == "surgical_technique":
                # Prioritize surgical/procedural images
                if any(term in image_caption.lower() for term in ["surgical", "procedure", "approach", "technique"]):
                    score += 2.0
            elif section_type == "pathophysiology":
                # Prioritize anatomical/pathological images
                if any(term in image_caption.lower() for term in ["anatomy", "pathology", "microscopic", "cellular"]):
                    score += 2.0
            elif section_type == "diagnostic_evaluation":
                # Prioritize imaging/diagnostic images
                if any(term in image_caption.lower() for term in ["mri", "ct", "imaging", "scan", "x-ray"]):
                    score += 2.0

            if score > 0:
                image_copy = image.copy()
                image_copy["_relevance_score"] = score
                scored_images.append((score, image_copy))

        # Sort by relevance score
        scored_images.sort(key=lambda x: x[0], reverse=True)

        # Return top N most relevant images
        relevant_count = min(max_images, len(scored_images))
        return [img for score, img in scored_images[:relevant_count]]

    async def _generate_image_caption(
        self,
        image: Dict[str, Any],
        section_title: str,
        section_context: str
    ) -> str:
        """
        Generate contextual caption for an image placement.

        Uses AI to create a caption that connects the image to the section content.

        Args:
            image: Image metadata
            section_title: Section title where image will be placed
            section_context: Snippet of section content for context

        Returns:
            Generated caption text
        """
        # Use existing caption if good quality
        existing_caption = image.get("caption", "")
        if existing_caption and len(existing_caption) > 20:
            # Enhance existing caption with context
            prompt = f"""
Enhance this image caption to fit the context of the section:

Section Title: "{section_title}"
Section Context: {section_context}

Existing Caption: {existing_caption}

Create a brief, contextual caption (1-2 sentences) that:
1. Describes what the image shows
2. Connects it to the section topic
3. Is clinically relevant

Return ONLY the caption text, no additional commentary.
"""
        else:
            # Generate new caption
            prompt = f"""
Generate a brief image caption for:

Section Title: "{section_title}"
Section Context: {section_context}

Image Metadata: {json.dumps(image, indent=2)}

Create a brief, informative caption (1-2 sentences) that describes the image
and its relevance to this section.

Return ONLY the caption text.
"""

        try:
            response = await self.ai_service.generate_text(
                prompt=prompt,
                task=AITask.CHAPTER_GENERATION,
                max_tokens=100,
                temperature=0.5
            )
            caption = response["text"].strip()

            # Fallback if generation fails
            if not caption or len(caption) < 10:
                caption = existing_caption or f"Figure: {section_title}"

            return caption

        except Exception as e:
            logger.warning(f"Caption generation failed: {e}, using fallback")
            return existing_caption or f"Figure: {section_title}"

    def _summarize_sources(self, internal: List, external: List) -> str:
        """Create summary of available sources"""
        return f"Internal: {len(internal)} sources, External: {len(external)} sources"

    async def regenerate_section(
        self,
        chapter: Chapter,
        section_number: int,
        instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Regenerate a single section while reusing existing research

        This method provides 84% cost savings by:
        - Reusing stages 1-5 data (input validation, context, research, planning)
        - Only re-running stage 6 for the target section
        - Skipping stages 7-14 (images, citations, QA, etc. - already done)

        Cost comparison:
        - Full regeneration: $0.50-0.70 (all 14 stages)
        - Section regeneration: $0.08-0.12 (stage 6 only)

        Args:
            chapter: Chapter object with existing research data
            section_number: Section index to regenerate (0-based)
            instructions: Optional special instructions for AI

        Returns:
            Dictionary with new content and cost

        Raises:
            ValueError: If research data is missing or section doesn't exist
        """
        logger.info(f"Regenerating section {section_number} in chapter {chapter.id}")

        # Validate existing research data
        if not chapter.stage_3_internal_research or not chapter.stage_4_external_research:
            raise ValueError("Chapter missing research data. Cannot regenerate section without research.")

        if not chapter.stage_5_synthesis_metadata:
            raise ValueError("Chapter missing synthesis plan. Cannot regenerate section.")

        if not chapter.sections or section_number >= len(chapter.sections):
            raise ValueError(f"Section {section_number} does not exist")

        # Get the section metadata from stage 5 plan
        # Note: stage_5 contains the outline, we need to find which section corresponds to section_number
        section_info = chapter.sections[section_number]
        section_title = section_info.get("title", f"Section {section_number}")

        # Gather sources from existing research
        internal_sources = chapter.stage_3_internal_research.get("sources", [])
        external_sources = chapter.stage_4_external_research.get("pubmed_sources", [])

        # Filter sources relevant to this section
        # For simplicity, we'll use all sources, but could be optimized to filter by relevance
        all_sources = internal_sources + external_sources

        # Build regeneration prompt
        prompt = f"""
        Regenerate the following section for a neurosurgery chapter.

        **Chapter Title**: {chapter.title}
        **Section Title**: {section_title}
        **Section Number**: {section_number + 1}

        **Available Research Sources**: {len(all_sources)} sources
        """

        if instructions:
            prompt += f"\n\n**Special Instructions**: {instructions}"

        prompt += """

        **Requirements**:
        1. Write comprehensive, evidence-based content
        2. Use medical terminology appropriately
        3. Include specific details from the sources
        4. Maintain academic tone
        5. Target length: 300-500 words
        6. Format in HTML with proper heading tags

        **Research Sources Summary**:
        """

        # Add source summaries (limit to 10 most relevant to avoid token overload)
        for i, source in enumerate(all_sources[:10]):
            title = source.get("title", "Unknown")
            authors = source.get("authors", ["Unknown"])
            year = source.get("year", "N/A")
            prompt += f"\n{i+1}. {title} - {', '.join(authors[:2])} et al. ({year})"

        prompt += "\n\nGenerate the section content now:"

        # Generate with AI
        logger.info(f"Calling AI to regenerate section {section_number}")

        try:
            response = await self.ai_service.generate_text(
                prompt=prompt,
                task=AITask.CONTENT_GENERATION,
                max_tokens=2000,
                temperature=0.7
            )

            new_content = response["text"]
            cost_usd = response.get("cost_usd", 0.08)

            # Update the section in the chapter
            chapter.sections[section_number]["content"] = new_content
            chapter.sections[section_number]["regenerated_at"] = datetime.utcnow().isoformat()
            chapter.sections[section_number]["regeneration_cost_usd"] = cost_usd

            # Update word count
            word_count = len(new_content.split())
            chapter.sections[section_number]["word_count"] = word_count

            self.db.commit()

            logger.info(f"Section {section_number} regenerated successfully, cost: ${cost_usd:.4f}")

            # Emit WebSocket event
            await emitter.emit_section_regenerated(
                chapter_id=str(chapter.id),
                section_number=section_number,
                section_title=section_title,
                new_content=new_content,
                cost_usd=cost_usd
            )

            return {
                "new_content": new_content,
                "cost_usd": cost_usd,
                "word_count": word_count,
                "section_title": section_title
            }

        except Exception as e:
            logger.error(f"Section regeneration failed: {str(e)}", exc_info=True)
            raise
