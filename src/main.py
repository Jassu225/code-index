"""
Main FastAPI application entry point for the Serverless Code Index System.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .api.health import router as health_router
from .api.files import router as files_router
from .api.repositories import router as repositories_router
from .core.locks import FileLock
from .core.indexer import FileIndexer
from .core.config import get_settings
from .core.database import get_database
from .core.cloud_run_jobs import get_jobs_service

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Serverless Code Index System...")
    
    try:
        # Initialize configuration
        settings = get_settings()
        logger.info(f"Configuration loaded for project: {settings.gcp_project_id}")
        
        # Initialize database connection
        db = get_database()
        logger.info("Database connection initialized")
        
        # Initialize Cloud Run Jobs service
        jobs_service = get_jobs_service()
        logger.info("Cloud Run Jobs service initialized")
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Serverless Code Index System...")


# Create FastAPI application
app = FastAPI(
    title="Serverless Code Index System",
    description="A serverless backend that tracks exported/imported variables across files in git repositories",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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
        "name": "Serverless Code Index System",
        "version": "0.1.0",
        "description": "A serverless backend that tracks exported/imported variables across files in git repositories",
        "docs": "/docs",
        "health": "/health",
        "status": "operational"
    }


@app.get("/status", tags=["status"])
async def status() -> Dict[str, Any]:
    """System status endpoint."""
    try:
        # Get database stats
        db = get_database()
        db_stats = await db.get_database_stats()
        
        # Get jobs info
        jobs_service = get_jobs_service()
        jobs_info = await jobs_service.get_job_info("system-status")
        
        return {
            "status": "operational",
            "version": "0.1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": {
                "api": "operational",
                "database": "operational" if "error" not in db_stats else "degraded",
                "jobs": "operational" if "error" not in jobs_info else "degraded"
            },
            "database_stats": db_stats,
            "jobs_info": jobs_info
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            "status": "degraded",
            "version": "0.1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": {
                "api": "operational",
                "database": "degraded",
                "jobs": "degraded"
            },
            "error": str(e)
        }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
