"""
AI Provider Service - Abstraction layer for multiple AI providers
Supports Claude Sonnet 4.5 (primary), GPT-4/5, and Gemini with hierarchical fallback

Features:
- Circuit breaker pattern for resilience
- Automatic fallback on provider failure
- Per-provider health tracking
- Fail-fast on repeated failures
"""

import anthropic
import openai
import google.generativeai as genai
import httpx
import time
from typing import Optional, Dict, Any, List
from enum import Enum

from backend.config import settings
from backend.utils import get_logger
from backend.services.circuit_breaker import circuit_breaker_manager, CircuitState

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
        """Initialize AI provider clients with circuit breaker protection"""
        # Initialize circuit breakers
        self.circuit_breakers = circuit_breaker_manager

        # Initialize provider metrics service (lazy import to avoid circular dependency)
        try:
            from backend.services.provider_metrics_service import provider_metrics_service
            self.metrics_service = provider_metrics_service
        except ImportError:
            self.metrics_service = None
            logger.warning("Provider metrics service not available")

        # Initialize Claude (Anthropic)
        if settings.ANTHROPIC_API_KEY:
            self.claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.circuit_breakers.get_breaker("claude")
            logger.info("Claude client initialized with circuit breaker")
        else:
            self.claude_client = None
            logger.warning("Claude API key not configured")

        # Initialize OpenAI (v1.0+ client)
        if settings.OPENAI_API_KEY:
            from openai import OpenAI
            self.openai_client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=httpx.Timeout(30.0, connect=5.0),  # 30s read, 5s connect
                max_retries=2
            )
            self.circuit_breakers.get_breaker("gpt4")
            logger.info("OpenAI client initialized with circuit breaker")
        else:
            self.openai_client = None
            logger.warning("OpenAI API key not configured")

        # Initialize Gemini
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.circuit_breakers.get_breaker("gemini")
            logger.info("Gemini client initialized with circuit breaker")
        else:
            logger.warning("Gemini API key not configured")

        # Initialize Perplexity (for AI-first external research)
        if settings.PERPLEXITY_API_KEY:
            self.perplexity_api_key = settings.PERPLEXITY_API_KEY
            self.perplexity_base_url = settings.PERPLEXITY_API_URL
            self.circuit_breakers.get_breaker("perplexity")
            logger.info("Perplexity client configured with circuit breaker")
        else:
            self.perplexity_api_key = None
            self.perplexity_base_url = None
            logger.warning("Perplexity API key not configured - AI external research disabled")

    def get_preferred_provider(self, task: AITask) -> AIProvider:
        """
        Get preferred AI provider for a given task

        Args:
            task: Type of AI task

        Returns:
            Preferred AI provider enum
        """
        # Balanced Hybrid Configuration (Phase 1 - Conservative)
        # Cost-optimized: Gemini for drafts, GPT-4o for structured, Claude for critical
        task_to_provider = {
            AITask.CHAPTER_GENERATION: AIProvider.GEMINI,  # ✓ Phase 1: Gemini for fast, cheap drafts (99.97% cheaper)
            AITask.SECTION_WRITING: AIProvider.CLAUDE,     # Keep Claude for now (phase in later)
            AITask.IMAGE_ANALYSIS: AIProvider.CLAUDE,      # Claude for vision critical medical images
            AITask.FACT_CHECKING: AIProvider.GPT4,         # ✓ GPT-4o for structured fact-check + 70% savings vs Claude
            AITask.METADATA_EXTRACTION: AIProvider.GPT4,   # GPT-4o for 100% reliable structured output
            AITask.SUMMARIZATION: AIProvider.GEMINI,       # Gemini for fast, cheap summaries
            AITask.EMBEDDING: AIProvider.GPT4,             # GPT-4o text-embedding-3-large (best quality)
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
        Generate text using the appropriate AI provider with circuit breaker protection

        Args:
            prompt: User prompt
            task: Type of task (for provider selection)
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            provider: Override provider selection

        Returns:
            dict with keys: text, provider, tokens_used, cost_usd

        Circuit Breaker Logic:
            1. Check if primary provider circuit is closed
            2. If open, automatically try fallback provider
            3. Record success/failure for circuit breaker state
        """
        # Determine provider
        if provider is None:
            provider = self.get_preferred_provider(task)

        # Try primary provider with circuit breaker
        result = await self._try_provider_with_circuit_breaker(
            provider=provider,
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )

        if result is not None:
            return result

        # Primary failed, try fallback chain
        fallback_chain = self._get_fallback_chain(provider)
        for fallback_provider in fallback_chain:
            logger.info(f"Attempting fallback from {provider} to {fallback_provider}")

            result = await self._try_provider_with_circuit_breaker(
                provider=fallback_provider,
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )

            if result is not None:
                return result

        # All providers failed
        raise Exception(
            f"All AI providers failed or circuit breakers open. "
            f"Primary: {provider}, Fallbacks: {fallback_chain}"
        )

    async def _try_provider_with_circuit_breaker(
        self,
        provider: AIProvider,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to call provider with circuit breaker protection

        Returns:
            Result dict on success, None if circuit breaker rejects or call fails
        """
        provider_name = provider.value
        breaker = self.circuit_breakers.get_breaker(provider_name)

        # Check if circuit breaker allows calls
        if not breaker.is_call_allowed():
            stats = breaker.get_stats()
            logger.warning(
                f"Circuit breaker OPEN for {provider_name}, skipping call "
                f"(state: {stats['state']})"
            )
            return None

        try:
            # Attempt provider call
            if provider == AIProvider.CLAUDE:
                result = await self._generate_claude(prompt, system_prompt, max_tokens, temperature)
            elif provider == AIProvider.GPT4:
                result = await self._generate_gpt4(prompt, system_prompt, max_tokens, temperature)
            elif provider == AIProvider.GEMINI:
                result = await self._generate_gemini(prompt, max_tokens, temperature, system_prompt)
            else:
                raise ValueError(f"Unknown provider: {provider}")

            # Success - record and return
            breaker.record_success()
            return result

        except Exception as e:
            # Failure - record for circuit breaker
            breaker.record_failure(error=e)
            logger.error(
                f"Provider {provider_name} call failed: {str(e)[:200]}"
            )
            return None

    def _get_fallback_chain(self, primary_provider: AIProvider) -> List[AIProvider]:
        """
        Get ordered fallback provider chain

        Args:
            primary_provider: Primary provider that failed

        Returns:
            List of fallback providers to try in order
        """
        # Define fallback priorities
        if primary_provider == AIProvider.CLAUDE:
            return [AIProvider.GPT4, AIProvider.GEMINI]
        elif primary_provider == AIProvider.GPT4:
            return [AIProvider.GEMINI, AIProvider.CLAUDE]
        elif primary_provider == AIProvider.GEMINI:
            return [AIProvider.GPT4, AIProvider.CLAUDE]
        else:
            return [AIProvider.GPT4, AIProvider.GEMINI]

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
            model=settings.ANTHROPIC_MODEL,
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
            "model": settings.ANTHROPIC_MODEL,
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
        """
        Generate text using GPT-4o (OpenAI v1.0+ API)

        Note: Despite method name, this now uses GPT-4o (configured in settings)
        which is 75% cheaper than GPT-4-turbo and has better reasoning.
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.openai_client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,  # gpt-4o
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

        text = response.choices[0].message.content

        # Calculate cost (GPT-4o pricing)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost_usd = (
            (input_tokens / 1000) * settings.OPENAI_GPT4_INPUT_COST_PER_1K +
            (output_tokens / 1000) * settings.OPENAI_GPT4_OUTPUT_COST_PER_1K
        )

        logger.info(
            f"{settings.OPENAI_CHAT_MODEL} generation: {input_tokens} input + {output_tokens} output tokens, "
            f"${cost_usd:.4f}"
        )

        return {
            "text": text,
            "provider": "gpt4o",  # Updated to reflect actual model
            "model": settings.OPENAI_CHAT_MODEL,
            "tokens_used": input_tokens + output_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd
        }

    async def _generate_gemini(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate text using Gemini 2.0 Flash

        Args:
            prompt: User prompt
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
            system_prompt: Optional system instructions (prepended to prompt)

        Returns:
            dict with text, tokens, and cost information
        """
        # Create model instance
        model = genai.GenerativeModel(settings.GOOGLE_MODEL)

        # Combine system prompt with user prompt if provided
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        # Generate content with safety settings adjusted for medical content
        # Note: Medical content should be allowed since this is a medical knowledge base
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            ),
            safety_settings={
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            }
        )

        # Check for blocked content (safety filters)
        if response.prompt_feedback.block_reason:
            raise ValueError(f"Gemini blocked prompt due to: {response.prompt_feedback.block_reason}")

        # Check if response was generated
        if not response.candidates:
            raise ValueError("Gemini did not generate a response (no candidates)")

        # Extract text
        text = response.text

        # Get actual token counts from usage metadata (Gemini 2.0 Flash provides these)
        # Handle different SDK versions gracefully
        try:
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
                total_tokens = input_tokens + output_tokens
            else:
                # Fallback: Estimate tokens (4 chars ≈ 1 token)
                input_tokens = len(full_prompt) // 4
                output_tokens = len(text) // 4
                total_tokens = input_tokens + output_tokens
                logger.warning("Gemini usage_metadata not available, using token estimation")
        except AttributeError:
            # Fallback for older SDK versions
            input_tokens = len(full_prompt) // 4
            output_tokens = len(text) // 4
            total_tokens = input_tokens + output_tokens
            logger.warning("Gemini usage_metadata attribute error, using token estimation")

        # Calculate accurate cost using separate input/output pricing
        cost_usd = (
            (input_tokens / 1000) * settings.GOOGLE_GEMINI_INPUT_COST_PER_1K +
            (output_tokens / 1000) * settings.GOOGLE_GEMINI_OUTPUT_COST_PER_1K
        )

        logger.info(
            f"Gemini generation: {input_tokens} input + {output_tokens} output tokens, "
            f"${cost_usd:.6f}"
        )

        return {
            "text": text,
            "provider": "gemini",
            "model": settings.GOOGLE_MODEL,
            "tokens_used": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd
        }

    async def generate_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-large"
    ) -> Dict[str, Any]:
        """
        Generate text embedding using OpenAI (v1.0+ API)

        CRITICAL: Uses dimensions=1536 parameter to comply with pgvector HNSW limit (2000 dims)
        text-embedding-3-large @ 1536 dims still outperforms ada-002 @ 1536 dims

        Args:
            text: Text to embed
            model: Embedding model to use

        Returns:
            dict with keys: embedding (list of floats), dimensions, cost_usd
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        response = self.openai_client.embeddings.create(
            model=model,
            input=text,
            dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS  # CRITICAL: 1536 for pgvector compatibility
        )

        embedding = response.data[0].embedding
        tokens_used = response.usage.total_tokens

        # Calculate cost
        cost_usd = (tokens_used / 1000) * settings.OPENAI_EMBEDDING_COST_PER_1K

        logger.debug(f"Embedding generated: {len(embedding)} dims, {tokens_used} tokens, ${cost_usd:.6f}")

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
        max_tokens: int = 2000,
        image_format: str = "PNG"
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

        # Determine media type from image format
        format_to_media = {
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
            "GIF": "image/gif"
        }
        media_type = format_to_media.get(image_format.upper(), "image/png")

        response = self.claude_client.messages.create(
            model=settings.ANTHROPIC_MODEL,
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
        return await self.analyze_image(image_data, prompt, max_tokens, image_format)

    async def _generate_openai_vision(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 4000,
        image_format: str = "PNG"
    ) -> Dict[str, Any]:
        """
        Generate image analysis using GPT-4o (multimodal vision support)

        GPT-4o has native multimodal capabilities for text and images.
        67% cheaper than legacy gpt-4-vision-preview.

        Args:
            image_data: Image bytes (PNG, JPEG, GIF, WebP)
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
            model="gpt-4o",  # GPT-4o with native vision support
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
                                "url": f"data:image/{image_format.lower()};base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=max_tokens
        )

        text = response.choices[0].message.content if response.choices else ""

        # Calculate cost (GPT-4o pricing)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost_usd = (
            (input_tokens / 1000) * settings.OPENAI_GPT4O_INPUT_COST_PER_1K +
            (output_tokens / 1000) * settings.OPENAI_GPT4O_OUTPUT_COST_PER_1K
        )

        logger.info(f"GPT-4o Vision analysis: ${cost_usd:.4f}")

        return {
            "text": text,
            "provider": "gpt4o_vision",
            "tokens_used": input_tokens + output_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "model": "gpt-4o"
        }

    async def _generate_google_vision(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 4000,
        image_format: str = "PNG"
    ) -> Dict[str, Any]:
        """
        Generate image analysis using Google Gemini 2.0 Flash Vision

        Gemini 2.0 Flash has native multimodal support for images.

        Args:
            image_data: Image bytes (PNG, JPEG, WebP, max 20MB)
            prompt: Analysis prompt
            max_tokens: Maximum tokens for response

        Returns:
            dict with analysis results including actual token counts
        """
        if not settings.GOOGLE_API_KEY:
            raise ValueError("Gemini API key not configured")

        import PIL.Image
        import io

        # Convert bytes to PIL Image
        try:
            image = PIL.Image.open(io.BytesIO(image_data))
        except Exception as e:
            raise ValueError(f"Failed to load image: {str(e)}")

        # Validate image format
        if image.format not in ['PNG', 'JPEG', 'JPG', 'WEBP']:
            raise ValueError(f"Unsupported image format: {image.format}. Use PNG, JPEG, or WebP")

        # Create model instance (Gemini 2.0 Flash supports vision natively)
        model = genai.GenerativeModel(settings.GOOGLE_MODEL)

        # Generate response with image and text
        response = model.generate_content(
            [prompt, image],
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.4  # Lower temperature for factual medical analysis
            ),
            safety_settings={
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            }
        )

        # Check for blocked content
        if response.prompt_feedback.block_reason:
            raise ValueError(f"Gemini blocked image analysis: {response.prompt_feedback.block_reason}")

        if not response.candidates:
            raise ValueError("Gemini did not generate a response for image")

        # Extract text
        text = response.text

        # Get actual token counts from usage metadata
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        total_tokens = input_tokens + output_tokens

        # Calculate cost (images are processed as tokens by Gemini)
        cost_usd = (
            (input_tokens / 1000) * settings.GOOGLE_GEMINI_INPUT_COST_PER_1K +
            (output_tokens / 1000) * settings.GOOGLE_GEMINI_OUTPUT_COST_PER_1K
        )

        logger.info(
            f"Gemini Vision analysis: {input_tokens} input + {output_tokens} output tokens, "
            f"${cost_usd:.6f}"
        )

        return {
            "text": text,
            "provider": "gemini_vision",
            "model": settings.GOOGLE_MODEL,
            "tokens_used": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd
        }

    async def generate_vision_analysis_with_fallback(
        self,
        image_base64: str,
        prompt: str,
        task: AITask = AITask.IMAGE_ANALYSIS,
        max_tokens: int = 4000,
        image_format: str = "PNG",
        image_id: Optional[str] = None,
        chapter_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate vision analysis with hierarchical fallback

        Fallback order: Claude Vision → OpenAI Vision → Google Vision (optional)

        Args:
            image_base64: Base64 encoded image
            prompt: Analysis prompt
            task: Task type
            max_tokens: Maximum tokens
            image_format: Image format (JPEG, PNG, etc.)
            image_id: Optional image ID for metrics tracking
            chapter_id: Optional chapter ID for metrics tracking

        Returns:
            Analysis result with provider info
        """
        import base64

        # Decode base64 to bytes
        image_data = base64.b64decode(image_base64)

        # Try Claude Vision first
        start_time = time.time()
        try:
            logger.info(f"Attempting Claude Vision analysis (format: {image_format})")
            result = await self._generate_claude_vision(image_data, prompt, max_tokens, image_format)

            # Record success metric
            response_time_ms = int((time.time() - start_time) * 1000)
            if self.metrics_service:
                try:
                    self.metrics_service.record_metric(
                        provider="claude",
                        model=result.get("model", "claude-sonnet-4"),
                        task_type=task.value,
                        success=True,
                        image_id=image_id,
                        chapter_id=chapter_id,
                        response_time_ms=response_time_ms,
                        input_tokens=result.get("input_tokens"),
                        output_tokens=result.get("output_tokens"),
                        total_tokens=result.get("tokens_used"),
                        cost_usd=result.get("cost_usd"),
                        json_parse_success=None,  # Will be set by caller
                        was_fallback=False
                    )
                except Exception as metric_error:
                    logger.warning(f"Failed to record Claude metric: {metric_error}")

            return result
        except Exception as e:
            # Record failure metric
            response_time_ms = int((time.time() - start_time) * 1000)
            error_type = type(e).__name__
            if self.metrics_service:
                try:
                    self.metrics_service.record_metric(
                        provider="claude",
                        model="claude-sonnet-4",
                        task_type=task.value,
                        success=False,
                        image_id=image_id,
                        chapter_id=chapter_id,
                        response_time_ms=response_time_ms,
                        error_type=error_type,
                        error_message=str(e)[:500],  # Limit error message length
                        was_fallback=False
                    )
                except Exception as metric_error:
                    logger.warning(f"Failed to record Claude failure metric: {metric_error}")

            logger.warning(f"Claude Vision failed: {str(e)}, falling back to OpenAI Vision")

        # Fall back to OpenAI Vision
        start_time = time.time()
        try:
            logger.info(f"Attempting OpenAI Vision analysis (format: {image_format})")
            result = await self._generate_openai_vision(image_data, prompt, max_tokens, image_format)

            # Record fallback success metric
            response_time_ms = int((time.time() - start_time) * 1000)
            if self.metrics_service:
                try:
                    self.metrics_service.record_metric(
                        provider="gpt4o",
                        model=result.get("model", "gpt-4o"),
                        task_type=task.value,
                        success=True,
                        image_id=image_id,
                        chapter_id=chapter_id,
                        response_time_ms=response_time_ms,
                        input_tokens=result.get("input_tokens"),
                        output_tokens=result.get("output_tokens"),
                        total_tokens=result.get("tokens_used"),
                        cost_usd=result.get("cost_usd"),
                        json_parse_success=None,
                        was_fallback=True,
                        original_provider="claude",
                        fallback_reason="Claude Vision failed"
                    )
                except Exception as metric_error:
                    logger.warning(f"Failed to record GPT-4o metric: {metric_error}")

            return result
        except Exception as e:
            # Record fallback failure metric
            response_time_ms = int((time.time() - start_time) * 1000)
            error_type = type(e).__name__
            if self.metrics_service:
                try:
                    self.metrics_service.record_metric(
                        provider="gpt4o",
                        model="gpt-4o",
                        task_type=task.value,
                        success=False,
                        image_id=image_id,
                        chapter_id=chapter_id,
                        response_time_ms=response_time_ms,
                        error_type=error_type,
                        error_message=str(e)[:500],
                        was_fallback=True,
                        original_provider="claude",
                        fallback_reason="Claude Vision failed"
                    )
                except Exception as metric_error:
                    logger.warning(f"Failed to record GPT-4o failure metric: {metric_error}")

            logger.warning(f"OpenAI Vision failed: {str(e)}, falling back to Google Vision")

        # Fall back to Google Vision (optional)
        start_time = time.time()
        try:
            logger.info(f"Attempting Google Vision analysis (format: {image_format})")
            result = await self._generate_google_vision(image_data, prompt, max_tokens, image_format)

            # Record second fallback success metric
            response_time_ms = int((time.time() - start_time) * 1000)
            if self.metrics_service:
                try:
                    self.metrics_service.record_metric(
                        provider="gemini",
                        model=result.get("model", settings.GOOGLE_MODEL),
                        task_type=task.value,
                        success=True,
                        image_id=image_id,
                        chapter_id=chapter_id,
                        response_time_ms=response_time_ms,
                        input_tokens=result.get("input_tokens"),
                        output_tokens=result.get("output_tokens"),
                        total_tokens=result.get("tokens_used"),
                        cost_usd=result.get("cost_usd"),
                        json_parse_success=None,
                        was_fallback=True,
                        original_provider="claude",
                        fallback_reason="Claude and OpenAI Vision failed"
                    )
                except Exception as metric_error:
                    logger.warning(f"Failed to record Gemini metric: {metric_error}")

            return result
        except Exception as e:
            # Record second fallback failure metric
            response_time_ms = int((time.time() - start_time) * 1000)
            error_type = type(e).__name__
            if self.metrics_service:
                try:
                    self.metrics_service.record_metric(
                        provider="gemini",
                        model=settings.GOOGLE_MODEL,
                        task_type=task.value,
                        success=False,
                        image_id=image_id,
                        chapter_id=chapter_id,
                        response_time_ms=response_time_ms,
                        error_type=error_type,
                        error_message=str(e)[:500],
                        was_fallback=True,
                        original_provider="claude",
                        fallback_reason="Claude and OpenAI Vision failed"
                    )
                except Exception as metric_error:
                    logger.warning(f"Failed to record Gemini failure metric: {metric_error}")

            logger.error(f"All vision providers failed: {str(e)}")
            raise ValueError("All vision providers failed for image analysis")

    async def _generate_gemini_streaming(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str] = None
    ):
        """
        Generate text using Gemini 2.0 Flash with streaming

        Yields text chunks as they're generated for real-time display.

        Args:
            prompt: User prompt
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
            system_prompt: Optional system instructions

        Yields:
            dict with chunk text and metadata
        """
        # Create model instance
        model = genai.GenerativeModel(settings.GOOGLE_MODEL)

        # Combine system prompt with user prompt if provided
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        # Generate content with streaming
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            ),
            safety_settings={
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            },
            stream=True  # Enable streaming
        )

        # Stream chunks
        full_text = ""
        for chunk in response:
            if chunk.text:
                full_text += chunk.text
                yield {
                    "chunk": chunk.text,
                    "full_text": full_text,
                    "provider": "gemini",
                    "model": settings.GOOGLE_MODEL
                }

        # After streaming completes, get final token counts
        # Note: Token counts are only available after streaming completes
        logger.info(f"Gemini streaming completed, generated {len(full_text)} characters")

    async def _generate_gemini_with_functions(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate text using Gemini with function calling

        Allows Gemini to call predefined functions for structured data extraction.

        Args:
            prompt: User prompt
            functions: List of function definitions (OpenAI-style format)
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
            system_prompt: Optional system instructions

        Returns:
            dict with text, function calls, and metadata
        """
        # Create model instance
        model = genai.GenerativeModel(settings.GOOGLE_MODEL)

        # Combine system prompt with user prompt if provided
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        # Convert OpenAI-style functions to Gemini format
        tools = [genai.types.Tool(
            function_declarations=[
                genai.types.FunctionDeclaration(
                    name=func["name"],
                    description=func["description"],
                    parameters=func.get("parameters", {})
                )
                for func in functions
            ]
        )]

        # Generate content with function calling
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            ),
            safety_settings={
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            },
            tools=tools
        )

        # Check for function calls
        function_calls = []
        if response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call'):
                    function_calls.append({
                        "name": part.function_call.name,
                        "arguments": dict(part.function_call.args)
                    })

        # Extract text
        text = response.text if hasattr(response, 'text') and response.text else ""

        # Get token counts
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        total_tokens = input_tokens + output_tokens

        # Calculate cost
        cost_usd = (
            (input_tokens / 1000) * settings.GOOGLE_GEMINI_INPUT_COST_PER_1K +
            (output_tokens / 1000) * settings.GOOGLE_GEMINI_OUTPUT_COST_PER_1K
        )

        logger.info(
            f"Gemini function calling: {input_tokens} input + {output_tokens} output tokens, "
            f"{len(function_calls)} function calls, ${cost_usd:.6f}"
        )

        return {
            "text": text,
            "function_calls": function_calls,
            "provider": "gemini",
            "model": settings.GOOGLE_MODEL,
            "tokens_used": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd
        }

    async def _generate_gemini_with_cache(
        self,
        prompt: str,
        cache_context: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate text using Gemini with context caching (50% cost reduction on cached content)

        Use this for repeated queries with the same large context (e.g., medical terminology,
        chapter guidelines) to get 50% discount on cached tokens.

        Args:
            prompt: User prompt
            cache_context: Large context to cache (e.g., medical glossary, guidelines)
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
            system_prompt: Optional system instructions

        Returns:
            dict with text, tokens, and cost information
        """
        # Create model with caching
        # Note: Caching requires the context to be at least 32K tokens
        model = genai.GenerativeModel(
            model_name=settings.GOOGLE_MODEL,
            system_instruction=system_prompt if system_prompt else None
        )

        # Combine cached context with prompt
        full_prompt = f"{cache_context}\n\n{prompt}"

        # Generate content (caching is automatic for repeated contexts)
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            ),
            safety_settings={
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            }
        )

        # Check for blocked content
        if response.prompt_feedback.block_reason:
            raise ValueError(f"Gemini blocked prompt due to: {response.prompt_feedback.block_reason}")

        if not response.candidates:
            raise ValueError("Gemini did not generate a response")

        # Extract text
        text = response.text

        # Get token counts
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        cached_tokens = response.usage_metadata.cached_content_token_count if hasattr(response.usage_metadata, 'cached_content_token_count') else 0
        total_tokens = input_tokens + output_tokens

        # Calculate cost (cached tokens are 10x cheaper)
        cost_usd = (
            ((input_tokens - cached_tokens) / 1000) * settings.GOOGLE_GEMINI_INPUT_COST_PER_1K +  # Regular input
            (cached_tokens / 1000) * (settings.GOOGLE_GEMINI_INPUT_COST_PER_1K * 0.1) +  # Cached input (10x cheaper)
            (output_tokens / 1000) * settings.GOOGLE_GEMINI_OUTPUT_COST_PER_1K  # Output
        )

        logger.info(
            f"Gemini with caching: {input_tokens} input ({cached_tokens} cached) + {output_tokens} output tokens, "
            f"${cost_usd:.6f}"
        )

        return {
            "text": text,
            "provider": "gemini",
            "model": settings.GOOGLE_MODEL,
            "tokens_used": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "cost_usd": cost_usd
        }

    async def generate_text_with_schema(
        self,
        prompt: str,
        schema: Dict[str, Any],
        task: AITask,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Generate text with JSON schema validation using GPT-4o Structured Outputs

        This method GUARANTEES that the response will match the provided JSON schema.
        No more try/catch for JSON parsing - the response is always valid JSON.

        Perfect for:
        - Metadata extraction
        - Structured data extraction
        - Medical claim categorization
        - Research source analysis

        Args:
            prompt: User prompt describing what to extract
            schema: JSON schema dict (from backend.schemas.ai_schemas)
            task: Task type (for logging/analytics)
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens to generate
            temperature: Lower = more deterministic (default 0.3 for structured data)

        Returns:
            dict with keys:
                - data: Parsed JSON object (GUARANTEED to match schema)
                - provider: "gpt4o"
                - model: "gpt-4o"
                - tokens_used: Total tokens
                - input_tokens: Input token count
                - output_tokens: Output token count
                - cost_usd: Cost in USD

        Example:
            from backend.schemas.ai_schemas import CHAPTER_ANALYSIS_SCHEMA

            result = await service.generate_text_with_schema(
                prompt="Analyze this medical topic: Glioblastoma",
                schema=CHAPTER_ANALYSIS_SCHEMA,
                task=AITask.METADATA_EXTRACTION
            )

            # No try/catch needed - guaranteed valid
            analysis = result['data']
            chapter_type = analysis['chapter_type']  # Always present and valid
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Use GPT-4o with structured outputs (response_format)
        logger.info(f"Generating structured output with schema: {schema.get('name', 'unknown')}")

        response = self.openai_client.chat.completions.create(
            model="gpt-4o",  # Only GPT-4o supports structured outputs
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": schema
            }
        )

        # Extract and parse response
        # With structured outputs, this is GUARANTEED to be valid JSON matching the schema
        import json
        text = response.choices[0].message.content
        parsed_data = json.loads(text)  # Will never fail with structured outputs

        # Calculate cost
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        total_tokens = input_tokens + output_tokens

        cost_usd = (
            (input_tokens / 1000) * settings.OPENAI_GPT4O_INPUT_COST_PER_1K +
            (output_tokens / 1000) * settings.OPENAI_GPT4O_OUTPUT_COST_PER_1K
        )

        logger.info(
            f"GPT-4o structured output: {input_tokens} input + {output_tokens} output tokens, "
            f"${cost_usd:.6f}, schema={schema.get('name')}"
        )

        return {
            "data": parsed_data,  # Parsed JSON object (schema-validated)
            "raw_text": text,      # Raw JSON string (for debugging)
            "provider": "gpt4o",
            "model": "gpt-4o",
            "tokens_used": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "schema_name": schema.get("name", "unknown")
        }

    async def generate_batch_structured_outputs(
        self,
        prompts: List[Dict[str, str]],
        schema: Dict[str, Any],
        task: AITask,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple structured outputs in parallel

        Useful for batch processing (e.g., analyzing 100 PubMed abstracts)

        Args:
            prompts: List of dicts with 'prompt' key
            schema: JSON schema for all responses
            task: Task type
            system_prompt: Optional system instructions

        Returns:
            List of response dicts (same format as generate_text_with_schema)
        """
        import asyncio

        tasks = [
            self.generate_text_with_schema(
                prompt=p['prompt'],
                schema=schema,
                task=task,
                system_prompt=system_prompt
            )
            for p in prompts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions, log errors
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch item {i} failed: {str(result)}")
            else:
                valid_results.append(result)

        return valid_results

    async def _generate_perplexity_research(
        self,
        query: str,
        max_tokens: int = 4000,
        focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate neurosurgical research using Perplexity AI (sonar-pro)

        Perplexity provides real-time web search with citations for current
        surgical techniques, expert opinions, and clinical practice patterns.

        Args:
            query: Research query (neurosurgical topic)
            max_tokens: Maximum tokens for response
            focus: Optional focus area (e.g., "surgical_techniques", "clinical_outcomes")

        Returns:
            dict with keys:
                - research: Generated research content
                - citations: List of source URLs with metadata
                - provider: "perplexity"
                - model: "sonar-pro"
                - tokens_used: Total tokens
                - cost_usd: Estimated cost

        Raises:
            ValueError: If Perplexity API key not configured
            httpx.HTTPError: If API request fails
        """
        if not self.perplexity_api_key:
            raise ValueError("Perplexity API key not configured")

        logger.info(f"Perplexity research: '{query}' (focus: {focus or 'general'})")

        # Build system prompt based on focus
        system_prompt = """You are an expert neurosurgery research assistant synthesizing PRACTICAL SURGICAL KNOWLEDGE.

Focus on:
- Current surgical techniques and approaches
- Expert surgical tips and clinical pearls
- Real-world practice patterns from leading neurosurgeons
- Clinical decision-making frameworks
- Practical management strategies
- Complication avoidance and management

Provide actionable neurosurgical expertise that a neurosurgeon needs in clinical practice or the operating room.
Search broadly for expert content, surgical guides, clinical protocols, and authoritative neurosurgical sources."""

        if focus == "surgical_techniques":
            system_prompt += "\n\nEmphasize detailed surgical approaches, technical nuances, and procedural steps."
        elif focus == "clinical_outcomes":
            system_prompt += "\n\nEmphasize clinical outcomes, evidence-based results, and patient management."

        # Build user prompt for comprehensive research
        user_prompt = f"""Conduct comprehensive neurosurgical research on: {query}

Provide:
1. Detailed surgical approach and current techniques
2. Clinical decision-making framework
3. Expert tips from experienced neurosurgeons
4. Common complications and management strategies
5. Patient selection and preoperative planning
6. Current best practices and expert consensus

Focus on PRACTICAL KNOWLEDGE a neurosurgeon needs in clinic/OR, not just literature review.
Search for expert content, surgical guides, and clinical protocols from authoritative sources."""

        try:
            # Call Perplexity API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.perplexity_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.perplexity_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.PERPLEXITY_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": settings.PERPLEXITY_TEMPERATURE,
                        "max_tokens": max_tokens,
                        "return_citations": True,  # Get source URLs
                        "search_recency_filter": "month"  # Recent content (last 30 days)
                    }
                )

                response.raise_for_status()
                data = response.json()

            # Extract research content
            research_content = data["choices"][0]["message"]["content"]

            # Extract citations
            citations = data.get("citations", [])

            # Estimate tokens and cost (Perplexity doesn't always return usage)
            # Rough estimate: 4 characters ≈ 1 token
            estimated_input_tokens = len(system_prompt + user_prompt) // 4
            estimated_output_tokens = len(research_content) // 4
            total_tokens = estimated_input_tokens + estimated_output_tokens

            # Calculate cost
            cost_usd = (
                (estimated_input_tokens / 1000) * settings.PERPLEXITY_INPUT_COST_PER_1K +
                (estimated_output_tokens / 1000) * settings.PERPLEXITY_OUTPUT_COST_PER_1K
            )

            logger.info(
                f"Perplexity research complete: ~{total_tokens} tokens, "
                f"{len(citations)} citations, ${cost_usd:.4f}"
            )

            return {
                "research": research_content,
                "citations": citations,
                "provider": "perplexity",
                "model": settings.PERPLEXITY_MODEL,
                "tokens_used": total_tokens,
                "input_tokens": estimated_input_tokens,
                "output_tokens": estimated_output_tokens,
                "cost_usd": cost_usd,
                "citation_count": len(citations)
            }

        except httpx.HTTPError as e:
            logger.error(f"Perplexity API request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Perplexity research error: {str(e)}", exc_info=True)
            raise

    async def _generate_gemini_grounded_research(
        self,
        query: str,
        max_tokens: int = 4000,
        focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate neurosurgical research using Gemini 2.0 Flash with Google Search grounding

        Gemini provides real-time web search with citations using Google Search,
        significantly cheaper than Perplexity (~96% cost savings).

        Args:
            query: Neurosurgical research query
            max_tokens: Maximum tokens for response
            focus: Optional focus area (e.g., "surgical_techniques")

        Returns:
            dict with keys:
                - research: Synthesized research content
                - citations: List of source URLs/citations
                - provider: "gemini"
                - model: Model used
                - tokens_used: Estimated token count
                - cost_usd: Research cost
                - citation_count: Number of citations

        Raises:
            Exception: If Gemini API fails
        """
        if not settings.GEMINI_GROUNDING_ENABLED:
            raise ValueError(
                "Gemini grounding is not enabled. "
                "Set GEMINI_GROUNDING_ENABLED=true in environment."
            )

        logger.info(f"Gemini grounded research: '{query}' (focus: {focus or 'general'})")

        try:
            # Construct focused prompt for neurosurgical expertise
            focus_context = ""
            if focus == "surgical_techniques":
                focus_context = """
                Focus specifically on:
                - Detailed surgical approaches and techniques
                - Step-by-step surgical procedures
                - Expert tips and clinical pearls from neurosurgeons
                - Intraoperative considerations and decision-making
                - Surgical anatomy and anatomical landmarks
                """
            elif focus == "clinical_management":
                focus_context = """
                Focus specifically on:
                - Clinical decision-making algorithms
                - Patient selection criteria
                - Preoperative planning and optimization
                - Postoperative care and monitoring
                - Complication management
                """
            else:
                focus_context = """
                Provide comprehensive neurosurgical information covering:
                - Surgical techniques and approaches
                - Clinical management strategies
                - Current best practices
                - Evidence-based recommendations
                """

            prompt = f"""You are an expert neurosurgery research assistant synthesizing PRACTICAL SURGICAL KNOWLEDGE from the web.

Research Query: {query}

{focus_context}

Provide a comprehensive synthesis of current neurosurgical expertise from authoritative sources including:
- Neurosurgical society guidelines and protocols
- Academic neurosurgical centers' clinical protocols
- Expert neurosurgeons' published techniques and recommendations
- Current standard of care from major neurosurgical institutions
- Evidence-based clinical practice guidelines

Format: Structured synthesis with clear sections and inline citations.
Emphasize ACTIONABLE clinical knowledge that neurosurgeons can apply in practice."""

            # Use new Google GenAI SDK (google-genai) with grounding support
            # This is different from google-generativeai package
            from google import genai as google_genai
            from google.genai import types

            # Create Gemini client
            client = google_genai.Client(api_key=settings.GOOGLE_API_KEY)

            # Create google_search tool
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            # Create generation config with tools
            config = types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=settings.GEMINI_GROUNDING_TEMPERATURE,
                max_output_tokens=max_tokens,
            )

            # Generate content with grounding
            response = client.models.generate_content(
                model=settings.GOOGLE_MODEL,
                contents=prompt,
                config=config,
            )

            # Extract research content
            research_content = response.text

            # Extract grounding metadata and citations
            citations = []
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]

                # Extract grounding metadata
                if hasattr(candidate, 'grounding_metadata'):
                    grounding = candidate.grounding_metadata

                    # Extract search entry point (optional)
                    if hasattr(grounding, 'search_entry_point'):
                        search_entry = grounding.search_entry_point
                        if hasattr(search_entry, 'rendered_content'):
                            logger.info(f"Gemini search entry point available")

                    # Extract grounding chunks (citations)
                    if hasattr(grounding, 'grounding_chunks'):
                        for chunk in grounding.grounding_chunks:
                            if hasattr(chunk, 'web'):
                                web_chunk = chunk.web
                                citation = {
                                    "url": getattr(web_chunk, 'uri', ''),
                                    "title": getattr(web_chunk, 'title', ''),
                                }
                                if citation["url"]:
                                    citations.append(citation["url"])

                    # Extract web search queries used
                    if hasattr(grounding, 'web_search_queries'):
                        queries_used = grounding.web_search_queries
                        logger.info(f"Gemini used {len(queries_used)} search queries")

            # Estimate tokens (Gemini doesn't always return usage)
            # Gemini 2.0 Flash typically: ~4 chars = 1 token
            estimated_input_tokens = len(prompt) // 4
            estimated_output_tokens = len(research_content) // 4
            total_tokens = estimated_input_tokens + estimated_output_tokens

            # Calculate cost (Gemini 2.0 Flash is MUCH cheaper than Perplexity)
            # Gemini: $0.075 per 1M input, $0.30 per 1M output
            # Perplexity: ~$1 per 1M tokens (both directions)
            cost_usd = (
                (estimated_input_tokens / 1000) * settings.GOOGLE_GEMINI_INPUT_COST_PER_1K +
                (estimated_output_tokens / 1000) * settings.GOOGLE_GEMINI_OUTPUT_COST_PER_1K
            )

            logger.info(
                f"Gemini grounded research complete: ~{total_tokens} tokens, "
                f"{len(citations)} citations, ${cost_usd:.6f} "
                f"(~96% cheaper than Perplexity)"
            )

            return {
                "research": research_content,
                "citations": citations,
                "provider": "gemini",
                "model": settings.GOOGLE_MODEL,
                "tokens_used": total_tokens,
                "input_tokens": estimated_input_tokens,
                "output_tokens": estimated_output_tokens,
                "cost_usd": cost_usd,
                "citation_count": len(citations)
            }

        except Exception as e:
            logger.error(f"Gemini grounded research error: {str(e)}", exc_info=True)
            raise

    async def external_research_ai(
        self,
        query: str,
        provider: Optional[str] = None,
        max_results: int = 10,
        focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unified AI research interface for external neurosurgical expertise synthesis

        Routes to appropriate AI provider (Perplexity or Gemini with Google Search grounding)
        for real-time web-based research on neurosurgical topics.

        Dual AI Provider Support:
        - Perplexity (sonar-pro): High-quality synthesis, ~$1 per 1M tokens
        - Gemini 2.0 Flash (grounding): Google Search integration, ~96% cheaper

        Args:
            query: Neurosurgical research query
            provider: AI provider to use ("perplexity", "gemini", or None for config default)
            max_results: Maximum number of sources/citations to return
            focus: Optional focus area ("surgical_techniques", "clinical_management", etc.)

        Returns:
            dict with keys:
                - research: Synthesized research content
                - sources: List of source citations (URLs)
                - provider: Provider used ("perplexity" or "gemini")
                - model: Specific model used
                - metadata: Additional research metadata (tokens, citations, cost savings)
                - cost_usd: Research cost

        Example:
            # Use Gemini (cheaper, Google Search grounding)
            result = await service.external_research_ai(
                query="glioblastoma surgical management",
                provider="gemini",
                focus="surgical_techniques"
            )

            # Use Perplexity (alternative provider)
            result = await service.external_research_ai(
                query="craniopharyngioma approaches",
                provider="perplexity",
                max_results=5
            )
        """
        # Determine provider
        if provider is None:
            provider = settings.EXTERNAL_RESEARCH_AI_PROVIDER

        logger.info(f"AI external research: '{query}' (provider: {provider})")

        # Route to appropriate provider
        if provider == "perplexity":
            if not self.perplexity_api_key:
                raise ValueError(
                    "Perplexity API key not configured. "
                    "Set PERPLEXITY_API_KEY in environment or disable AI research."
                )

            result = await self._generate_perplexity_research(
                query=query,
                max_tokens=settings.PERPLEXITY_MAX_TOKENS,
                focus=focus
            )

            return {
                "research": result["research"],
                "sources": result["citations"][:max_results],  # Limit to max_results
                "provider": "perplexity",
                "model": result["model"],
                "metadata": {
                    "tokens_used": result["tokens_used"],
                    "citation_count": result["citation_count"],
                    "focus": focus
                },
                "cost_usd": result["cost_usd"]
            }

        elif provider == "gemini_grounding" or provider == "gemini":
            # Phase 2: Gemini with Google Search grounding (NOW LIVE)
            if not settings.GEMINI_GROUNDING_ENABLED:
                raise ValueError(
                    "Gemini grounding is not enabled. "
                    "Set GEMINI_GROUNDING_ENABLED=true in environment."
                )

            result = await self._generate_gemini_grounded_research(
                query=query,
                max_tokens=settings.GEMINI_GROUNDING_MAX_TOKENS,
                focus=focus
            )

            return {
                "research": result["research"],
                "sources": result["citations"][:max_results],  # Limit to max_results
                "provider": "gemini",
                "model": result["model"],
                "metadata": {
                    "tokens_used": result["tokens_used"],
                    "citation_count": result["citation_count"],
                    "focus": focus,
                    "cost_savings_vs_perplexity": "~96%"  # Gemini is significantly cheaper
                },
                "cost_usd": result["cost_usd"]
            }

        else:
            raise ValueError(
                f"Unknown AI research provider: {provider}. "
                f"Use 'perplexity' or 'gemini' (both supported)"
            )
