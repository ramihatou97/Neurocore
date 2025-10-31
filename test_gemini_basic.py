"""
Quick test script to verify Gemini 2.0 Flash integration
Run this to confirm the API key and model are working correctly
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.ai_provider_service import AIProviderService, AITask, AIProvider
from backend.config import settings


async def test_basic_generation():
    """Test basic text generation with Gemini"""
    print("=" * 70)
    print("TESTING GEMINI 2.0 FLASH - BASIC TEXT GENERATION")
    print("=" * 70)

    # Initialize service
    print(f"\n1. Initializing AI Provider Service...")
    print(f"   API Key configured: {bool(settings.GOOGLE_API_KEY)}")
    print(f"   Model: {settings.GOOGLE_MODEL}")

    service = AIProviderService()

    # Test 1: Simple medical query
    print("\n2. Test 1: Simple Medical Query")
    print("   Prompt: 'What is a craniotomy?'")

    try:
        result = await service.generate_text(
            prompt="What is a craniotomy? Provide a brief 2-sentence answer.",
            task=AITask.SUMMARIZATION,
            provider=AIProvider.GEMINI,  # Force Gemini
            max_tokens=100,
            temperature=0.7
        )

        print(f"\n   ✓ Response received!")
        print(f"   Provider: {result['provider']}")
        print(f"   Model: {result['model']}")
        print(f"   Input tokens: {result['input_tokens']}")
        print(f"   Output tokens: {result['output_tokens']}")
        print(f"   Total tokens: {result['tokens_used']}")
        print(f"   Cost: ${result['cost_usd']:.6f}")
        print(f"\n   Generated text:")
        print(f"   {'-' * 66}")
        print(f"   {result['text'][:300]}...")
        print(f"   {'-' * 66}")

    except Exception as e:
        print(f"\n   ✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: With system prompt
    print("\n3. Test 2: With System Prompt")
    print("   System: 'You are a neurosurgery expert'")
    print("   Prompt: 'Explain subdural hematoma causes'")

    try:
        result = await service.generate_text(
            prompt="Explain the most common causes of subdural hematoma in 2-3 sentences.",
            task=AITask.SUMMARIZATION,
            system_prompt="You are an expert neurosurgeon providing concise medical information.",
            provider=AIProvider.GEMINI,
            max_tokens=150,
            temperature=0.5
        )

        print(f"\n   ✓ Response received!")
        print(f"   Tokens: {result['tokens_used']} (in: {result['input_tokens']}, out: {result['output_tokens']})")
        print(f"   Cost: ${result['cost_usd']:.6f}")
        print(f"\n   Generated text:")
        print(f"   {'-' * 66}")
        print(f"   {result['text']}")
        print(f"   {'-' * 66}")

    except Exception as e:
        print(f"\n   ✗ ERROR: {str(e)}")
        return False

    # Test 3: Cost comparison
    print("\n4. Cost Comparison Test")
    print("   Generating same prompt with Claude and Gemini...")

    test_prompt = "List 3 key symptoms of increased intracranial pressure."

    try:
        # Gemini
        gemini_result = await service.generate_text(
            prompt=test_prompt,
            task=AITask.SUMMARIZATION,
            provider=AIProvider.GEMINI,
            max_tokens=100,
            temperature=0.7
        )

        # Claude
        claude_result = await service.generate_text(
            prompt=test_prompt,
            task=AITask.SUMMARIZATION,
            provider=AIProvider.CLAUDE,
            max_tokens=100,
            temperature=0.7
        )

        print(f"\n   Gemini Cost: ${gemini_result['cost_usd']:.6f}")
        print(f"   Claude Cost: ${claude_result['cost_usd']:.6f}")
        print(f"   Savings: ${claude_result['cost_usd'] - gemini_result['cost_usd']:.6f}")
        print(f"   Reduction: {((claude_result['cost_usd'] - gemini_result['cost_usd']) / claude_result['cost_usd'] * 100):.1f}%")

    except Exception as e:
        print(f"\n   ✗ ERROR in cost comparison: {str(e)}")
        return False

    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED - GEMINI 2.0 FLASH IS WORKING!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_basic_generation())
    sys.exit(0 if success else 1)
