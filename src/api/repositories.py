#!/usr/bin/env python3
"""
Repository API endpoints.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..core.database import FirestoreDatabase, get_database
from ..models.repository import RepositoryMetadata

logger = logging.getLogger(__name__)
router = APIRouter(tags=["repositories"])


class RepositoryIndexRequest(BaseModel):
    """Request model for indexing a repository."""
    repo_url: str = Field(..., description="Repository URL (e.g., https://github.com/user/repo)")
    branch: str = Field(default="main", description="Branch to index (defaults to 'main')")


class RepositoryIndexResponse(BaseModel):
    """Response model for repository indexing."""
    success: bool = Field(..., description="Whether indexing was successful")
    message: str = Field(..., description="Response message")
    repo_url: str = Field(..., description="Repository URL")
    total_files: int = Field(..., description="Total files found")
    processed_files: int = Field(..., description="Successfully processed files")
    failed_files: int = Field(..., description="Failed to process files")
    skipped_files: int = Field(..., description="Skipped files")
    indexed_at: str = Field(..., description="When indexing was completed")


@router.get("/", response_model=List[RepositoryMetadata])
async def list_repositories(
    db: FirestoreDatabase = Depends(get_database)
) -> List[RepositoryMetadata]:
    """List all repositories."""
    try:
        repositories = await db.list_repositories()
        return repositories
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing repositories: {str(e)}"
        )


@router.get("/{repo_url:path}", response_model=RepositoryMetadata)
async def get_repository(
    repo_url: str,
    db: FirestoreDatabase = Depends(get_database)
) -> RepositoryMetadata:
    """Get a specific repository by URL."""
    try:
        repository = await db.get_repository(repo_url)
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_url} not found"
            )
        return repository
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting repository {repo_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting repository: {str(e)}"
        )


@router.post("/index", response_model=RepositoryIndexResponse)
async def index_repository(
    request: RepositoryIndexRequest,
    db: FirestoreDatabase = Depends(get_database)
) -> RepositoryIndexResponse:
    """
    Index a repository for the first time.
    
    This endpoint will:
    1. Scan the repository structure
    2. Identify relevant files (src, app, packages, root)
    3. Process each file to extract exports/imports
    4. Store file indexes and repository metadata
    """
    try:
        from src.core.repository_indexer import RepositoryIndexer
        
        # Initialize RepositoryIndexer
        repo_indexer = RepositoryIndexer(db)
        
        logger.info(f"Starting repository indexing for {request.repo_url}")
        
        # Index the repository
        results = await repo_indexer.index_repository(
            repo_url=request.repo_url,
            branch=request.branch
        )
        
        indexed_at = datetime.utcnow().isoformat() + "Z"
        
        logger.info(f"Repository indexing completed for {request.repo_url}")
        
        return RepositoryIndexResponse(
            success=True,
            message="Repository indexed successfully",
            repo_url=request.repo_url,
            total_files=results["total_files"],
            processed_files=results["processed"],
            failed_files=results["failed"],
            skipped_files=results["skipped"],
            indexed_at=indexed_at
        )
        
    except Exception as e:
        logger.error(f"Error indexing repository {request.repo_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error indexing repository: {str(e)}"
        )


@router.delete("/{repo_url:path}")
async def delete_repository(
    repo_url: str,
    db: FirestoreDatabase = Depends(get_database)
):
    """Delete a repository and all its file indexes."""
    try:
        # Delete repository metadata
        await db.delete_repository(repo_url)
        
        # Note: You might want to also delete all file indexes for this repository
        # This could be done by adding a method to delete all files for a repo
        
        return {"message": f"Repository {repo_url} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting repository {repo_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting repository: {str(e)}"
        )
