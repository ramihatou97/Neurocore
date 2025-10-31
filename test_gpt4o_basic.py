"""
Quick test to verify GPT-4o integration
Tests basic text generation with new model and pricing
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.ai_provider_service import AIProviderService, AITask, AIProvider
from backend.config import settings


async def test_gpt4o():
    """Test GPT-4o basic functionality"""
    print("=" * 70)
    print("TESTING GPT-4O INTEGRATION")
    print("=" * 70)

    # Verify configuration
    print(f"\n1. Configuration Check")
    print(f"   OpenAI Chat Model: {settings.OPENAI_CHAT_MODEL}")
    print(f"   Embedding Model: {settings.OPENAI_EMBEDDING_MODEL}")
    print(f"   Embedding Dimensions: {settings.OPENAI_EMBEDDING_DIMENSIONS}")
    print(f"   GPT-4o Input Cost: ${settings.OPENAI_GPT4O_INPUT_COST_PER_1K} per 1K tokens")
    print(f"   GPT-4o Output Cost: ${settings.OPENAI_GPT4O_OUTPUT_COST_PER_1K} per 1K tokens")

    assert settings.OPENAI_CHAT_MODEL == "gpt-4o", "Chat model should be gpt-4o"
    assert settings.OPENAI_EMBEDDING_MODEL == "text-embedding-3-large", "Embedding should be text-embedding-3-large"
    assert settings.OPENAI_EMBEDDING_DIMENSIONS == 3072, "Dimensions should be 3072"
    print("   ✓ Configuration correct!")

    # Initialize service
    print(f"\n2. Initializing AI Provider Service...")
    service = AIProviderService()

    # Test 1: Basic GPT-4o text generation
    print("\n3. Test 1: Basic GPT-4o Text Generation")
    print("   Prompt: 'What is a craniotomy? Answer in 2 sentences.'")

    try:
        result = await service.generate_text(
            prompt="What is a craniotomy? Answer in 2 sentences.",
            task=AITask.METADATA_EXTRACTION,  # Routes to GPT-4
            provider=AIProvider.GPT4,  # Force GPT-4o
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
        print(f"   {result['text'][:200]}...")
        print(f"   {'-' * 66}")

        assert result['model'] == 'gpt-4o', "Should use gpt-4o model"
        assert result['provider'] == 'gpt4o', "Provider should be gpt4o"
        assert result['cost_usd'] < 0.01, "Cost should be very low for GPT-4o"

    except Exception as e:
        print(f"\n   ✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Cost comparison (simulated - showing pricing difference)
    print("\n4. Test 2: Cost Analysis")
    print(f"   Input tokens: {result['input_tokens']}")
    print(f"   Output tokens: {result['output_tokens']}")

    # GPT-4o actual cost
    gpt4o_cost = (
        (result['input_tokens'] / 1000) * settings.OPENAI_GPT4O_INPUT_COST_PER_1K +
        (result['output_tokens'] / 1000) * settings.OPENAI_GPT4O_OUTPUT_COST_PER_1K
    )

    # Old GPT-4-turbo pricing
    gpt4_turbo_cost = (
        (result['input_tokens'] / 1000) * 0.01 +  # $10 per 1M
        (result['output_tokens'] / 1000) * 0.03   # $30 per 1M
    )

    savings = gpt4_turbo_cost - gpt4o_cost
    savings_pct = (savings / gpt4_turbo_cost * 100) if gpt4_turbo_cost > 0 else 0

    print(f"\n   GPT-4o Cost: ${gpt4o_cost:.6f}")
    print(f"   GPT-4-turbo Cost (old): ${gpt4_turbo_cost:.6f}")
    print(f"   Savings: ${savings:.6f}")
    print(f"   Reduction: {savings_pct:.1f}%")

    # Test 3: Embedding with text-embedding-3-large
    print("\n5. Test 3: Embeddings with text-embedding-3-large")

    try:
        embedding_result = await service.generate_embedding(
            text="Neurosurgical knowledge base for medical professionals",
            model="text-embedding-3-large"
        )

        print(f"\n   ✓ Embedding generated!")
        print(f"   Model: {embedding_result['model']}")
        print(f"   Dimensions: {embedding_result['dimensions']}")
        print(f"   Tokens used: {embedding_result['tokens_used']}")
        print(f"   Cost: ${embedding_result['cost_usd']:.6f}")

        assert embedding_result['dimensions'] == 3072, "Should have 3072 dimensions"
        assert embedding_result['model'] == 'text-embedding-3-large', "Should use text-embedding-3-large"

    except Exception as e:
        print(f"\n   ✗ ERROR: {str(e)}")
        return False

    print("\n" + "=" * 70)
    print("✓ ALL GPT-4O TESTS PASSED!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   • GPT-4o is working correctly")
    print(f"   • {savings_pct:.1f}% cost reduction vs GPT-4-turbo")
    print(f"   • text-embedding-3-large producing 3072-dim embeddings")
    print(f"   • All configurations validated")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_gpt4o())
    sys.exit(0 if success else 1)
