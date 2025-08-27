"""
Repository metadata models for tracking repository-level information.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RepositoryMetadata(BaseModel):
    """Repository metadata for tracking processing status and statistics."""
    
    repoId: str = Field(..., description="Repository identifier")
    name: str = Field(..., description="Repository name")
    url: str = Field(..., description="Repository URL")
    lastProcessedCommit: str = Field(..., description="Last processed commit SHA")
    lastProcessedCommitTimestamp: str = Field(..., description="ISO 8601 UTC timestamp of last processed commit")
    totalFiles: int = Field(0, description="Total files in repository")
    processedFiles: int = Field(0, description="Number of successfully processed files")
    lastUpdated: str = Field(..., description="ISO 8601 UTC timestamp")
    status: str = Field("pending", description="Processing status")
    
    @field_validator('lastUpdated', 'lastProcessedCommitTimestamp', mode='before')
    @classmethod
    def ensure_utc_timestamp(cls, v):
        """Ensure timestamps are in ISO 8601 UTC format."""
        if isinstance(v, datetime):
            return v.isoformat() + 'Z'
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status values."""
        valid_statuses = ['pending', 'processing', 'completed', 'failed', 'paused']
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v
    
    @field_validator('totalFiles', 'processedFiles')
    @classmethod
    def validate_file_counts(cls, v):
        """Validate file count values."""
        if v < 0:
            raise ValueError("File counts cannot be negative")
        return v
    
    @property
    def processing_progress(self) -> float:
        """Calculate processing progress as a percentage."""
        if self.totalFiles == 0:
            return 0.0
        return (self.processedFiles / self.totalFiles) * 100
    
    @property
    def is_processing_complete(self) -> bool:
        """Check if processing is complete."""
        return self.status == "completed" and self.processedFiles >= self.totalFiles
    
    @property
    def has_failures(self) -> bool:
        """Check if there are processing failures."""
        return self.status == "failed" or (self.totalFiles > 0 and self.processedFiles < self.totalFiles)
