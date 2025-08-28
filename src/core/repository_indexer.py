#!/usr/bin/env python3
"""
Repository indexer for first-time repository processing.
"""

import logging
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from .indexer import FileIndexer
from .parser import CodeParser
from ..models.repository import RepositoryMetadata
from ..models.file_index import FileIndex

logger = logging.getLogger(__name__)


class RepositoryIndexer:
    """
    Handles first-time indexing of entire repositories.
    
    This class is responsible for:
    1. Scanning repository structure
    2. Identifying relevant files
    3. Processing each file with FileIndexer
    4. Storing repository metadata
    """
    
    def __init__(self, firestore_client):
        """Initialize repository indexer."""
        self.firestore_client = firestore_client
        self.file_indexer = FileIndexer(firestore_client)
        self.parser = CodeParser()
        
        # Collections
        self.repositories = firestore_client.collection('repositories')
        self.file_indexes = firestore_client.collection('file_indexes')
    
    async def index_repository(
        self,
        repo_url: str,
        branch: str = "main"
    ) -> Dict[str, any]:
        """
        Index an entire repository for the first time.
        
        Args:
            repo_url: Repository URL
            branch: Branch to index (defaults to 'main')
            
        Returns:
            Dictionary with indexing results
        """
        logger.info(f"Starting first-time indexing of repository: {repo_url}")
        
        try:
            # Clone repository to temporary directory
            temp_dir = await self._clone_repository(repo_url, branch)
            
            # Get commit information from the cloned repository
            commit_info = await self._get_commit_info(temp_dir, branch)
            commit_sha = commit_info["sha"]
            commit_timestamp = commit_info["timestamp"]
            
            logger.info(f"Latest commit: {commit_sha[:8]} at {commit_timestamp}")
            
            # Create repository metadata
            repo_metadata = RepositoryMetadata(
                repoId=repo_url,
                name=repo_url,
                url=repo_url,
                lastProcessedCommit=commit_sha,
                lastProcessedCommitTimestamp=commit_timestamp,
                totalFiles=0,
                processedFiles=0,
                lastUpdated=datetime.utcnow().isoformat() + 'Z',
                status="processing"
            )
            
            # Store repository metadata with auto-generated UID
            doc_ref = self.repositories.add(repo_metadata.model_dump())
            repo_uid = doc_ref[1].id  # Get the auto-generated UID
            logger.info(f"Created repository metadata with UID: {repo_uid}")
            
            try:
                # Get files to process
                files_to_process = self._get_repository_files(temp_dir)
                logger.info(f"Found {len(files_to_process)} files to process")
                
                # Process files
                results = await self._process_repository_files(
                    repo_url, temp_dir, files_to_process, commit_sha, commit_timestamp
                )
            finally:
                # Clean up temporary directory
                await self._cleanup_temp_directory(temp_dir)
            
            # Update repository status
            final_status = {
                "status": "completed",
                "totalFiles": len(files_to_process),
                "processedFiles": results["processed"],
                "lastUpdated": datetime.utcnow().isoformat() + 'Z'
            }
            
            # Get the document reference using the UID
            repo_ref = self.repositories.document(repo_uid)
            repo_ref.update(final_status)
            logger.info(f"Repository indexing completed: {repo_url} (UID: {repo_uid})")
            
            return {
                "repo_url": repo_url,
                "repo_uid": repo_uid,
                "total_files": len(files_to_process),
                "processed": results["processed"],
                "failed": results["failed"],
                "skipped": results["skipped"]
            }
            
        except Exception as e:
            logger.error(f"Error indexing repository {repo_url}: {e}")
            # Update repository status to failed if we have a UID
            if 'repo_uid' in locals():
                repo_ref = self.repositories.document(repo_uid)
                repo_ref.update({
                    "status": "failed",
                    "lastUpdated": datetime.utcnow().isoformat() + 'Z',
                    "errorMessage": str(e)
                })
            raise
    
    def _get_repository_files(self, repo_path: str) -> List[str]:
        """
        Get list of relevant files in repository.
        
        Args:
            repo_path: Path to repository root
            
        Returns:
            List of file paths relative to repository root
        """
        repo_path_obj = Path(repo_path)
        files = []
        
        # File extensions to process
        extensions = {'.ts', '.js', '.tsx', '.jsx', '.py', '.go', '.java', '.cs'}
        
        # Only process files in specific folders or root
        allowed_folders = {'src', 'app', 'packages'}
        
        for file_path in repo_path_obj.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                # Get relative path from repository root
                relative_path = str(file_path.relative_to(repo_path_obj))
                
                # Check if file is in one of the allowed folders or in root
                path_parts = Path(relative_path).parts
                if len(path_parts) == 1 or path_parts[0] in allowed_folders:
                    files.append(relative_path)
        
        # Sort files for consistent processing order
        files.sort()
        return files
    
    async def _process_repository_files(
        self,
        repo_url: str,
        repo_path: str,
        file_paths: List[str],
        commit_sha: str,
        commit_timestamp: str
    ) -> Dict[str, int]:
        """
        Process multiple files in a repository.
        
        Args:
            repo_url: Repository URL
            repo_path: Path to repository root
            file_paths: List of file paths to process
            commit_sha: Commit SHA
            commit_timestamp: Commit timestamp
            
        Returns:
            Dictionary with processing results
        """
        processed = 0
        failed = 0
        skipped = 0
        
        for file_path in file_paths:
            try:
                logger.info(f"Processing file: {file_path}")
                
                # Read file content
                full_path = Path(repo_path) / file_path
                if not full_path.exists():
                    logger.warning(f"File not found: {file_path}")
                    failed += 1
                    continue
                
                file_content = full_path.read_text(encoding='utf-8', errors='ignore')
                
                # Determine language from file extension
                language = self._get_language_from_path(file_path)
                
                # Process the file using FileIndexer
                success = await self.file_indexer.process_file(
                    repo_url=repo_url,
                    file_path=file_path,
                    commit_sha=commit_sha,
                    file_timestamp=commit_timestamp,
                    file_content=file_content,
                    language=language
                    # exports and imports will be parsed automatically by FileIndexer
                )
                
                if success:
                    processed += 1
                    logger.info(f"Successfully processed: {file_path}")
                else:
                    failed += 1
                    logger.warning(f"Failed to process: {file_path}")
                    
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                failed += 1
        
        return {
            "processed": processed,
            "failed": failed,
            "skipped": skipped
        }
    
    def _get_language_from_path(self, file_path: str) -> str:
        """Determine language from file path."""
        if file_path.endswith(".ts"):
            return "typescript"
        elif file_path.endswith(".js"):
            return "javascript"
        elif file_path.endswith(".tsx"):
            return "typescript"
        elif file_path.endswith(".jsx"):
            return "javascript"
        elif file_path.endswith(".py"):
            return "python"
        elif file_path.endswith(".go"):
            return "go"
        elif file_path.endswith(".java"):
            return "java"
        elif file_path.endswith(".cs"):
            return "csharp"
        else:
            return "text"
    
    async def _clone_repository(self, repo_url: str, branch: str = "main") -> str:
        """
        Clone repository to temporary directory.
        
        Args:
            repo_url: Repository URL to clone
            branch: Branch to clone (defaults to 'main')
            
        Returns:
            Path to temporary directory containing cloned repository
        """
        import tempfile
        import subprocess
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="repo_index_")
        logger.info(f"Created temporary directory: {temp_dir}")
        
        try:
            # Clone repository with specific branch
            logger.info(f"Cloning repository: {repo_url} (branch: {branch})")
            result = subprocess.run(
                ["git", "clone", "--branch", branch, "--single-branch", repo_url, temp_dir],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Repository cloned successfully to: {temp_dir}")
            return temp_dir
            
        except subprocess.CalledProcessError as e:
            # Clean up temp directory if cloning failed
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.error(f"Failed to clone repository: {e.stderr}")
            raise RuntimeError(f"Failed to clone repository: {e.stderr}")
    
    async def _cleanup_temp_directory(self, temp_dir: str):
        """
        Clean up temporary directory.
        
        Args:
            temp_dir: Path to temporary directory to remove
        """
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")
    
    async def _get_commit_info(self, repo_path: str, branch: str) -> Dict[str, str]:
        """
        Get commit information from cloned repository.
        
        Args:
            repo_path: Path to cloned repository
            branch: Branch name
            
        Returns:
            Dictionary with commit SHA, timestamp, and repository name
        """
        import subprocess
        import os
        
        try:
            # Change to repository directory
            original_cwd = os.getcwd()
            os.chdir(repo_path)
            
            try:
                # Get latest commit SHA
                commit_result = subprocess.run(
                    ["git", "log", "-1", "--format=%H"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                commit_sha = commit_result.stdout.strip()
                
                # Get commit timestamp
                timestamp_result = subprocess.run(
                    ["git", "log", "-1", "--format=%aI"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                commit_timestamp = timestamp_result.stdout.strip()
                
                return {
                    "sha": commit_sha,
                    "timestamp": commit_timestamp
                }
                
            finally:
                # Restore original working directory
                os.chdir(original_cwd)
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get commit info: {e.stderr}")
            raise RuntimeError(f"Failed to get commit info: {e.stderr}")
        except Exception as e:
            logger.error(f"Error getting commit info: {e}")
            raise
