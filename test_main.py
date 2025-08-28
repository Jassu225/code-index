#!/usr/bin/env python3
"""
Test main.py without the lifespan to debug route registration issues.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.health import router as health_router
from src.api.files import router as files_router
from src.api.repositories import router as repositories_router
from src.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class HealthStatus(BaseModel):
    """Health status response model."""
    status: str
    version: str
    timestamp: str
    uptime: float

# Create FastAPI application WITHOUT lifespan
app = FastAPI(
    title="Serverless Code Index System",
    description="A serverless backend that tracks exported/imported variables across files in git repositories",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
    # No lifespan parameter
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(files_router, prefix="/files", tags=["files"])
app.include_router(repositories_router, prefix="/repositories", tags=["repositories"])

@app.get("/", tags=["root"])
async def root() -> Dict[str, Any]:
    """Root endpoint with system information."""
    return {
        "name": "Serverless Code Index System - TEST VERSION",
        "version": "0.1.0",
        "description": "A serverless backend that tracks exported/imported variables across files in git repositories",
        "docs": "/docs",
        "health": "/health",
        "status": "operational"
    }

@app.get("/status", tags=["status"])
async def status() -> Dict[str, Any]:
    """System status endpoint."""
    return {
        "status": "operational",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "api": "operational",
            "note": "test version without GCP dependencies"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083, log_level="info")