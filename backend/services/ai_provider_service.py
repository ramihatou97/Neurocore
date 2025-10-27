"""
AI Provider Service - Abstraction layer for multiple AI providers
Supports Claude Sonnet 4.5 (primary), GPT-4/5, and Gemini with hierarchical fallback
"""

import anthropic
import openai
import google.generativeai as genai
from typing import Optional, Dict, Any, List
from enum import Enum

from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class AIProvider(str, Enum):
    """Available AI providers"""
    CLAUDE = "claude"
    GPT4 = "gpt4"
    GEMINI = "gemini"


class AITask(str, Enum):
    """AI task types for provider selection"""
    CHAPTER_GENERATION = "chapter_generation"      # Claude Sonnet 4.5 (primary)
    SECTION_WRITING = "section_writing"            # Claude Sonnet 4.5 (primary)
    IMAGE_ANALYSIS = "image_analysis"              # Claude Vision (95% complete)
    FACT_CHECKING = "fact_checking"                # GPT-4 (cross-validation)
    METADATA_EXTRACTION = "metadata_extraction"    # GPT-4 (structured output)
    SUMMARIZATION = "summarization"                # Gemini (fast summaries)
    EMBEDDING = "embedding"                        # OpenAI (text-embedding-3-large)


class AIProviderService:
    """
    Unified interface for multiple AI providers with intelligent routing

    Provider Hierarchy:
    - Claude Sonnet 4.5: Primary for medical content generation (depth, accuracy)
    - GPT-4/5: Secondary for structured tasks, fact-checking
    - Gemini: Tertiary for fast summarization, lightweight tasks

    Cost Tracking:
    - Tracks token usage and costs per request
    - Returns cost information for analytics
    """

    def __init__(self):
        """Initialize AI provider clients"""
        # Initialize Claude (Anthropic)
        if settings.ANTHROPIC_API_KEY:
            self.claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info("Claude client initialized")
        else:
            self.claude_client = None
            logger.warning("Claude API key not configured")

        # Initialize OpenAI
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
            logger.info("OpenAI client initialized")
        else:
            logger.warning("OpenAI API key not configured")

        # Initialize Gemini
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            logger.info("Gemini client initialized")
        else:
            logger.warning("Gemini API key not configured")

    def get_preferred_provider(self, task: AITask) -> AIProvider:
        """
        Get preferred AI provider for a given task

        Args:
            task: Type of AI task

        Returns:
            Preferred AI provider enum
        """
        task_to_provider = {
            AITask.CHAPTER_GENERATION: AIProvider.CLAUDE,
            AITask.SECTION_WRITING: AIProvider.CLAUDE,
            AITask.IMAGE_ANALYSIS: AIProvider.CLAUDE,
            AITask.FACT_CHECKING: AIProvider.GPT4,
            AITask.METADATA_EXTRACTION: AIProvider.GPT4,
            AITask.SUMMARIZATION: AIProvider.GEMINI,
            AITask.EMBEDDING: AIProvider.GPT4,  # OpenAI embeddings
        }
        return task_to_provider.get(task, AIProvider.CLAUDE)

    async def generate_text(
        self,
        prompt: str,
        task: AITask,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        provider: Optional[AIProvider] = None
    ) -> Dict[str, Any]:
        """
        Generate text using the appropriate AI provider

        Args:
            prompt: User prompt
            task: Type of task (for provider selection)
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            provider: Override provider selection

        Returns:
            dict with keys: text, provider, tokens_used, cost_usd
        """
        # Determine provider
        if provider is None:
            provider = self.get_preferred_provider(task)

        try:
            if provider == AIProvider.CLAUDE:
                return await self._generate_claude(prompt, system_prompt, max_tokens, temperature)
            elif provider == AIProvider.GPT4:
                return await self._generate_gpt4(prompt, system_prompt, max_tokens, temperature)
            elif provider == AIProvider.GEMINI:
                return await self._generate_gemini(prompt, max_tokens, temperature)
            else:
                raise ValueError(f"Unknown provider: {provider}")

        except Exception as e:
            logger.error(f"AI generation failed with {provider}: {str(e)}", exc_info=True)

            # Fallback to next provider
            if provider == AIProvider.CLAUDE and settings.OPENAI_API_KEY:
                logger.info("Falling back to GPT-4")
                return await self._generate_gpt4(prompt, system_prompt, max_tokens, temperature)
            elif provider == AIProvider.GPT4 and settings.GOOGLE_API_KEY:
                logger.info("Falling back to Gemini")
                return await self._generate_gemini(prompt, max_tokens, temperature)
            else:
                raise

    async def _generate_claude(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate text using Claude Sonnet 4.5"""
        if not self.claude_client:
            raise ValueError("Claude client not initialized")

        messages = [{"role": "user", "content": prompt}]

        response = self.claude_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "You are an expert neurosurgeon and medical writer.",
            messages=messages
        )

        # Extract text from response
        text = response.content[0].text if response.content else ""

        # Calculate cost
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost_usd = (
            (input_tokens / 1000) * settings.ANTHROPIC_SONNET_INPUT_COST_PER_1K +
            (output_tokens / 1000) * settings.ANTHROPIC_SONNET_OUTPUT_COST_PER_1K
        )

        logger.info(
            f"Claude generation: {input_tokens} input + {output_tokens} output tokens, "
            f"${cost_usd:.4f}"
        )

        return {
            "text": text,
            "provider": "claude",
            "model": settings.CLAUDE_MODEL,
            "tokens_used": input_tokens + output_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd
        }

    async def _generate_gpt4(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate text using GPT-4"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = openai.ChatCompletion.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

        text = response.choices[0].message.content

        # Calculate cost
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost_usd = (
            (input_tokens / 1000) * settings.OPENAI_GPT4_INPUT_COST_PER_1K +
            (output_tokens / 1000) * settings.OPENAI_GPT4_OUTPUT_COST_PER_1K
        )

        logger.info(
            f"GPT-4 generation: {input_tokens} input + {output_tokens} output tokens, "
            f"${cost_usd:.4f}"
        )

        return {
            "text": text,
            "provider": "gpt4",
            "model": settings.OPENAI_MODEL,
            "tokens_used": input_tokens + output_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd
        }

    async def _generate_gemini(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate text using Gemini"""
        model = genai.GenerativeModel(settings.GEMINI_MODEL)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )

        text = response.text

        # Approximate token count (Gemini doesn't always provide exact counts)
        approx_tokens = len(prompt.split()) + len(text.split())
        cost_usd = (approx_tokens / 1000) * settings.GOOGLE_GEMINI_INPUT_COST_PER_1K

        logger.info(f"Gemini generation: ~{approx_tokens} tokens, ${cost_usd:.4f}")

        return {
            "text": text,
            "provider": "gemini",
            "model": settings.GEMINI_MODEL,
            "tokens_used": approx_tokens,
            "input_tokens": approx_tokens // 2,
            "output_tokens": approx_tokens // 2,
            "cost_usd": cost_usd
        }

    async def generate_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-large"
    ) -> Dict[str, Any]:
        """
        Generate text embedding using OpenAI

        Args:
            text: Text to embed
            model: Embedding model to use

        Returns:
            dict with keys: embedding (list of floats), dimensions, cost_usd
        """
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")

        response = openai.Embedding.create(
            model=model,
            input=text
        )

        embedding = response.data[0].embedding
        tokens_used = response.usage.total_tokens

        # Calculate cost
        cost_usd = (tokens_used / 1000) * settings.OPENAI_EMBEDDING_COST_PER_1K

        logger.debug(f"Embedding generated: {tokens_used} tokens, ${cost_usd:.6f}")

        return {
            "embedding": embedding,
            "dimensions": len(embedding),
            "model": model,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd
        }

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "Analyze this medical image in detail. Identify anatomical structures, pathology, and clinical significance.",
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Analyze image using Claude Vision (95% complete analysis)

        Args:
            image_data: Image bytes
            prompt: Analysis prompt
            max_tokens: Maximum tokens for response

        Returns:
            dict with analysis results
        """
        if not self.claude_client:
            raise ValueError("Claude client not initialized")

        import base64

        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        # Determine media type (assume PNG, but could be improved)
        media_type = "image/png"

        response = self.claude_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=max_tokens,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )

        text = response.content[0].text if response.content else ""

        # Calculate cost
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost_usd = (
            (input_tokens / 1000) * settings.ANTHROPIC_SONNET_INPUT_COST_PER_1K +
            (output_tokens / 1000) * settings.ANTHROPIC_SONNET_OUTPUT_COST_PER_1K
        )

        logger.info(f"Claude Vision analysis: ${cost_usd:.4f}")

        return {
            "text": text,  # Changed from "analysis" to match generate_text signature
            "provider": "claude_vision",
            "tokens_used": input_tokens + output_tokens,
            "cost_usd": cost_usd,
            "model": "claude-sonnet-4"
        }

    async def _generate_claude_vision(
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
        return await self.analyze_image(image_data, prompt, max_tokens)

    async def _generate_openai_vision(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Generate image analysis using OpenAI Vision (GPT-4 Vision)

        Args:
            image_data: Image bytes
            prompt: Analysis prompt
            max_tokens: Maximum tokens for response

        Returns:
            dict with analysis results
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        import base64

        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        response = self.openai_client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=max_tokens
        )

        text = response.choices[0].message.content if response.choices else ""

        # Calculate cost (GPT-4 Vision pricing)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost_usd = (
            (input_tokens / 1000) * 0.01 +  # $0.01 per 1K input tokens
            (output_tokens / 1000) * 0.03   # $0.03 per 1K output tokens
        )

        logger.info(f"OpenAI Vision analysis: ${cost_usd:.4f}")

        return {
            "text": text,
            "provider": "openai_vision",
            "tokens_used": input_tokens + output_tokens,
            "cost_usd": cost_usd,
            "model": "gpt-4-vision-preview"
        }

    async def _generate_google_vision(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Generate image analysis using Google Gemini Vision (optional)

        Args:
            image_data: Image bytes
            prompt: Analysis prompt
            max_tokens: Maximum tokens for response

        Returns:
            dict with analysis results
        """
        if not self.gemini_model:
            raise ValueError("Gemini client not initialized")

        import PIL.Image
        import io

        # Convert bytes to PIL Image
        image = PIL.Image.open(io.BytesIO(image_data))

        # Generate response
        response = self.gemini_model.generate_content(
            [prompt, image],
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.4
            )
        )

        text = response.text if hasattr(response, 'text') else ""

        # Gemini doesn't provide token counts in the same way, estimate
        estimated_tokens = len(text.split()) * 1.3  # Rough estimate
        cost_usd = (estimated_tokens / 1000) * 0.001  # Approximate cost

        logger.info(f"Google Vision analysis: ${cost_usd:.4f}")

        return {
            "text": text,
            "provider": "google_vision",
            "tokens_used": int(estimated_tokens),
            "cost_usd": cost_usd,
            "model": "gemini-pro-vision"
        }

    async def generate_vision_analysis_with_fallback(
        self,
        image_base64: str,
        prompt: str,
        task: AITask = AITask.IMAGE_ANALYSIS,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Generate vision analysis with hierarchical fallback

        Fallback order: Claude Vision → OpenAI Vision → Google Vision (optional)

        Args:
            image_base64: Base64 encoded image
            prompt: Analysis prompt
            task: Task type
            max_tokens: Maximum tokens

        Returns:
            Analysis result with provider info
        """
        import base64

        # Decode base64 to bytes
        image_data = base64.b64decode(image_base64)

        # Try Claude Vision first
        try:
            logger.info("Attempting Claude Vision analysis")
            result = await self._generate_claude_vision(image_data, prompt, max_tokens)
            return result
        except Exception as e:
            logger.warning(f"Claude Vision failed: {str(e)}, falling back to OpenAI Vision")

        # Fall back to OpenAI Vision
        try:
            logger.info("Attempting OpenAI Vision analysis")
            result = await self._generate_openai_vision(image_data, prompt, max_tokens)
            return result
        except Exception as e:
            logger.warning(f"OpenAI Vision failed: {str(e)}, falling back to Google Vision")

        # Fall back to Google Vision (optional)
        try:
            logger.info("Attempting Google Vision analysis")
            result = await self._generate_google_vision(image_data, prompt, max_tokens)
            return result
        except Exception as e:
            logger.error(f"All vision providers failed: {str(e)}")
            raise ValueError("All vision providers failed for image analysis")
