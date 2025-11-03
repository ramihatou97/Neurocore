#!/usr/bin/env python3
"""
Quick test script to verify Perplexity API integration
Tests both the configuration loading and API connectivity
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.config.settings import settings
from backend.services.ai_provider_service import AIProviderService


async def test_perplexity_config():
    """Test 1: Verify Perplexity configuration is loaded"""
    print("=" * 60)
    print("TEST 1: Configuration Loading")
    print("=" * 60)

    print(f"✓ PERPLEXITY_API_KEY loaded: {bool(settings.PERPLEXITY_API_KEY)}")
    if settings.PERPLEXITY_API_KEY:
        print(f"  Key prefix: {settings.PERPLEXITY_API_KEY[:10]}...")
    print(f"✓ PERPLEXITY_MODEL: {settings.PERPLEXITY_MODEL}")
    print(f"✓ PERPLEXITY_API_URL: {settings.PERPLEXITY_API_URL}")
    print(f"✓ EXTERNAL_RESEARCH_AI_ENABLED: {settings.EXTERNAL_RESEARCH_AI_ENABLED}")
    print(f"✓ EXTERNAL_RESEARCH_STRATEGY: {settings.EXTERNAL_RESEARCH_STRATEGY}")
    print(f"✓ EXTERNAL_RESEARCH_AI_PROVIDER: {settings.EXTERNAL_RESEARCH_AI_PROVIDER}")
    print(f"✓ EXTERNAL_RESEARCH_PARALLEL_EXECUTION: {settings.EXTERNAL_RESEARCH_PARALLEL_EXECUTION}")

    print()
    return bool(settings.PERPLEXITY_API_KEY)


async def test_perplexity_api():
    """Test 2: Test actual Perplexity API call"""
    print("=" * 60)
    print("TEST 2: Perplexity API Connectivity")
    print("=" * 60)

    try:
        ai_service = AIProviderService()

        # Check if Perplexity is initialized
        if not ai_service.perplexity_api_key:
            print("✗ Perplexity not initialized (API key missing)")
            return False

        print("✓ AIProviderService initialized with Perplexity")
        print(f"  API Base URL: {ai_service.perplexity_base_url}")

        # Test simple research query
        print("\n🔬 Testing Perplexity research query...")
        print("   Query: 'surgical approaches to brain tumors'")

        result = await ai_service.external_research_ai(
            query="surgical approaches to brain tumors",
            provider="perplexity",
            max_results=3,
            focus="surgical_techniques"
        )

        print("\n✓ Perplexity API call successful!")
        print(f"  Provider: {result.get('provider')}")
        print(f"  Sources found: {len(result.get('sources', []))}")
        print(f"  Tokens used: {result.get('metadata', {}).get('tokens_used', 0)}")
        print(f"  Cost: ${result.get('cost_usd', 0):.4f}")

        # Show first few sources
        sources = result.get('sources', [])
        if sources:
            print(f"\n  First {min(3, len(sources))} sources:")
            for i, source in enumerate(sources[:3], 1):
                print(f"    {i}. {source.get('title', 'No title')[:60]}...")
                if source.get('url'):
                    print(f"       URL: {source['url'][:60]}...")

        # Show research excerpt
        research = result.get('research', '')
        if research:
            print(f"\n  Research excerpt (first 200 chars):")
            print(f"    {research[:200]}...")

        return True

    except Exception as e:
        print(f"\n✗ Perplexity API test failed:")
        print(f"  Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PERPLEXITY INTEGRATION TEST")
    print("=" * 60)
    print()

    # Test 1: Configuration
    config_ok = await test_perplexity_config()
    if not config_ok:
        print("\n❌ Configuration test failed - Perplexity API key not found")
        print("   Please check .env file for PERPLEXITY_API_KEY")
        return False

    print()

    # Test 2: API connectivity
    api_ok = await test_perplexity_api()

    print()
    print("=" * 60)
    if config_ok and api_ok:
        print("✅ ALL TESTS PASSED - Perplexity integration working!")
    else:
        print("❌ SOME TESTS FAILED - See errors above")
    print("=" * 60)
    print()

    return config_ok and api_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
