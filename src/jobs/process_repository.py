#!/usr/bin/env python3
"""
Cloud Run Job for processing large repositories.

This job is designed to run in Google Cloud Run Jobs and process entire repositories
for code indexing. It handles repositories with > 100 files by processing them
in batches and updating progress in Firestore.
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_settings
from src.core.database import FirestoreDatabase
from src.core.indexer import FileIndexer
from src.core.parser import CodeParser
from src.core.locks import DistributedLockManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RepositoryProcessor:
    """Processes entire repositories for code indexing."""
    
    def __init__(self):
        """Initialize the repository processor."""
        self.settings = get_settings()
        self.db = FirestoreDatabase()
        self.indexer = FileIndexer()
        self.parser = CodeParser()
        self.lock_manager = DistributedLockManager()
        
        # Job configuration
        self.batch_size = 50  # Process files in batches
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
    async def process_repository(
        self, 
        repo_id: str, 
        repo_url: str, 
        force_reprocess: bool = False
    ) -> bool:
        """
        Process an entire repository for code indexing.
        
        Args:
            repo_id: Repository identifier
            repo_url: Repository URL
            force_reprocess: Whether to reprocess all files
            
        Returns:
            True if processing completed successfully, False otherwise
        """
        try:
            logger.info(f"Starting repository processing: {repo_id}")
            
            # Update repository status
            await self.db.update_repository(repo_id, {
                "status": "processing",
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            })
            
            # Get repository metadata
            repo_metadata = await self.db.get_repository(repo_id)
            if not repo_metadata:
                logger.error(f"Repository not found: {repo_id}")
                return False
            
            # Get list of files to process
            files_to_process = await self._get_files_to_process(repo_id, force_reprocess)
            
            if not files_to_process:
                logger.info(f"No files to process for repository: {repo_id}")
                await self._mark_repository_complete(repo_id, repo_metadata)
                return True
            
            logger.info(f"Processing {len(files_to_process)} files for repository: {repo_id}")
            
            # Process files in batches
            total_files = len(files_to_process)
            processed_files = 0
            failed_files = 0
            
            for i in range(0, total_files, self.batch_size):
                batch = files_to_process[i:i + self.batch_size]
                batch_start = i + 1
                batch_end = min(i + self.batch_size, total_files)
                
                logger.info(f"Processing batch {batch_start}-{batch_end} of {total_files}")
                
                # Process batch
                batch_results = await self._process_file_batch(repo_id, batch)
                
                # Update progress
                processed_files += batch_results["successful"]
                failed_files += batch_results["failed"]
                
                # Update repository progress
                await self._update_repository_progress(
                    repo_id, 
                    processed_files, 
                    total_files, 
                    failed_files
                )
                
                # Small delay between batches to avoid overwhelming the system
                if i + self.batch_size < total_files:
                    await asyncio.sleep(1)
            
            # Mark repository as complete
            await self._mark_repository_complete(repo_id, repo_metadata)
            
            logger.info(f"Repository processing completed: {repo_id}")
            logger.info(f"Total files: {total_files}, Processed: {processed_files}, Failed: {failed_files}")
            
            return failed_files == 0
            
        except Exception as e:
            logger.error(f"Error processing repository {repo_id}: {e}")
            await self._mark_repository_failed(repo_id, str(e))
            return False
    
    async def _get_files_to_process(
        self, 
        repo_id: str, 
        force_reprocess: bool
    ) -> List[str]:
        """Get list of files that need processing."""
        try:
            # This would typically involve:
            # 1. Cloning the repository
            # 2. Scanning for supported file types
            # 3. Checking which files have changed (unless force_reprocess)
            
            # For now, return a mock list - in production this would be dynamic
            # based on the actual repository content
            # Only include files in allowed folders: src, app, packages, or root
            mock_files = [
                "src/main.py",
                "src/api/repositories.py",
                "src/core/database.py",
                "src/models/repository.py",
                "package.json",  # root file
                "tsconfig.json"  # root file
            ]
            
            if force_reprocess:
                return mock_files
            
            # Check which files actually need processing
            files_to_process = []
            for file_path in mock_files:
                existing_index = await self.db.get_file_index(repo_id, file_path)
                if not existing_index:
                    files_to_process.append(file_path)
            
            return files_to_process
            
        except Exception as e:
            logger.error(f"Error getting files to process: {e}")
            return []
    
    async def _process_file_batch(
        self, 
        repo_id: str, 
        file_paths: List[str]
    ) -> dict:
        """Process a batch of files."""
        successful = 0
        failed = 0
        
        for file_path in file_paths:
            try:
                # Acquire file lock
                lock_key = f"{repo_id}:{file_path}"
                lock_acquired = await self.lock_manager.acquire_lock(lock_key, timeout=30)
                
                if not lock_acquired:
                    logger.warning(f"Could not acquire lock for {file_path}")
                    failed += 1
                    continue
                
                try:
                    # Process the file
                    await self._process_single_file(repo_id, file_path)
                    successful += 1
                    
                finally:
                    # Always release the lock
                    await self.lock_manager.release_lock(lock_key)
                    
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                failed += 1
        
        return {"successful": successful, "failed": failed}
    
    async def _process_single_file(self, repo_id: str, file_path: str):
        """Process a single file for indexing."""
        try:
            # This would involve:
            # 1. Reading file content
            # 2. Parsing with CodeParser
            # 3. Indexing with FileIndexer
            # 4. Storing results in Firestore
            
            # Mock processing for now
            logger.info(f"Processing file: {file_path}")
            
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            # Create mock file index
            mock_index = {
                "repoId": repo_id,
                "filePath": file_path,
                "fileHash": f"mock_hash_{file_path}",
                "lastCommitSHA": "mock_commit_sha",
                "lastCommitTimestamp": datetime.utcnow().isoformat() + "Z",
                "exports": [],
                "imports": [],
                "updatedAt": datetime.utcnow().isoformat() + "Z",
                "language": "python",
                "parseErrors": []
            }
            
            # Store in database
            await self.db.create_or_update_file_index(repo_id, file_path, mock_index)
            
        except Exception as e:
            logger.error(f"Error processing single file {file_path}: {e}")
            raise
    
    async def _update_repository_progress(
        self, 
        repo_id: str, 
        processed: int, 
        total: int, 
        failed: int
    ):
        """Update repository processing progress."""
        try:
            progress = {
                "processedFiles": processed,
                "totalFiles": total,
                "failedFiles": failed,
                "progressPercentage": int((processed / total) * 100) if total > 0 else 0,
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            }
            
            await self.db.update_repository(repo_id, progress)
            
        except Exception as e:
            logger.error(f"Error updating repository progress: {e}")
    
    async def _mark_repository_complete(self, repo_id: str, repo_metadata):
        """Mark repository as successfully processed."""
        try:
            await self.db.update_repository(repo_id, {
                "status": "completed",
                "lastUpdated": datetime.utcnow().isoformat() + "Z",
                "lastProcessedCommit": "mock_commit_sha",
                "lastProcessedCommitTimestamp": datetime.utcnow().isoformat() + "Z"
            })
            
        except Exception as e:
            logger.error(f"Error marking repository complete: {e}")
    
    async def _mark_repository_failed(self, repo_id: str, error_message: str):
        """Mark repository as failed."""
        try:
            await self.db.update_repository(repo_id, {
                "status": "failed",
                "lastUpdated": datetime.utcnow().isoformat() + "Z",
                "errorMessage": error_message
            })
            
        except Exception as e:
            logger.error(f"Error marking repository failed: {e}")


async def main():
    """Main entry point for the Cloud Run Job."""
    parser = argparse.ArgumentParser(description="Process repository for code indexing")
    parser.add_argument("--repo-id", required=True, help="Repository ID to process")
    parser.add_argument("--repo-url", required=True, help="Repository URL")
    parser.add_argument("--force-reprocess", action="store_true", help="Force reprocessing of all files")
    parser.add_argument("--project-id", help="GCP Project ID")
    parser.add_argument("--region", help="GCP Region")
    
    args = parser.parse_args()
    
    # Set environment variables if provided
    if args.project_id:
        os.environ["GCP_PROJECT_ID"] = args.project_id
    if args.region:
        os.environ["GCP_REGION"] = args.region
    
    logger.info(f"Starting repository processing job")
    logger.info(f"Repository ID: {args.repo_id}")
    logger.info(f"Repository URL: {args.repo_url}")
    logger.info(f"Force reprocess: {args.force_reprocess}")
    
    try:
        processor = RepositoryProcessor()
        success = await processor.process_repository(
            args.repo_id, 
            args.repo_url, 
            args.force_reprocess
        )
        
        if success:
            logger.info("Repository processing completed successfully")
            sys.exit(0)
        else:
            logger.error("Repository processing failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error in repository processing job: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
