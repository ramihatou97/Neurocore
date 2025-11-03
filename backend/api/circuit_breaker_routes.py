"""
Circuit Breaker Monitoring API Routes
Provides health status and control endpoints for AI provider circuit breakers
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List

from backend.services.circuit_breaker import circuit_breaker_manager
from backend.utils import get_logger, get_current_admin_user
from backend.database import User

logger = get_logger(__name__)

router = APIRouter(prefix="/circuit-breakers", tags=["circuit-breakers"])


class CircuitBreakerStatusResponse(BaseModel):
    """Response model for circuit breaker status"""
    providers: Dict[str, Dict[str, Any]]
    available_providers: List[str]
    all_healthy: bool
    summary: Dict[str, int]


@router.get(
    "/status",
    response_model=CircuitBreakerStatusResponse,
    summary="Get circuit breaker status for all AI providers",
    description="""
    Returns comprehensive status of all circuit breakers.

    Includes:
    - Current state (CLOSED/OPEN/HALF_OPEN) for each provider
    - Failure and success counts
    - Availability status
    - Success rates

    Use this endpoint to monitor AI provider health.
    """
)
async def get_circuit_breaker_status() -> CircuitBreakerStatusResponse:
    """
    Get status of all circuit breakers

    No authentication required (monitoring endpoint)
    """
    try:
        # Get all stats
        all_stats = circuit_breaker_manager.get_all_stats()

        # Get available providers
        available = circuit_breaker_manager.get_available_providers()

        # Calculate summary
        summary = {
            'total_providers': len(all_stats),
            'available': len(available),
            'closed': sum(1 for s in all_stats.values() if s['state'] == 'closed'),
            'open': sum(1 for s in all_stats.values() if s['state'] == 'open'),
            'half_open': sum(1 for s in all_stats.values() if s['state'] == 'half_open')
        }

        # Check if all healthy
        all_healthy = summary['open'] == 0

        return CircuitBreakerStatusResponse(
            providers=all_stats,
            available_providers=available,
            all_healthy=all_healthy,
            summary=summary
        )

    except Exception as e:
        logger.error(f"Failed to get circuit breaker status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve circuit breaker status"
        )


@router.get(
    "/{provider}/status",
    summary="Get circuit breaker status for specific provider",
    description="Returns detailed status for a single AI provider circuit breaker"
)
async def get_provider_circuit_breaker_status(provider: str) -> Dict[str, Any]:
    """
    Get status of specific circuit breaker

    Args:
        provider: Provider name (claude, gpt4, gemini, perplexity)
    """
    try:
        breaker = circuit_breaker_manager.get_breaker(provider)
        return breaker.get_stats()

    except Exception as e:
        logger.error(f"Failed to get status for {provider}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve status for provider: {provider}"
        )


@router.post(
    "/{provider}/reset",
    summary="Reset circuit breaker for specific provider",
    description="""
    Manually reset a circuit breaker to CLOSED state.

    **Requires admin authentication.**

    Use cases:
    - After fixing provider API issues
    - For testing
    - Emergency recovery
    """
)
async def reset_provider_circuit_breaker(
    provider: str,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Reset circuit breaker (admin only)

    Args:
        provider: Provider name
        current_user: Admin user (from dependency)
    """
    try:
        breaker = circuit_breaker_manager.get_breaker(provider)
        breaker.reset()

        logger.info(
            f"Circuit breaker manually reset for {provider} "
            f"by admin: {current_user.email}"
        )

        return {
            "status": "success",
            "message": f"Circuit breaker reset for {provider}",
            "provider": provider,
            "new_state": "closed"
        }

    except Exception as e:
        logger.error(f"Failed to reset circuit breaker for {provider}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset circuit breaker for: {provider}"
        )


@router.post(
    "/reset-all",
    summary="Reset all circuit breakers",
    description="""
    Reset all circuit breakers to CLOSED state.

    **Requires admin authentication.**

    ⚠️ Use with caution - this resets all providers.
    """
)
async def reset_all_circuit_breakers(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Reset all circuit breakers (admin only)

    Args:
        current_user: Admin user (from dependency)
    """
    try:
        circuit_breaker_manager.reset_all()

        logger.warning(
            f"All circuit breakers manually reset by admin: {current_user.email}"
        )

        return {
            "status": "success",
            "message": "All circuit breakers reset",
            "reset_count": len(circuit_breaker_manager.breakers)
        }

    except Exception as e:
        logger.error(f"Failed to reset all circuit breakers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset circuit breakers"
        )


@router.post(
    "/{provider}/force-open",
    summary="Force open circuit breaker (disable provider)",
    description="""
    Manually open a circuit breaker to disable a provider.

    **Requires admin authentication.**

    Use cases:
    - Planned maintenance
    - Cost control
    - Testing fallback behavior
    """
)
async def force_open_circuit_breaker(
    provider: str,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Force open circuit breaker (admin only)

    Args:
        provider: Provider name
        current_user: Admin user (from dependency)
    """
    try:
        breaker = circuit_breaker_manager.get_breaker(provider)
        breaker.force_open()

        logger.warning(
            f"Circuit breaker manually opened for {provider} "
            f"by admin: {current_user.email}"
        )

        return {
            "status": "success",
            "message": f"Circuit breaker opened for {provider}",
            "provider": provider,
            "new_state": "open"
        }

    except Exception as e:
        logger.error(f"Failed to open circuit breaker for {provider}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to open circuit breaker for: {provider}"
        )
