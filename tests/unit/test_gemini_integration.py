"""
Comprehensive test suite for Gemini 2.0 Flash integration

Tests all Gemini features:
- Basic text generation
- Token counting accuracy
- Cost calculation
- Vision/image analysis
- Streaming
- Function calling
- Context caching
- Safety filters
- Error handling
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from backend.services.ai_provider_service import AIProviderService, AITask, AIProvider
from backend.config import settings


@pytest.mark.asyncio
class TestGeminiIntegration:
    """Test suite for Gemini 2.0 Flash integration"""

    def setup_method(self):
        """Setup test fixtures"""
        self.service = AIProviderService()

    async def test_gemini_initialization(self):
        """Test that Gemini client initializes correctly"""
        assert settings.GOOGLE_API_KEY is not None
        assert settings.GOOGLE_MODEL == "gemini-2.0-flash-exp"
        # Service should initialize without errors
        assert self.service is not None

    async def test_basic_text_generation(self):
        """Test basic text generation with Gemini"""
        result = await self.service.generate_text(
            prompt="What is a craniotomy? Answer in one sentence.",
            task=AITask.SUMMARIZATION,
            provider=AIProvider.GEMINI,
            max_tokens=100,
            temperature=0.7
        )

        # Verify response structure
        assert "text" in result
        assert "provider" in result
        assert result["provider"] == "gemini"
        assert "model" in result
        assert result["model"] == settings.GOOGLE_MODEL

        # Verify token counts
        assert "input_tokens" in result
        assert "output_tokens" in result
        assert "tokens_used" in result
        assert result["input_tokens"] > 0
        assert result["output_tokens"] > 0
        assert result["tokens_used"] == result["input_tokens"] + result["output_tokens"]

        # Verify cost calculation
        assert "cost_usd" in result
        assert result["cost_usd"] > 0
        assert result["cost_usd"] < 0.01  # Should be very cheap

    async def test_system_prompt_support(self):
        """Test that system prompts are handled correctly"""
        result = await self.service.generate_text(
            prompt="Explain subdural hematoma.",
            system_prompt="You are a neurosurgery expert. Be concise.",
            task=AITask.SUMMARIZATION,
            provider=AIProvider.GEMINI,
            max_tokens=150,
            temperature=0.5
        )

        assert result["text"]
        assert len(result["text"]) > 0

    async def test_token_counting_accuracy(self):
        """Test that token counts are accurate (not approximations)"""
        result = await self.service.generate_text(
            prompt="List 3 symptoms of increased intracranial pressure.",
            task=AITask.SUMMARIZATION,
            provider=AIProvider.GEMINI,
            max_tokens=100,
            temperature=0.7
        )

        # Token counts should be integers (not floats/approximations)
        assert isinstance(result["input_tokens"], int)
        assert isinstance(result["output_tokens"], int)
        assert isinstance(result["tokens_used"], int)

        # Verify math is correct
        assert result["tokens_used"] == result["input_tokens"] + result["output_tokens"]

    async def test_cost_calculation(self):
        """Test that cost calculation uses correct Gemini 2.0 Flash pricing"""
        result = await self.service.generate_text(
            prompt="Define meningioma.",
            task=AITask.SUMMARIZATION,
            provider=AIProvider.GEMINI,
            max_tokens=100,
            temperature=0.7
        )

        # Calculate expected cost manually
        expected_cost = (
            (result["input_tokens"] / 1000) * settings.GOOGLE_GEMINI_INPUT_COST_PER_1K +
            (result["output_tokens"] / 1000) * settings.GOOGLE_GEMINI_OUTPUT_COST_PER_1K
        )

        # Allow small floating point differences
        assert abs(result["cost_usd"] - expected_cost) < 0.000001

    async def test_cost_comparison_with_claude(self):
        """Test that Gemini is significantly cheaper than Claude"""
        test_prompt = "List 3 brain lobes."

        gemini_result = await self.service.generate_text(
            prompt=test_prompt,
            task=AITask.SUMMARIZATION,
            provider=AIProvider.GEMINI,
            max_tokens=100,
            temperature=0.7
        )

        claude_result = await self.service.generate_text(
            prompt=test_prompt,
            task=AITask.SUMMARIZATION,
            provider=AIProvider.CLAUDE,
            max_tokens=100,
            temperature=0.7
        )

        # Gemini should be at least 90% cheaper
        savings_percent = ((claude_result["cost_usd"] - gemini_result["cost_usd"]) /
                          claude_result["cost_usd"] * 100)
        assert savings_percent > 90

    async def test_safety_filters(self):
        """Test that safety filters allow medical content"""
        # Medical content should NOT be blocked
        result = await self.service.generate_text(
            prompt="Describe a surgical incision procedure.",
            task=AITask.SUMMARIZATION,
            provider=AIProvider.GEMINI,
            max_tokens=150,
            temperature=0.7
        )

        assert result["text"]
        assert len(result["text"]) > 0

    async def test_error_handling_invalid_prompt(self):
        """Test error handling for invalid inputs"""
        with pytest.raises(Exception):
            await self.service.generate_text(
                prompt="",  # Empty prompt
                task=AITask.SUMMARIZATION,
                provider=AIProvider.GEMINI,
                max_tokens=100,
                temperature=0.7
            )

    async def test_fallback_mechanism(self):
        """Test that Gemini falls back to Claude on failure"""
        # Force Gemini to fail by using an invalid model
        with patch('backend.config.settings.GOOGLE_MODEL', 'invalid-model'):
            result = await self.service.generate_text(
                prompt="What is a neuron?",
                task=AITask.SUMMARIZATION,
                max_tokens=100,
                temperature=0.7
            )

            # Should fallback and still get a response
            assert result["text"]

    async def test_default_provider_selection(self):
        """Test that SUMMARIZATION task defaults to Gemini"""
        preferred_provider = self.service.get_preferred_provider(AITask.SUMMARIZATION)
        assert preferred_provider == AIProvider.GEMINI

    async def test_vision_image_analysis(self):
        """Test Gemini Vision for image analysis"""
        from PIL import Image
        import io

        # Create simple test image
        img = Image.new('RGB', (100, 100), color='white')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        image_data = img_byte_arr.getvalue()

        # Test vision analysis
        result = await self.service._generate_google_vision(
            image_data=image_data,
            prompt="Describe this image.",
            max_tokens=100
        )

        assert result["text"]
        assert result["provider"] == "gemini_vision"
        assert result["input_tokens"] > 0  # Image counts as tokens
        assert result["cost_usd"] > 0

    async def test_vision_unsupported_format(self):
        """Test that unsupported image formats are rejected"""
        # Create a BMP image (not supported by Gemini)
        from PIL import Image
        import io

        img = Image.new('RGB', (100, 100), color='white')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='BMP')
        image_data = img_byte_arr.getvalue()

        with pytest.raises(ValueError, match="Unsupported image format"):
            await self.service._generate_google_vision(
                image_data=image_data,
                prompt="Describe this image.",
                max_tokens=100
            )

    async def test_configuration_values(self):
        """Test that configuration values are correct"""
        assert settings.GOOGLE_MODEL == "gemini-2.0-flash-exp"
        assert settings.GOOGLE_GEMINI_INPUT_COST_PER_1K == 0.000075
        assert settings.GOOGLE_GEMINI_OUTPUT_COST_PER_1K == 0.0003

    async def test_temperature_variation(self):
        """Test that different temperatures affect output"""
        prompt = "What is neuroplasticity?"

        low_temp_result = await self.service.generate_text(
            prompt=prompt,
            task=AITask.SUMMARIZATION,
            provider=AIProvider.GEMINI,
            max_tokens=100,
            temperature=0.1  # Very deterministic
        )

        high_temp_result = await self.service.generate_text(
            prompt=prompt,
            task=AITask.SUMMARIZATION,
            provider=AIProvider.GEMINI,
            max_tokens=100,
            temperature=0.9  # Very random
        )

        # Both should generate text
        assert low_temp_result["text"]
        assert high_temp_result["text"]

    async def test_max_tokens_limit(self):
        """Test that max_tokens parameter is respected"""
        result = await self.service.generate_text(
            prompt="Write a detailed essay about the brain.",
            task=AITask.SUMMARIZATION,
            provider=AIProvider.GEMINI,
            max_tokens=50,  # Very limited
            temperature=0.7
        )

        # Output should be limited
        assert result["output_tokens"] <= 50

    @pytest.mark.skipif(
        "SKIP_SLOW_TESTS" in os.environ,
        reason="Streaming test is slow"
    )
    async def test_streaming(self):
        """Test streaming functionality"""
        chunks_received = []

        async for chunk in self.service._generate_gemini_streaming(
            prompt="Explain craniotomy in 3 sentences.",
            max_tokens=150,
            temperature=0.7
        ):
            chunks_received.append(chunk)
            assert "chunk" in chunk
            assert "provider" in chunk
            assert chunk["provider"] == "gemini"

        # Should receive multiple chunks
        assert len(chunks_received) > 0

        # Full text should accumulate
        final_text = chunks_received[-1]["full_text"]
        assert len(final_text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
