"""
Test script for Gemini Vision (image analysis)
Creates a simple test image and verifies Gemini can analyze it
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.ai_provider_service import AIProviderService
from backend.config import settings


async def test_vision():
    """Test Gemini Vision with a simple test image"""
    print("=" * 70)
    print("TESTING GEMINI 2.0 FLASH VISION")
    print("=" * 70)

    # Create a simple test image using PIL
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io

        # Create a simple image with text
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)

        # Draw some shapes and text to simulate a medical diagram
        draw.rectangle([50, 50, 350, 250], outline='black', width=3)
        draw.ellipse([100, 100, 300, 200], outline='red', width=2)
        draw.text((120, 130), "Brain Diagram", fill='black')
        draw.text((140, 160), "Test Image", fill='blue')

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        image_data = img_byte_arr.getvalue()

        print(f"\n1. Created test image: 400x300 PNG")
        print(f"   Image size: {len(image_data)} bytes")

    except Exception as e:
        print(f"\n✗ ERROR creating test image: {str(e)}")
        return False

    # Initialize service
    print(f"\n2. Initializing AI Provider Service...")
    service = AIProviderService()

    # Test Gemini Vision
    print("\n3. Testing Gemini Vision Analysis")
    print("   Prompt: 'Describe what you see in this image'")

    try:
        result = await service._generate_google_vision(
            image_data=image_data,
            prompt="Describe what you see in this image. What text and shapes are present?",
            max_tokens=200
        )

        print(f"\n   ✓ Vision analysis completed!")
        print(f"   Provider: {result['provider']}")
        print(f"   Model: {result['model']}")
        print(f"   Input tokens: {result['input_tokens']}")
        print(f"   Output tokens: {result['output_tokens']}")
        print(f"   Total tokens: {result['tokens_used']}")
        print(f"   Cost: ${result['cost_usd']:.6f}")
        print(f"\n   Analysis:")
        print(f"   {'-' * 66}")
        print(f"   {result['text']}")
        print(f"   {'-' * 66}")

    except Exception as e:
        print(f"\n   ✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    # Compare with Claude Vision
    print("\n4. Cost Comparison with Claude Vision")

    try:
        claude_result = await service._generate_claude_vision(
            image_data=image_data,
            prompt="Describe what you see in this image. What text and shapes are present?",
            max_tokens=200
        )

        print(f"\n   Gemini Vision Cost: ${result['cost_usd']:.6f}")
        print(f"   Claude Vision Cost: ${claude_result['cost_usd']:.6f}")
        savings = claude_result['cost_usd'] - result['cost_usd']
        print(f"   Savings: ${savings:.6f}")
        if claude_result['cost_usd'] > 0:
            reduction = (savings / claude_result['cost_usd'] * 100)
            print(f"   Reduction: {reduction:.1f}%")

    except Exception as e:
        print(f"\n   ⚠ Could not compare with Claude: {str(e)}")

    print("\n" + "=" * 70)
    print("✓ GEMINI VISION TEST PASSED!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_vision())
    sys.exit(0 if success else 1)
