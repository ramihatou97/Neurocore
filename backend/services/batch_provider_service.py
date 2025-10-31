"""
Batch AI Provider Service
Handles parallel and batch processing of AI requests for efficiency

This service provides:
- Parallel processing of multiple AI requests (using asyncio)
- Intelligent batching with rate limiting
- Progress tracking for long-running batch jobs
- Cost optimization through efficient request grouping
- Support for mixed task types in a single batch

Phase 4: Advanced features for high-throughput AI operations
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum

from backend.services.ai_provider_service import AIProviderService, AITask, AIProvider
from backend.schemas.ai_schemas import get_schema_by_name
from backend.utils import get_logger

logger = get_logger(__name__)


class BatchStatus(str, Enum):
    """Batch processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


class BatchProviderService:
    """
    Service for batch and parallel AI request processing

    Features:
    - Process multiple prompts in parallel (faster than sequential)
    - Automatic rate limiting and error handling
    - Progress tracking and callbacks
    - Cost aggregation and reporting
    - Support for structured outputs in batches
    """

    def __init__(self, max_concurrent: int = 5):
        """
        Initialize batch provider service

        Args:
            max_concurrent: Maximum number of concurrent AI requests (default: 5)
                           Adjust based on API rate limits
        """
        self.ai_service = AIProviderService()
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def batch_generate_text(
        self,
        prompts: List[Dict[str, Any]],
        task: AITask,
        provider: Optional[AIProvider] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Generate text for multiple prompts in parallel

        Args:
            prompts: List of prompt dictionaries with 'prompt' and optional 'system_prompt'
            task: AI task type for routing
            provider: Optional provider override
            max_tokens: Max tokens per response
            temperature: Temperature for generation
            progress_callback: Optional callback(completed, total) for progress updates

        Returns:
            Dictionary with results, errors, and summary statistics

        Example:
            prompts = [
                {"prompt": "Explain craniotomy"},
                {"prompt": "Explain glioblastoma", "system_prompt": "Be concise"},
            ]
            results = await batch_service.batch_generate_text(prompts, AITask.METADATA_EXTRACTION)
        """
        logger.info(f"Starting batch text generation: {len(prompts)} prompts")

        start_time = datetime.utcnow()
        results = []
        errors = []
        total_cost = 0.0
        total_tokens = 0
        completed = 0

        async def process_single_prompt(prompt_data: Dict[str, Any], index: int):
            """Process a single prompt with rate limiting"""
            async with self.semaphore:
                try:
                    result = await self.ai_service.generate_text(
                        prompt=prompt_data["prompt"],
                        task=task,
                        provider=provider,
                        system_prompt=prompt_data.get("system_prompt"),
                        max_tokens=max_tokens,
                        temperature=temperature
                    )

                    # Add index for ordering
                    result["batch_index"] = index
                    result["input_prompt"] = prompt_data["prompt"][:100] + "..."  # Truncate for logging

                    return {"success": True, "result": result}

                except Exception as e:
                    logger.error(f"Batch item {index} failed: {str(e)}")
                    return {
                        "success": False,
                        "error": str(e),
                        "batch_index": index,
                        "input_prompt": prompt_data["prompt"][:100] + "..."
                    }

        # Create tasks for all prompts
        tasks = [
            process_single_prompt(prompt, idx)
            for idx, prompt in enumerate(prompts)
        ]

        # Process with progress tracking
        for coro in asyncio.as_completed(tasks):
            item_result = await coro
            completed += 1

            if item_result["success"]:
                result_data = item_result["result"]
                results.append(result_data)
                total_cost += result_data.get("cost_usd", 0.0)
                total_tokens += result_data.get("tokens_used", 0)
            else:
                errors.append({
                    "batch_index": item_result["batch_index"],
                    "error": item_result["error"],
                    "prompt_preview": item_result["input_prompt"]
                })

            # Progress callback
            if progress_callback:
                progress_callback(completed, len(prompts))

        # Calculate duration
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # Determine status
        if len(errors) == 0:
            status = BatchStatus.COMPLETED
        elif len(results) == 0:
            status = BatchStatus.FAILED
        else:
            status = BatchStatus.PARTIALLY_COMPLETED

        logger.info(
            f"Batch generation complete: {len(results)}/{len(prompts)} successful, "
            f"${total_cost:.4f}, {duration:.2f}s"
        )

        return {
            "status": status.value,
            "results": results,
            "errors": errors,
            "summary": {
                "total_requests": len(prompts),
                "successful": len(results),
                "failed": len(errors),
                "total_cost_usd": total_cost,
                "total_tokens": total_tokens,
                "average_cost_per_request": total_cost / len(results) if results else 0.0,
                "duration_seconds": duration,
                "requests_per_second": len(prompts) / duration if duration > 0 else 0
            },
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat()
        }

    async def batch_generate_structured(
        self,
        prompts: List[Dict[str, Any]],
        schema_name: str,
        task: AITask,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Generate structured outputs for multiple prompts in parallel

        Uses GPT-4o structured outputs for guaranteed schema compliance.
        Ideal for batch metadata extraction, fact-checking, or analysis.

        Args:
            prompts: List of prompt dictionaries with 'prompt' key
            schema_name: Name of schema to use (from ai_schemas.py)
            task: AI task type
            system_prompt: Optional system prompt (applied to all)
            max_tokens: Max tokens per response
            temperature: Temperature for generation (0.3 recommended for structured)
            progress_callback: Optional callback(completed, total)

        Returns:
            Dictionary with parsed structured results and summary

        Example:
            prompts = [
                {"prompt": "Analyze: Craniotomy for tumor"},
                {"prompt": "Analyze: Glioblastoma treatment"},
            ]
            results = await batch_service.batch_generate_structured(
                prompts,
                schema_name="chapter_analysis",
                task=AITask.METADATA_EXTRACTION
            )
        """
        logger.info(f"Starting batch structured generation: {len(prompts)} prompts with {schema_name} schema")

        # Get schema
        schema = get_schema_by_name(schema_name)

        start_time = datetime.utcnow()
        results = []
        errors = []
        total_cost = 0.0
        completed = 0

        async def process_single_structured(prompt_data: Dict[str, Any], index: int):
            """Process a single structured output request"""
            async with self.semaphore:
                try:
                    result = await self.ai_service.generate_text_with_schema(
                        prompt=prompt_data["prompt"],
                        schema=schema,
                        task=task,
                        system_prompt=system_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )

                    # Add index and preview
                    result["batch_index"] = index
                    result["input_prompt"] = prompt_data["prompt"][:100] + "..."

                    return {"success": True, "result": result}

                except Exception as e:
                    logger.error(f"Batch structured item {index} failed: {str(e)}")
                    return {
                        "success": False,
                        "error": str(e),
                        "batch_index": index,
                        "input_prompt": prompt_data["prompt"][:100] + "..."
                    }

        # Create tasks
        tasks = [
            process_single_structured(prompt, idx)
            for idx, prompt in enumerate(prompts)
        ]

        # Process with progress tracking
        for coro in asyncio.as_completed(tasks):
            item_result = await coro
            completed += 1

            if item_result["success"]:
                result_data = item_result["result"]
                results.append(result_data)
                total_cost += result_data.get("cost_usd", 0.0)
            else:
                errors.append({
                    "batch_index": item_result["batch_index"],
                    "error": item_result["error"],
                    "prompt_preview": item_result["input_prompt"]
                })

            # Progress callback
            if progress_callback:
                progress_callback(completed, len(prompts))

        # Calculate stats
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        if len(errors) == 0:
            status = BatchStatus.COMPLETED
        elif len(results) == 0:
            status = BatchStatus.FAILED
        else:
            status = BatchStatus.PARTIALLY_COMPLETED

        logger.info(
            f"Batch structured generation complete: {len(results)}/{len(prompts)} successful, "
            f"${total_cost:.4f}, {duration:.2f}s"
        )

        return {
            "status": status.value,
            "results": results,
            "errors": errors,
            "schema_name": schema_name,
            "summary": {
                "total_requests": len(prompts),
                "successful": len(results),
                "failed": len(errors),
                "total_cost_usd": total_cost,
                "average_cost_per_request": total_cost / len(results) if results else 0.0,
                "duration_seconds": duration,
                "requests_per_second": len(prompts) / duration if duration > 0 else 0
            },
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat()
        }

    async def batch_generate_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-3-large",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Generate embeddings for multiple texts in parallel

        Args:
            texts: List of texts to embed
            model: Embedding model to use
            progress_callback: Optional callback(completed, total)

        Returns:
            Dictionary with embeddings and summary

        Example:
            texts = ["Craniotomy procedure", "Glioblastoma treatment", ...]
            results = await batch_service.batch_generate_embeddings(texts)
        """
        logger.info(f"Starting batch embedding generation: {len(texts)} texts")

        start_time = datetime.utcnow()
        results = []
        errors = []
        total_cost = 0.0
        completed = 0

        async def process_single_embedding(text: str, index: int):
            """Process a single embedding request"""
            async with self.semaphore:
                try:
                    result = await self.ai_service.generate_embedding(
                        text=text,
                        model=model
                    )

                    result["batch_index"] = index
                    result["text_preview"] = text[:100] + "..."

                    return {"success": True, "result": result}

                except Exception as e:
                    logger.error(f"Batch embedding {index} failed: {str(e)}")
                    return {
                        "success": False,
                        "error": str(e),
                        "batch_index": index,
                        "text_preview": text[:100] + "..."
                    }

        # Create tasks
        tasks = [
            process_single_embedding(text, idx)
            for idx, text in enumerate(texts)
        ]

        # Process
        for coro in asyncio.as_completed(tasks):
            item_result = await coro
            completed += 1

            if item_result["success"]:
                result_data = item_result["result"]
                results.append(result_data)
                total_cost += result_data.get("cost_usd", 0.0)
            else:
                errors.append({
                    "batch_index": item_result["batch_index"],
                    "error": item_result["error"],
                    "text_preview": item_result["text_preview"]
                })

            if progress_callback:
                progress_callback(completed, len(texts))

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        status = (
            BatchStatus.COMPLETED if len(errors) == 0
            else BatchStatus.FAILED if len(results) == 0
            else BatchStatus.PARTIALLY_COMPLETED
        )

        logger.info(
            f"Batch embedding complete: {len(results)}/{len(texts)} successful, "
            f"${total_cost:.4f}, {duration:.2f}s"
        )

        return {
            "status": status.value,
            "results": results,
            "errors": errors,
            "model": model,
            "summary": {
                "total_requests": len(texts),
                "successful": len(results),
                "failed": len(errors),
                "total_cost_usd": total_cost,
                "average_cost_per_request": total_cost / len(results) if results else 0.0,
                "duration_seconds": duration,
                "requests_per_second": len(texts) / duration if duration > 0 else 0
            },
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat()
        }

    def get_optimal_batch_size(self, estimated_tokens_per_request: int) -> int:
        """
        Calculate optimal batch size based on token estimates and rate limits

        Args:
            estimated_tokens_per_request: Estimated tokens per request

        Returns:
            Recommended batch size
        """
        # Simple heuristic: adjust based on request size
        if estimated_tokens_per_request < 500:
            return min(20, self.max_concurrent * 4)
        elif estimated_tokens_per_request < 2000:
            return min(10, self.max_concurrent * 2)
        else:
            return self.max_concurrent

    async def batch_with_retry(
        self,
        batch_func: Callable,
        *args,
        max_retries: int = 2,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute batch operation with automatic retry on failure

        Args:
            batch_func: Batch function to call (e.g., self.batch_generate_text)
            max_retries: Maximum number of retries
            *args, **kwargs: Arguments to pass to batch_func

        Returns:
            Batch results with retry information
        """
        retries = 0
        last_error = None

        while retries <= max_retries:
            try:
                result = await batch_func(*args, **kwargs)

                # If there were retries, add retry info
                if retries > 0:
                    result["retry_info"] = {
                        "retries_needed": retries,
                        "max_retries": max_retries
                    }

                return result

            except Exception as e:
                last_error = e
                retries += 1
                logger.warning(f"Batch operation failed (attempt {retries}/{max_retries + 1}): {str(e)}")

                if retries <= max_retries:
                    # Exponential backoff
                    wait_time = 2 ** retries
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)

        # All retries exhausted
        logger.error(f"Batch operation failed after {max_retries + 1} attempts")
        raise last_error
