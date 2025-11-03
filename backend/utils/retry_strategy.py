"""
Retry Strategy Module for The Neurosurgical Core of Knowledge

Phase 2: Production-Ready Error Handling
Provides intelligent retry logic with exponential backoff and jitter
"""

import logging
import time
import random
import asyncio
from typing import Callable, Optional, Tuple, Type, Union, Any
from functools import wraps
import inspect

from backend.exceptions import (
    ExternalServiceError,
    OpenAIAPIError,
    AnthropicAPIError,
    GoogleAPIError,
    PerplexityAPIError,
    DatabaseConnectionError,
    DatabaseTimeoutError,
)


logger = logging.getLogger(__name__)


# Exceptions that should trigger retry (transient failures)
RETRYABLE_EXCEPTIONS = (
    # External service timeouts and rate limits
    ExternalServiceError,
    OpenAIAPIError,
    AnthropicAPIError,
    GoogleAPIError,
    PerplexityAPIError,
    # Database connection issues
    DatabaseConnectionError,
    DatabaseTimeoutError,
    # Network errors
    ConnectionError,
    TimeoutError,
)


class RetryStrategy:
    """
    Configurable retry strategy with exponential backoff

    Features:
    - Exponential backoff with configurable base delay
    - Jitter to prevent thundering herd
    - Maximum retry attempts
    - Selective retry based on exception type
    - Detailed logging of retry attempts
    - Integration with circuit breaker
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS,
        on_retry: Optional[Callable] = None
    ):
        """
        Initialize retry strategy

        Args:
            max_attempts: Maximum number of retry attempts (including initial attempt)
            base_delay: Base delay in seconds (multiplied exponentially)
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff (typically 2.0)
            jitter: Add random jitter to prevent thundering herd
            retryable_exceptions: Tuple of exception types that should trigger retry
            on_retry: Optional callback function called before each retry

        Example:
            >>> strategy = RetryStrategy(
            ...     max_attempts=5,
            ...     base_delay=1.0,
            ...     max_delay=60.0,
            ...     exponential_base=2.0,
            ...     jitter=True
            ... )
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
        self.on_retry = on_retry

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt number

        Uses exponential backoff: delay = base_delay * (exponential_base ^ attempt)
        With optional jitter: delay * random(0.5, 1.5)

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        # Add jitter
        if self.jitter:
            jitter_factor = random.uniform(0.5, 1.5)
            delay *= jitter_factor

        return delay

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if the exception should trigger a retry

        Args:
            exception: The exception that occurred
            attempt: Current attempt number (0-indexed)

        Returns:
            True if should retry, False otherwise
        """
        # Check if we've exhausted retry attempts
        # attempt is 0-indexed, so with max_attempts=3, valid attempts are 0,1,2
        # After attempt=2 (3rd attempt), we should not retry
        if attempt >= self.max_attempts - 1:
            return False

        # Check if exception is retryable
        return isinstance(exception, self.retryable_exceptions)

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic (synchronous)

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            Last exception if all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                if not self.should_retry(e, attempt):
                    # Don't retry, re-raise immediately
                    raise

                # Calculate delay
                delay = self.calculate_delay(attempt)

                # Log retry attempt
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_attempts} failed: {str(e)}. "
                    f"Retrying in {delay:.2f}s...",
                    extra={
                        "function": getattr(func, '__name__', 'unknown'),
                        "attempt": attempt + 1,
                        "max_attempts": self.max_attempts,
                        "delay": delay,
                        "exception_type": type(e).__name__
                    }
                )

                # Call on_retry callback if provided
                if self.on_retry:
                    self.on_retry(attempt, e, delay)

                # Wait before retrying
                time.sleep(delay)

        # All retries exhausted, raise last exception
        func_name = getattr(func, '__name__', 'unknown')
        logger.error(
            f"All {self.max_attempts} attempts failed for {func_name}",
            extra={
                "function": func_name,
                "final_exception": str(last_exception)
            }
        )
        raise last_exception

    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute an async function with retry logic

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            Last exception if all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                if not self.should_retry(e, attempt):
                    # Don't retry, re-raise immediately
                    raise

                # Calculate delay
                delay = self.calculate_delay(attempt)

                # Log retry attempt
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_attempts} failed: {str(e)}. "
                    f"Retrying in {delay:.2f}s...",
                    extra={
                        "function": getattr(func, '__name__', 'unknown'),
                        "attempt": attempt + 1,
                        "max_attempts": self.max_attempts,
                        "delay": delay,
                        "exception_type": type(e).__name__
                    }
                )

                # Call on_retry callback if provided
                if self.on_retry:
                    self.on_retry(attempt, e, delay)

                # Wait before retrying
                await asyncio.sleep(delay)

        # All retries exhausted, raise last exception
        func_name = getattr(func, '__name__', 'unknown')
        logger.error(
            f"All {self.max_attempts} attempts failed for {func_name}",
            extra={
                "function": func_name,
                "final_exception": str(last_exception)
            }
        )
        raise last_exception


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS,
    on_retry: Optional[Callable] = None
):
    """
    Decorator to add retry logic to a function

    Args:
        max_attempts: Maximum number of retry attempts (including initial attempt)
        base_delay: Base delay in seconds (multiplied exponentially)
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff (typically 2.0)
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Tuple of exception types that should trigger retry
        on_retry: Optional callback function called before each retry

    Example:
        >>> @with_retry(max_attempts=5, base_delay=1.0)
        ... def call_external_api():
        ...     return requests.get("https://api.example.com/data")

        >>> @with_retry(max_attempts=3, base_delay=2.0)
        ... async def call_async_api():
        ...     async with aiohttp.ClientSession() as session:
        ...         async with session.get("https://api.example.com") as resp:
        ...             return await resp.json()
    """
    def decorator(func: Callable) -> Callable:
        strategy = RetryStrategy(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions,
            on_retry=on_retry
        )

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await strategy.execute_async(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return strategy.execute(func, *args, **kwargs)

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Predefined retry strategies for common scenarios

def retry_external_api(
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0
):
    """
    Retry strategy for external API calls

    Default: 5 attempts, 1s base delay, 60s max delay
    Delays: 1s, 2s, 4s, 8s, 16s (with jitter)

    Example:
        >>> @retry_external_api(max_attempts=5)
        ... def call_openai_api(prompt: str):
        ...     return openai.ChatCompletion.create(...)
    """
    return with_retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=True,
        retryable_exceptions=RETRYABLE_EXCEPTIONS
    )


def retry_database(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0
):
    """
    Retry strategy for database operations

    Default: 3 attempts, 0.5s base delay, 10s max delay
    Delays: 0.5s, 1s, 2s (with jitter)

    Example:
        >>> @retry_database(max_attempts=3)
        ... def fetch_chapter(chapter_id: str):
        ...     return db.query(Chapter).filter_by(id=chapter_id).first()
    """
    return with_retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=True,
        retryable_exceptions=(
            DatabaseConnectionError,
            DatabaseTimeoutError,
            ConnectionError,
            TimeoutError,
        )
    )


def retry_fast(
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 1.0
):
    """
    Fast retry strategy for quick operations

    Default: 3 attempts, 0.1s base delay, 1s max delay
    Delays: 0.1s, 0.2s, 0.4s (with jitter)

    Example:
        >>> @retry_fast(max_attempts=3)
        ... def check_cache(key: str):
        ...     return redis.get(key)
    """
    return with_retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=True,
        retryable_exceptions=RETRYABLE_EXCEPTIONS
    )


def retry_aggressive(
    max_attempts: int = 10,
    base_delay: float = 2.0,
    max_delay: float = 300.0
):
    """
    Aggressive retry strategy for critical operations

    Default: 10 attempts, 2s base delay, 300s (5min) max delay
    Delays: 2s, 4s, 8s, 16s, 32s, 64s, 128s, 256s, 300s, 300s (with jitter)

    Use for critical operations that must succeed eventually.

    Example:
        >>> @retry_aggressive(max_attempts=10)
        ... def critical_operation():
        ...     return perform_critical_task()
    """
    return with_retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=True,
        retryable_exceptions=RETRYABLE_EXCEPTIONS
    )


# Example usage for migration guide
if __name__ == "__main__":
    # Example 1: Simple sync function
    @with_retry(max_attempts=3, base_delay=1.0)
    def fetch_data():
        print("Attempting to fetch data...")
        import random
        if random.random() < 0.7:  # 70% chance of failure
            raise ConnectionError("Connection failed")
        return {"data": "success"}

    # Example 2: Async function
    @with_retry(max_attempts=5, base_delay=2.0)
    async def async_fetch_data():
        print("Attempting async fetch...")
        import random
        if random.random() < 0.5:  # 50% chance of failure
            raise TimeoutError("Request timed out")
        return {"data": "success"}

    # Example 3: Using predefined strategy
    @retry_external_api(max_attempts=5)
    def call_api():
        print("Calling external API...")
        return {"status": "ok"}

    # Test synchronous retry
    try:
        result = fetch_data()
        print(f"Success: {result}")
    except Exception as e:
        print(f"Failed after all retries: {e}")

    # Test async retry
    try:
        asyncio.run(async_fetch_data())
    except Exception as e:
        print(f"Async failed after all retries: {e}")
