"""
Health check and monitoring endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import time

from app.utils.supabase_singleton import supabase_health_check, get_supabase_stats
from app.utils.connection_monitor import get_connection_health, get_connection_stats
from app.utils.circuit_breaker import get_circuit_breaker

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Dict with health status
    """
    try:
        # Perform Supabase health check
        supabase_health = supabase_health_check()
        
        # Get connection health
        connection_health = get_connection_health()
        
        # Determine overall health
        overall_health = "healthy"
        if not supabase_health.get("healthy", False):
            overall_health = "unhealthy"
        elif connection_health.get("status") == "degraded":
            overall_health = "degraded"
        elif connection_health.get("status") == "unhealthy":
            overall_health = "unhealthy"
        
        return {
            "status": overall_health,
            "timestamp": time.time(),
            "supabase": {
                "healthy": supabase_health.get("healthy", False),
                "response_time_ms": supabase_health.get("response_time_ms", 0)
            },
            "connection_health": connection_health.get("status", "unknown"),
            "uptime_seconds": connection_health.get("stats", {}).get("uptime_seconds", 0)
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with full diagnostics.
    
    Returns:
        Dict with comprehensive health information
    """
    try:
        # Get all health information
        supabase_health = supabase_health_check()
        supabase_stats = get_supabase_stats()
        connection_health = get_connection_health()
        connection_stats = get_connection_stats()
        circuit_breaker = get_circuit_breaker()
        circuit_status = circuit_breaker.get_status()
        
        return {
            "timestamp": time.time(),
            "overall_status": connection_health.get("status", "unknown"),
            "supabase": {
                "connection": supabase_health,
                "client_stats": supabase_stats
            },
            "performance": connection_stats,
            "circuit_breakers": circuit_status,
            "health_analysis": connection_health,
            "recommendations": connection_health.get("recommendations", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/health/supabase")
async def supabase_health() -> Dict[str, Any]:
    """
    Supabase-specific health check.
    
    Returns:
        Dict with Supabase connection health
    """
    try:
        health_result = supabase_health_check()
        stats = get_supabase_stats()
        
        return {
            "timestamp": time.time(),
            "connection": health_result,
            "client_stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase health check failed: {str(e)}")

@router.get("/health/performance")
async def performance_metrics() -> Dict[str, Any]:
    """
    Performance metrics endpoint.
    
    Returns:
        Dict with performance metrics
    """
    try:
        connection_stats = get_connection_stats()
        
        # Get operation breakdown if available
        from app.utils.connection_monitor import get_connection_monitor
        monitor = get_connection_monitor()
        operation_breakdown = monitor.get_operation_breakdown()
        
        return {
            "timestamp": time.time(),
            "overall_stats": connection_stats,
            "operation_breakdown": operation_breakdown
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance metrics failed: {str(e)}")

@router.get("/health/circuit-breakers")
async def circuit_breaker_status() -> Dict[str, Any]:
    """
    Circuit breaker status endpoint.
    
    Returns:
        Dict with circuit breaker status
    """
    try:
        circuit_breaker = get_circuit_breaker()
        status = circuit_breaker.get_status()
        
        return {
            "timestamp": time.time(),
            "circuit_breakers": status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Circuit breaker status failed: {str(e)}")

@router.post("/health/reset")
async def reset_connections() -> Dict[str, Any]:
    """
    Reset Supabase connections (emergency endpoint).
    
    Returns:
        Dict with reset status
    """
    try:
        from app.utils.supabase_singleton import reset_supabase_client
        
        # Reset the client
        reset_supabase_client()
        
        # Wait a moment for reconnection
        import asyncio
        await asyncio.sleep(1)
        
        # Test new connection
        health_result = supabase_health_check()
        
        return {
            "timestamp": time.time(),
            "reset": True,
            "new_connection_health": health_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection reset failed: {str(e)}")

# Legacy endpoint for compatibility
@router.get("/")
async def root_health() -> Dict[str, str]:
    """Root health endpoint for basic checks"""
    try:
        health = await health_check()
        return {"status": health["status"]}
    except:
        return {"status": "unhealthy"}