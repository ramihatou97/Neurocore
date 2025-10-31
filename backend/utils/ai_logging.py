"""
Enhanced Logging for AI Operations
Comprehensive logging system for GPT-4o, structured outputs, and fact-checking

Features:
- Detailed operation logging with context
- Cost tracking per operation
- Performance metrics (latency, throughput)
- Error tracking and diagnostics
- Structured log format for analytics
- Log aggregation utilities
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import time

from backend.utils import get_logger

logger = get_logger(__name__)


class AIOperationLogger:
    """
    Enhanced logger for AI operations with structured output
    """

    def __init__(self, operation_name: str):
        """
        Initialize AI operation logger

        Args:
            operation_name: Name of the AI operation (e.g., "gpt4o_structured_output")
        """
        self.operation_name = operation_name
        self.start_time = None
        self.metadata = {}

    def __enter__(self):
        """Start operation logging"""
        self.start_time = time.time()
        logger.info(f"🚀 Starting AI operation: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Complete operation logging"""
        duration = time.time() - self.start_time

        if exc_type is None:
            # Success
            logger.info(
                f"✅ AI operation completed: {self.operation_name}",
                extra={
                    "operation": self.operation_name,
                    "duration_seconds": duration,
                    "status": "success",
                    **self.metadata
                }
            )
        else:
            # Failure
            logger.error(
                f"❌ AI operation failed: {self.operation_name}",
                extra={
                    "operation": self.operation_name,
                    "duration_seconds": duration,
                    "status": "failed",
                    "error_type": exc_type.__name__,
                    "error_message": str(exc_val),
                    **self.metadata
                },
                exc_info=True
            )

    def log_metadata(self, **kwargs):
        """Add metadata to operation log"""
        self.metadata.update(kwargs)


