#!/usr/bin/env python3
"""
Commit parser for incremental repository updates.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
import git

from .indexer import FileIndexer
from ..models.repository import RepositoryMetadata

logger = logging.getLogger(__name__)


class CommitParser:
    """
    Handles incremental updates based on git commits.
    
    This class is responsible for:
    1. Analyzing git commits for changes
    2. Identifying modified/added/deleted files
    3. Processing only changed files with FileIndexer
    4. Updating repository metadata
    """
    
    def __init__(self, firestore_client):
        """Initialize commit parser."""
        self.firestore_client = firestore_client
        self.file_indexer = FileIndexer(firestore_client)
        
        # Collections
        self.repositories = firestore_client.collection('repositories')
        self.file_indexes = firestore_client.collection('file_indexes')
    
    async def process_commit(
        self,
        repo_url: str,
        repo_path: str,
        commit_sha: str,
        commit_timestamp: str,
        commit_message: str = ""
    ) -> Dict[str, any]:
        """
        Process a single commit and update file indexes.
        
        Args:
            repo_url: Repository identifier
            repo_path: Path to repository root
            commit_sha: Commit SHA
            commit_timestamp: Commit timestamp
            commit_message: Optional commit message
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing commit {commit_sha[:8]} for repository: {repo_url}")
        
        try:
            # Get repository metadata
            repo_metadata = await self._get_repository_metadata(repo_url)
            if not repo_metadata:
                raise ValueError(f"Repository {repo_url} not found")
            
            # Get commit information
            commit_info = await self._analyze_commit(repo_path, commit_sha)
            
            # Process changed files
            results = await self._process_changed_files(
                repo_url, repo_path, commit_info, commit_sha, commit_timestamp
            )
            
            # Update repository metadata
            await self._update_repository_metadata(
                repo_url, commit_sha, commit_timestamp, results
            )
            
            logger.info(f"Commit {commit_sha[:8]} processed successfully")
            
            return {
                "repo_url": repo_url,
                "commit_sha": commit_sha,
                "changed_files": len(commit_info["changed_files"]),
                "processed": results["processed"],
                "failed": results["failed"],
                "skipped": results["skipped"]
            }
            
        except Exception as e:
            logger.error(f"Error processing commit {commit_sha[:8]}: {e}")
            raise
    
    async def _analyze_commit(
        self, 
        repo_path: str, 
        commit_sha: str
    ) -> Dict[str, any]:
        """
        Analyze a git commit to get changed files.
        
        Args:
            repo_path: Path to repository root
            commit_sha: Commit SHA
            
        Returns:
            Dictionary with commit analysis
        """
        try:
            # Change to repository directory
            original_cwd = os.getcwd()
            os.chdir(repo_path)
            
            try:
                # Open git repository
                repo = git.Repo(repo_path)
                
                # Get commit object
                commit = repo.commit(commit_sha)
                
                # Get changed files
                changed_files = set()
                added_files = set()
                deleted_files = set()
                modified_files = set()
                
                # Get diff with parent commit
                if commit.parents:
                    parent = commit.parents[0]
                    diff = parent.diff(commit)
                    
                    for change in diff:
                        file_path = change.a_path or change.b_path
                        if file_path:
                            changed_files.add(file_path)
                            
                            if change.change_type == 'A':  # Added
                                added_files.add(file_path)
                            elif change.change_type == 'D':  # Deleted
                                deleted_files.add(file_path)
                            elif change.change_type == 'M':  # Modified
                                modified_files.add(file_path)
                else:
                    # Initial commit - all files are added
                    for item in commit.tree.traverse():
                        if item.type == 'blob':  # File
                            changed_files.add(item.path)
                            added_files.add(item.path)
                
                return {
                    "changed_files": list(changed_files),
                    "added_files": list(added_files),
                    "deleted_files": list(deleted_files),
                    "modified_files": list(modified_files),
                    "commit_message": commit.message.strip(),
                    "author": commit.author.name,
                    "author_email": commit.author.email
                }
                
            finally:
                # Restore original working directory
                os.chdir(original_cwd)
                
        except Exception as e:
            logger.error(f"Error analyzing commit {commit_sha}: {e}")
            raise
    
    async def _process_changed_files(
        self,
        repo_url: str,
        repo_path: str,
        commit_info: Dict[str, any],
        commit_sha: str,
        commit_timestamp: str
    ) -> Dict[str, int]:
        """
        Process files changed in the commit.
        
        Args:
            repo_url: Repository identifier
            repo_path: Path to repository root
            commit_info: Commit analysis information
            commit_sha: Commit SHA
            commit_timestamp: Commit timestamp
            
        Returns:
            Dictionary with processing results
        """
        processed = 0
        failed = 0
        skipped = 0
        
        changed_files = commit_info["changed_files"]
        
        for file_path in changed_files:
            try:
                # Check if file is in allowed folders
                if not self._is_file_in_allowed_folder(file_path):
                    logger.info(f"Skipping file {file_path} - not in allowed folder")
                    skipped += 1
                    continue
                
                # Check if file was deleted
                if file_path in commit_info["deleted_files"]:
                    # Handle file deletion (could mark as deleted in database)
                    logger.info(f"File deleted: {file_path}")
                    skipped += 1
                    continue
                
                # Process added/modified files
                full_path = Path(repo_path) / file_path
                if not full_path.exists():
                    logger.warning(f"File not found: {file_path}")
                    failed += 1
                    continue
                
                # Read file content
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
    
    def _is_file_in_allowed_folder(self, file_path: str) -> bool:
        """
        Check if file is in one of the allowed folders.
        
        Args:
            file_path: Relative path within repository
            
        Returns:
            True if file should be processed, False otherwise
        """
        # Only process files in specific folders or root
        allowed_folders = {'src', 'app', 'packages'}
        path_parts = Path(file_path).parts
        
        # Allow root files (len == 1) or files in allowed folders
        return len(path_parts) == 1 or path_parts[0] in allowed_folders
    
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
    
    async def _get_repository_metadata(self, repo_url: str) -> Optional[RepositoryMetadata]:
        """Get repository metadata from Firestore."""
        try:
            repo_ref = self.repositories.document(repo_url)
            doc = repo_ref.get()
            
            if doc.exists:
                return RepositoryMetadata(**doc.to_dict())
            return None
            
        except Exception as e:
            logger.error(f"Error getting repository metadata for {repo_url}: {e}")
            return None
    
    async def _update_repository_metadata(
        self,
        repo_url: str,
        commit_sha: str,
        commit_timestamp: str,
        results: Dict[str, int]
    ):
        """Update repository metadata after processing commit."""
        try:
            repo_ref = self.repositories.document(repo_url)
            
            # Get current repository data
            repo_doc = repo_ref.get()
            
            if repo_doc.exists:
                current_data = repo_doc.to_dict()
                processed_files = current_data.get('processedFiles', 0) + results["processed"]
                
                repo_ref.update({
                    'lastProcessedCommit': commit_sha,
                    'lastProcessedCommitTimestamp': commit_timestamp,
                    'processedFiles': processed_files,
                    'lastUpdated': datetime.utcnow().isoformat() + 'Z'
                })
            
        except Exception as e:
            logger.error(f"Error updating repository metadata for {repo_url}: {e}")
            raise
