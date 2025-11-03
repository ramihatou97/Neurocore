#!/usr/bin/env python3
"""
Fix Image Media Type Detection
Fixes hardcoded image/png to use actual image format (JPEG/PNG)
"""

import re

file_path = "/Users/ramihatoum/Desktop/The neurosurgical core of knowledge/backend/services/ai_provider_service.py"

with open(file_path, 'r') as f:
    content = f.read()

# Fix 1: Update analyze_image signature and implementation
old_analyze_image = '''    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "Analyze this medical image in detail. Identify anatomical structures, pathology, and clinical significance.",
        max_tokens: int = 2000
    ) -> Dict[str, Any]:'''

new_analyze_image = '''    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "Analyze this medical image in detail. Identify anatomical structures, pathology, and clinical significance.",
        max_tokens: int = 2000,
        image_format: str = "PNG"
    ) -> Dict[str, Any]:'''

content = content.replace(old_analyze_image, new_analyze_image)

# Fix 2: Update media type determination in analyze_image
old_media_type = '''        # Determine media type (assume PNG, but could be improved)
        media_type = "image/png"'''

new_media_type = '''        # Determine media type from image format
        format_to_media = {
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
            "GIF": "image/gif"
        }
        media_type = format_to_media.get(image_format.upper(), "image/png")'''

content = content.replace(old_media_type, new_media_type)

# Fix 3: Update _generate_claude_vision signature
old_generate_claude = '''    async def _generate_claude_vision(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Generate image analysis using Claude Vision

        Wrapper around analyze_image for consistency with other vision providers

        Args:
            image_data: Image bytes
            prompt: Analysis prompt
            max_tokens: Maximum tokens for response

        Returns:
            dict with analysis results
        """
        return await self.analyze_image(image_data, prompt, max_tokens)'''

new_generate_claude = '''    async def _generate_claude_vision(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 4000,
        image_format: str = "PNG"
    ) -> Dict[str, Any]:
        """
        Generate image analysis using Claude Vision

        Wrapper around analyze_image for consistency with other vision providers

        Args:
            image_data: Image bytes
            prompt: Analysis prompt
            max_tokens: Maximum tokens for response
            image_format: Image format (JPEG, PNG, etc.)

        Returns:
            dict with analysis results
        """
        return await self.analyze_image(image_data, prompt, max_tokens, image_format)'''

content = content.replace(old_generate_claude, new_generate_claude)

# Fix 4: Update _generate_openai_vision signature
old_generate_openai_sig = '''    async def _generate_openai_vision(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:'''

new_generate_openai_sig = '''    async def _generate_openai_vision(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 4000,
        image_format: str = "PNG"
    ) -> Dict[str, Any]:'''

content = content.replace(old_generate_openai_sig, new_generate_openai_sig)

# Fix 5: Update GPT-4o data URL to use actual format
old_data_url = '''                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}"
                            }'''

new_data_url = '''                            "image_url": {
                                "url": f"data:image/{image_format.lower()};base64,{image_b64}"
                            }'''

content = content.replace(old_data_url, new_data_url)

# Fix 6: Update _generate_google_vision signature
old_generate_google_sig = '''    async def _generate_google_vision(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:'''

new_generate_google_sig = '''    async def _generate_google_vision(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 4000,
        image_format: str = "PNG"
    ) -> Dict[str, Any]:'''

content = content.replace(old_generate_google_sig, new_generate_google_sig)

# Write updated content
with open(file_path, 'w') as f:
    f.write(content)

print("✅ Fixed image media type detection in ai_provider_service.py")
print("   - Updated analyze_image to accept image_format parameter")
print("   - Fixed hardcoded 'image/png' to use actual format")
print("   - Updated _generate_claude_vision signature")
print("   - Updated _generate_openai_vision signature and data URL")
print("   - Updated _generate_google_vision signature")
