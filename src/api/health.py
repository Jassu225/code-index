"""
Health check API endpoints.
"""

import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.locks import FileLock
from ..core.indexer import FileIndexer

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    uptime: float
    version: str
    checks: Dict[str, Any]


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: str
    timestamp: str
    uptime: float
    version: str
    checks: Dict[str, Any]
    dependencies: Dict[str, Any]


# Track application start time
start_time = time.time()


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    uptime = time.time() - start_time
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        uptime=uptime,
        version="0.1.0",
        checks={
            "api": "healthy",
            "timestamp": "valid"
        }
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Detailed health check with dependency status."""
    uptime = time.time() - start_time
    
    # Basic checks
    checks = {
        "api": "healthy",
        "timestamp": "valid",
        "uptime": "valid"
    }
    
    # Dependency checks (these would be more comprehensive in production)
    dependencies = {
        "firestore": "unknown",  # Would check actual connectivity
        "cloud_tasks": "unknown",  # Would check actual connectivity
        "file_locks": "unknown"   # Would check actual connectivity
    }
    
    # Overall status
    overall_status = "healthy"
    
    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        uptime=uptime,
        version="0.1.0",
        checks=checks,
        dependencies=dependencies
    )


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check for Kubernetes/Cloud Run."""
    uptime = time.time() - start_time
    
    # In production, this would check:
    # - Database connectivity
    # - External service dependencies
    # - Required configuration
    # - Resource availability
    
    is_ready = uptime > 5  # Simple check: app has been running for at least 5 seconds
    
    if is_ready:
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime": uptime
        }
    else:
        raise HTTPException(
            status_code=503,
            detail="Service not ready yet"
        )


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check for Kubernetes/Cloud Run."""
    uptime = time.time() - start_time
    
    # In production, this would check:
    # - Application responsiveness
    # - Memory usage
    # - CPU usage
    # - Deadlock detection
    
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime": uptime
    }


@router.get("/metrics")
async def metrics() -> Dict[str, Any]:
    """Basic metrics endpoint (Prometheus format would be more comprehensive)."""
    uptime = time.time() - start_time
    
    return {
        "uptime_seconds": uptime,
        "version": "0.1.0",
        "status": "operational"
    }
