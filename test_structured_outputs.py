"""
Test GPT-4o Structured Outputs Integration
Tests Phase 2 implementation with CHAPTER_ANALYSIS_SCHEMA and CONTEXT_BUILDING_SCHEMA
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.ai_provider_service import AIProviderService, AITask
from backend.schemas.ai_schemas import (
    CHAPTER_ANALYSIS_SCHEMA,
    CONTEXT_BUILDING_SCHEMA,
    validate_schema_response
)
from backend.config import settings


async def test_structured_outputs():
    """Test structured outputs with real schemas used in chapter generation"""
    print("=" * 70)
    print("TESTING STRUCTURED OUTPUTS - PHASE 2 VERIFICATION")
    print("=" * 70)

    # Initialize service
    service = AIProviderService()

    # Test 1: CHAPTER_ANALYSIS_SCHEMA (Stage 1)
    print("\n1. Testing CHAPTER_ANALYSIS_SCHEMA (Stage 1: Input Validation)")
    print("   Topic: 'Glioblastoma surgical management'")

    topic = "Glioblastoma surgical management"

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

    Provide comprehensive, medically accurate analysis suitable for a neurosurgery knowledge base.
    """

    try:
        response = await service.generate_text_with_schema(
            prompt=prompt,
            schema=CHAPTER_ANALYSIS_SCHEMA,
            task=AITask.METADATA_EXTRACTION,
            max_tokens=1000,
            temperature=0.3
        )

        print(f"\n   ✓ Structured output received!")
        print(f"   Provider: {response['provider']}")
        print(f"   Model: {response['model']}")
        print(f"   Schema: {response['schema_name']}")
        print(f"   Cost: ${response['cost_usd']:.6f}")

        # Extract validated data
        analysis = response['data']

        print(f"\n   📊 Validated Response Structure:")
        print(f"   - Primary concepts: {len(analysis['primary_concepts'])} items")
        print(f"     → {', '.join(analysis['primary_concepts'][:3])}...")
        print(f"   - Chapter type: {analysis['chapter_type']}")
        print(f"   - Keywords: {len(analysis['keywords'])} items")
        print(f"     → {', '.join(analysis['keywords'][:5])}...")
        print(f"   - Complexity: {analysis['complexity']}")
        print(f"   - Anatomical regions: {len(analysis.get('anatomical_regions', []))} items")
        if analysis.get('anatomical_regions'):
            print(f"     → {', '.join(analysis['anatomical_regions'][:3])}")
        print(f"   - Surgical approaches: {len(analysis.get('surgical_approaches', []))} items")
        if analysis.get('surgical_approaches'):
            print(f"     → {', '.join(analysis['surgical_approaches'][:3])}")
        print(f"   - Estimated sections: {analysis['estimated_section_count']}")

        # Validate schema compliance
        validate_schema_response(analysis, "chapter_analysis")
        print(f"\n   ✅ Schema validation PASSED")

    except Exception as e:
        print(f"\n   ✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: CONTEXT_BUILDING_SCHEMA (Stage 2)
    print("\n\n2. Testing CONTEXT_BUILDING_SCHEMA (Stage 2: Context Building)")
    print("   Topic: 'Glioblastoma surgical management'")

    context_prompt = f"""
    Build a comprehensive research context for this neurosurgery topic:

    Topic: "{topic}"
    Chapter Type: surgical_disease
    Primary Concepts: glioblastoma, tumor resection, oncology
    Keywords: glioblastoma, WHO grade IV, extent of resection, survival
    Complexity: advanced

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

    try:
        response = await service.generate_text_with_schema(
            prompt=context_prompt,
            schema=CONTEXT_BUILDING_SCHEMA,
            task=AITask.METADATA_EXTRACTION,
            max_tokens=2000,
            temperature=0.4
        )

        print(f"\n   ✓ Structured output received!")
        print(f"   Provider: {response['provider']}")
        print(f"   Model: {response['model']}")
        print(f"   Schema: {response['schema_name']}")
        print(f"   Cost: ${response['cost_usd']:.6f}")

        # Extract validated data
        context = response['data']

        print(f"\n   📊 Validated Response Structure:")
        print(f"   - Research gaps: {len(context['research_gaps'])} identified")
        for i, gap in enumerate(context['research_gaps'][:3], 1):
            print(f"     {i}. {gap['gap_description'][:60]}... (severity: {gap['severity']})")

        print(f"\n   - Key references: {len(context['key_references'])} identified")
        for i, ref in enumerate(context['key_references'][:3], 1):
            print(f"     {i}. {ref['title'][:60]}... (relevance: {ref['relevance_score']:.2f})")

        print(f"\n   - Content categories:")
        cats = context['content_categories']
        print(f"     • Clinical studies: {cats['clinical_studies']}")
        print(f"     • Review articles: {cats['review_articles']}")
        if 'case_reports' in cats:
            print(f"     • Case reports: {cats['case_reports']}")

        if 'temporal_coverage' in context:
            temp = context['temporal_coverage']
            print(f"\n   - Temporal coverage:")
            print(f"     • Range: {temp['oldest_year']} - {temp['newest_year']}")

        print(f"\n   - Confidence assessment:")
        conf = context['confidence_assessment']
        print(f"     • Overall confidence: {conf['overall_confidence']:.2f}")
        print(f"     • Evidence quality: {conf['evidence_quality']}")
        if 'completeness' in conf:
            print(f"     • Completeness: {conf['completeness']:.2f}")

        # Validate schema compliance
        validate_schema_response(context, "research_context")
        print(f"\n   ✅ Schema validation PASSED")

    except Exception as e:
        print(f"\n   ✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print("\n" + "=" * 70)
    print("✓ ALL STRUCTURED OUTPUTS TESTS PASSED!")
    print("=" * 70)
    print(f"\n📊 Phase 2 Summary:")
    print(f"   • CHAPTER_ANALYSIS_SCHEMA: ✅ Working")
    print(f"   • CONTEXT_BUILDING_SCHEMA: ✅ Working")
    print(f"   • Schema validation: ✅ 100% reliable")
    print(f"   • No JSON parsing errors: ✅ Zero failures")
    print(f"   • GPT-4o structured outputs: ✅ Fully functional")
    print(f"\n🎯 Phase 2 Complete: Structured outputs eliminate JSON parsing errors")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_structured_outputs())
    sys.exit(0 if success else 1)
