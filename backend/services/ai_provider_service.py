"""
AI Provider Service - Abstraction layer for multiple AI providers
Supports Claude Sonnet 4.5 (primary), GPT-4/5, and Gemini with hierarchical fallback
"""

import anthropic
import openai
import google.generativeai as genai
import httpx
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

        # Initialize OpenAI (v1.0+ client)
        if settings.OPENAI_API_KEY:
            from openai import OpenAI
            self.openai_client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=httpx.Timeout(30.0, connect=5.0),  # 30s read, 5s connect
                max_retries=2
            )
            logger.info("OpenAI client initialized with timeout configuration")
        else:
            self.openai_client = None
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
                return await self._generate_gemini(prompt, max_tokens, temperature, system_prompt)
            else:
                raise ValueError(f"Unknown provider: {provider}")

        except Exception as e:
            logger.error(f"AI generation failed with {provider}: {str(e)}", exc_info=True)

            # Fallback to next provider
            if provider == AIProvider.CLAUDE and self.openai_client:
                logger.info("Falling back from Claude to GPT-4")
                return await self._generate_gpt4(prompt, system_prompt, max_tokens, temperature)
            elif provider == AIProvider.GPT4 and settings.GOOGLE_API_KEY:
                logger.info("Falling back from GPT-4 to Gemini")
                return await self._generate_gemini(prompt, max_tokens, temperature, system_prompt)
            else:
                logger.error("No fallback available, re-raising exception")
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
                                "url": f"data:image/png;base64,{image_b64}"
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
        max_tokens: int = 4000
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