def log_ai_operation(operation_type: str):
    """
    Decorator for logging AI operations with detailed metrics

    Args:
        operation_type: Type of AI operation (e.g., "text_generation", "structured_output")

    Usage:
        @log_ai_operation("gpt4o_structured_output")
        async def generate_with_schema(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            operation_id = f"{operation_type}_{int(start_time * 1000)}"

            logger.info(
                f"🎯 AI Operation Started: {operation_type}",
                extra={
                    "operation_id": operation_id,
                    "operation_type": operation_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            try:
                result = await func(*args, **kwargs)

                duration = time.time() - start_time

                # Extract metrics from result
                cost = result.get("cost_usd", 0) if isinstance(result, dict) else 0
                tokens = result.get("tokens_used", 0) if isinstance(result, dict) else 0
                model = result.get("model", "unknown") if isinstance(result, dict) else "unknown"
                provider = result.get("provider", "unknown") if isinstance(result, dict) else "unknown"

                logger.info(
                    f"✅ AI Operation Success: {operation_type}",
                    extra={
                        "operation_id": operation_id,
                        "operation_type": operation_type,
                        "status": "success",
                        "duration_seconds": duration,
                        "cost_usd": cost,
                        "tokens_used": tokens,
                        "model": model,
                        "provider": provider,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                logger.error(
                    f"❌ AI Operation Failed: {operation_type}",
                    extra={
                        "operation_id": operation_id,
                        "operation_type": operation_type,
                        "status": "failed",
                        "duration_seconds": duration,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    exc_info=True
                )
                raise

        return wrapper
    return decorator


class StructuredOutputLogger:
    """Logger specialized for structured output operations"""

    @staticmethod
    def log_schema_request(schema_name: str, prompt_length: int, temperature: float):
        """Log structured output request"""
        logger.info(
            f"📋 Structured Output Request: {schema_name}",
            extra={
                "event_type": "structured_output_request",
                "schema_name": schema_name,
                "prompt_length": prompt_length,
                "temperature": temperature,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def log_schema_response(
        schema_name: str,
        success: bool,
        validation_passed: bool,
        cost: float,
        duration: float
    ):
        """Log structured output response"""
        logger.info(
            f"✨ Structured Output Response: {schema_name}",
            extra={
                "event_type": "structured_output_response",
                "schema_name": schema_name,
                "success": success,
                "validation_passed": validation_passed,
                "cost_usd": cost,
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def log_schema_validation_error(schema_name: str, error: str):
        """Log schema validation error"""
        logger.error(
            f"⚠️ Schema Validation Error: {schema_name}",
            extra={
                "event_type": "schema_validation_error",
                "schema_name": schema_name,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


class FactCheckLogger:
    """Logger specialized for fact-checking operations"""

    @staticmethod
    def log_fact_check_start(chapter_id: str, section_count: int, source_count: int):
        """Log fact-check operation start"""
        logger.info(
            f"🔍 Fact-Check Started: Chapter {chapter_id}",
            extra={
                "event_type": "fact_check_start",
                "chapter_id": chapter_id,
                "section_count": section_count,
                "source_count": source_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def log_fact_check_complete(
        chapter_id: str,
        accuracy: float,
        total_claims: int,
        verified_claims: int,
        critical_issues: int,
        cost: float,
        passed: bool
    ):
        """Log fact-check operation completion"""
        status_emoji = "✅" if passed else "⚠️"
        logger.info(
            f"{status_emoji} Fact-Check Complete: Chapter {chapter_id}",
            extra={
                "event_type": "fact_check_complete",
                "chapter_id": chapter_id,
                "overall_accuracy": accuracy,
                "total_claims": total_claims,
                "verified_claims": verified_claims,
                "critical_issues_count": critical_issues,
                "cost_usd": cost,
                "passed": passed,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def log_critical_issue(chapter_id: str, issue: str, severity: str):
        """Log critical fact-check issue"""
        logger.warning(
            f"🚨 Critical Fact-Check Issue: {issue[:100]}...",
            extra={
                "event_type": "fact_check_critical_issue",
                "chapter_id": chapter_id,
                "issue": issue,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


class BatchOperationLogger:
    """Logger specialized for batch operations"""

    @staticmethod
    def log_batch_start(batch_type: str, request_count: int, max_concurrent: int):
        """Log batch operation start"""
        logger.info(
            f"📦 Batch Operation Started: {batch_type}",
            extra={
                "event_type": "batch_start",
                "batch_type": batch_type,
                "request_count": request_count,
                "max_concurrent": max_concurrent,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def log_batch_progress(batch_type: str, completed: int, total: int, elapsed: float):
        """Log batch operation progress"""
        progress_pct = (completed / total * 100) if total > 0 else 0
        rate = completed / elapsed if elapsed > 0 else 0

        logger.info(
            f"📊 Batch Progress: {batch_type} ({completed}/{total} - {progress_pct:.1f}%)",
            extra={
                "event_type": "batch_progress",
                "batch_type": batch_type,
                "completed": completed,
                "total": total,
                "progress_percentage": progress_pct,
                "requests_per_second": rate,
                "elapsed_seconds": elapsed,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def log_batch_complete(
        batch_type: str,
        total: int,
        successful: int,
        failed: int,
        cost: float,
        duration: float
    ):
        """Log batch operation completion"""
        success_rate = (successful / total * 100) if total > 0 else 0

        logger.info(
            f"✅ Batch Complete: {batch_type} ({successful}/{total} successful - {success_rate:.1f}%)",
            extra={
                "event_type": "batch_complete",
                "batch_type": batch_type,
                "total_requests": total,
                "successful": successful,
                "failed": failed,
                "success_rate": success_rate,
                "total_cost_usd": cost,
                "duration_seconds": duration,
                "requests_per_second": total / duration if duration > 0 else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


class CostTracker:
    """Track AI operation costs for analytics"""

    _costs: Dict[str, list] = {
        "gpt4o": [],
        "embeddings": [],
        "fact_checking": [],
        "batch_operations": []
    }

    @classmethod
    def track_cost(cls, operation_type: str, cost: float, metadata: Optional[Dict] = None):
        """Track cost for an operation"""
        record = {
            "cost_usd": cost,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }

        if operation_type not in cls._costs:
            cls._costs[operation_type] = []

        cls._costs[operation_type].append(record)

        logger.debug(
            f"💰 Cost Tracked: {operation_type} - ${cost:.6f}",
            extra={
                "event_type": "cost_tracked",
                "operation_type": operation_type,
                "cost_usd": cost,
                **record
            }
        )

    @classmethod
    def get_total_cost(cls, operation_type: Optional[str] = None) -> float:
        """Get total cost for operation type or all operations"""
        if operation_type:
            return sum(r["cost_usd"] for r in cls._costs.get(operation_type, []))
        else:
            return sum(
                sum(r["cost_usd"] for r in records)
                for records in cls._costs.values()
            )

    @classmethod
    def get_cost_summary(cls) -> Dict[str, Any]:
        """Get comprehensive cost summary"""
        summary = {}

        for op_type, records in cls._costs.items():
            if records:
                costs = [r["cost_usd"] for r in records]
                summary[op_type] = {
                    "total_cost": sum(costs),
                    "operation_count": len(costs),
                    "average_cost": sum(costs) / len(costs),
                    "min_cost": min(costs),
                    "max_cost": max(costs)
                }

        summary["overall_total"] = cls.get_total_cost()

        return summary

    @classmethod
    def reset(cls):
        """Reset cost tracking"""
        cls._costs = {key: [] for key in cls._costs.keys()}
        logger.info("💰 Cost tracker reset")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def log_gpt4o_request(prompt: str, model: str, max_tokens: int, temperature: float):
    """Log GPT-4o request"""
    logger.debug(
        f"🤖 GPT-4o Request",
        extra={
            "event_type": "gpt4o_request",
            "model": model,
            "prompt_length": len(prompt),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


def log_gpt4o_response(
    model: str,
    tokens_used: int,
    cost: float,
    duration: float,
    success: bool = True
):
    """Log GPT-4o response"""
    logger.debug(
        f"🤖 GPT-4o Response",
        extra={
            "event_type": "gpt4o_response",
            "model": model,
            "tokens_used": tokens_used,
            "cost_usd": cost,
            "duration_seconds": duration,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


def log_provider_fallback(primary: str, fallback: str, reason: str):
    """Log AI provider fallback"""
    logger.warning(
        f"🔄 Provider Fallback: {primary} → {fallback}",
        extra={
            "event_type": "provider_fallback",
            "primary_provider": primary,
            "fallback_provider": fallback,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


def log_rate_limit(provider: str, retry_after: int):
    """Log rate limit hit"""
    logger.warning(
        f"⏳ Rate Limit Hit: {provider}",
        extra={
            "event_type": "rate_limit",
            "provider": provider,
            "retry_after_seconds": retry_after,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
