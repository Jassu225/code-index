"""
Files API endpoints for file processing and indexing.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..models.file_index import FileIndex, ExportInfo, ImportInfo
from ..core.indexer import FileIndexer
from ..core.database import get_database, FirestoreDatabase

router = APIRouter()


class ProcessFileRequest(BaseModel):
    """Request model for processing a file."""
    repo_url: str
    file_path: str
    commit_sha: str
    file_timestamp: str
    file_content: str
    language: str


class ProcessFileResponse(BaseModel):
    """Response model for file processing."""
    success: bool
    message: str
    file_path: str
    processed_at: str


class FileIndexResponse(BaseModel):
    """Response model for file index information."""
    file_path: str
    file_hash: str
    last_commit_sha: str
    last_commit_timestamp: str
    language: str
    export_count: int
    import_count: int
    updated_at: str


@router.post("/process", response_model=ProcessFileResponse)
async def process_file(
    request: ProcessFileRequest,
    db: FirestoreDatabase = Depends(get_database)
) -> ProcessFileResponse:
    """
    Process a file for indexing using FileIndexer.
    
    This endpoint implements the two-layer deduplication strategy:
    1. File-level timestamp validation
    2. Content hash comparison
    """
    try:
        # Initialize FileIndexer with the database client
        from google.cloud import firestore
        from src.core.indexer import FileIndexer
        
        # Get Firestore client from the database
        firestore_client = firestore.Client(
            project=db.settings.gcp_project_id,
            database=db.settings.firestore_database_id or "(default)"
        )
        
        indexer = FileIndexer(firestore_client)
        
        # Process the file using FileIndexer
        # The FileIndexer will automatically parse the file_content to extract exports and imports
        success = await indexer.process_file(
            repo_url=request.repo_url,
            file_path=request.file_path,
            commit_sha=request.commit_sha,
            file_timestamp=request.file_timestamp,
            file_content=request.file_content,
            language=request.language
            # exports and imports will be parsed automatically by FileIndexer
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="File was not processed (may have been skipped due to deduplication)"
            )
        
        processed_at = datetime.utcnow().isoformat() + "Z"
        
        return ProcessFileResponse(
            success=True,
            message="File processed successfully",
            file_path=request.file_path,
            processed_at=processed_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


@router.get("/{repo_url:path}/{file_path:path}", response_model=FileIndexResponse)
async def get_file_index(
    repo_url: str, 
    file_path: str,
    db: FirestoreDatabase = Depends(get_database)
) -> FileIndexResponse:
    """
    Get file index information.
    
    Args:
        repo_url: Repository URL
        file_path: Relative path within repository (can include slashes)
        db: Firestore database instance
    """
    try:
        # Get file index from Firestore
        file_index = await db.get_file_index(repo_url, file_path)
        if not file_index:
            raise HTTPException(
                status_code=404,
                detail=f"File index not found: {repo_url}:{file_path}"
            )
        
        return FileIndexResponse(
            file_path=file_index.filePath,
            file_hash=file_index.fileHash,
            last_commit_sha=file_index.lastCommitSHA,
            last_commit_timestamp=file_index.lastCommitTimestamp,
            language=file_index.language,
            export_count=len(file_index.exports),
            import_count=len(file_index.imports),
            updated_at=file_index.updatedAt
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving file index: {str(e)}"
        )


@router.get("/{repo_url:path}", response_model=List[FileIndexResponse])
async def list_repository_files(
    repo_url: str,
    db: FirestoreDatabase = Depends(get_database)
) -> List[FileIndexResponse]:
    """
    List all indexed files for a repository.
    
    Args:
        repo_url: Repository URL
        db: Firestore database instance
    """
    try:
        # Get file indexes from Firestore
        file_indexes = await db.list_file_indexes(repo_url)
        
        # Convert to response format
        responses = []
        for file_index in file_indexes:
            response = FileIndexResponse(
                file_path=file_index.filePath,
                file_hash=file_index.fileHash,
                last_commit_sha=file_index.lastCommitSHA,
                last_commit_timestamp=file_index.lastCommitTimestamp,
                language=file_index.language,
                export_count=len(file_index.exports),
                import_count=len(file_index.imports),
                updated_at=file_index.updatedAt
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing repository files: {str(e)}"
        )


@router.delete("/{repo_url:path}/{file_path:path}")
async def delete_file_index(
    repo_url: str, 
    file_path: str,
    db: FirestoreDatabase = Depends(get_database)
) -> dict:
    """
    Delete a file index.
    
    Args:
        repo_url: Repository URL
        file_path: Relative path within repository
        db: Firestore database instance
    """
    try:
        # Check if file index exists
        existing_index = await db.get_file_index(repo_url, file_path)
        if not existing_index:
            raise HTTPException(
                status_code=404,
                detail=f"File index not found: {repo_url}:{file_path}"
            )
        
        # Delete from Firestore
        success = await db.delete_file_index(repo_url, file_path)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete file index from database"
            )
        
        return {
            "success": True,
            "message": f"File index deleted: {repo_url}:{file_path}",
            "deleted_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting file index: {str(e)}"
        )
