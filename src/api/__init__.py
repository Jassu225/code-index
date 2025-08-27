"""
API routes for the Serverless Code Index System.
"""

from .health import router as health_router
from .files import router as files_router
from .repositories import router as repositories_router

__all__ = [
    "health_router",
    "files_router", 
    "repositories_router",
]
