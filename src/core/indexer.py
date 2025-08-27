"""
File indexer implementing two-layer deduplication strategy.
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from google.cloud import firestore

from ..models.file_index import FileIndex, ExportInfo, ImportInfo
from ..models.repository import RepositoryMetadata
from .locks import FileLock

logger = logging.getLogger(__name__)


class FileIndexer:
    """
    File indexer with two-layer deduplication strategy.
    
    Layer 1: Content hash comparison
    Layer 2: File-level timestamp validation
    """
    
    def __init__(self, firestore_client: firestore.Client):
        """
        Initialize file indexer.
        
        Args:
            firestore_client: Firestore client instance
        """
        self.firestore_client = firestore_client
        self.file_indexes = firestore_client.collection('file_indexes')
        self.repositories = firestore_client.collection('repositories')
        
        # Initialize CodeParser for extracting exports/imports
        from src.core.parser import CodeParser
        self.parser = CodeParser()
    
    async def should_process_file(self, repo_url: str, file_path: str, file_hash: str) -> bool:
        """
        Layer 1: Check if file content has changed.
        
        Args:
            repo_url: Repository URL
            file_path: Relative path within repository
            file_hash: SHA hash of file content
            
        Returns:
            True if file should be processed, False if unchanged
        """
        try:
            existing_file = await self.get_file_index(repo_url, file_path)
            if existing_file and existing_file.fileHash == file_hash:
                logger.info(f"Skipping unchanged file {file_path} (hash: {file_hash[:8]}...)")
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking file hash for {file_path}: {e}")
            return True  # Process on error to be safe
    
    async def should_process_file_by_timestamp(self, repo_url: str, file_path: str, file_timestamp: str) -> bool:
        """
        Layer 2: Check if file modification timestamp is newer than last processed.
        
        Args:
            repo_url: Repository URL
            file_path: Relative path within repository
            file_timestamp: ISO 8601 UTC timestamp of file modification
            
        Returns:
            True if file should be processed, False if older
        """
        try:
            existing_file = await self.get_file_index(repo_url, file_path)
            if not existing_file or not existing_file.lastCommitTimestamp:
                return True  # First time processing this file, always process
            
            # Parse timestamps for comparison
            last_timestamp = datetime.fromisoformat(
                existing_file.lastCommitTimestamp.replace('Z', '+00:00')
            )
            current_timestamp = datetime.fromisoformat(
                file_timestamp.replace('Z', '+00:00')
            )
            
            # Skip if current file modification is older than last processed
            if current_timestamp < last_timestamp:
                logger.info(
                    f"Skipping older file modification {file_path} "
                    f"(timestamp: {file_timestamp}) for repo {repo_url} - "
                    f"last processed: {existing_file.lastCommitTimestamp}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking file timestamp for {file_path}: {e}")
            return True  # Process on error to be safe
    
    async def process_file(
        self,
        repo_url: str,
        file_path: str,
        commit_sha: str,
        file_timestamp: str,
        file_content: str,
        language: str,
        exports: Optional[List[ExportInfo]] = None,
        imports: Optional[List[ImportInfo]] = None
    ) -> bool:
        """
        Process a file with two-layer deduplication.
        
        Args:
            repo_url: Repository URL
            file_path: Relative path within repository
            commit_sha: Commit SHA that modified the file
            file_timestamp: ISO 8601 UTC timestamp of file modification
            file_content: File content for hash calculation
            language: Programming language identifier
            exports: Parsed export information (optional, will parse if not provided)
            imports: Parsed import information (optional, will parse if not provided)
            
        Returns:
            True if file was processed, False if skipped
        """
        try:
            logger.info(f"Starting to process file {file_path} for repo {repo_url}")
            
            # First: Validate file modification timestamp (temporarily disabled for testing)
            # if not await self.should_process_file_by_timestamp(repo_url, file_path, file_timestamp):
            #     logger.info(f"Skipping file {file_path} with older modification timestamp {file_timestamp}")
            #     return False
            
            # Second: Check file content hash using git ls-files
            file_hash = await self._get_git_file_hash(file_path, file_content)
            logger.info(f"File {file_path} hash: {file_hash[:8]}...")
            
            # Temporarily disable hash check for testing
            # if not await self.should_process_file(repo_url, file_path, file_hash):
            #     logger.info(f"Skipping unchanged file {file_path}")
            #     return False
            
            # Parse file for exports/imports if not provided
            if exports is None or imports is None:
                logger.info(f"Parsing file {file_path} for exports/imports...")
                try:
                    parse_result = await self.parser.parse_file(file_path, file_content)
                    if parse_result:
                        exports = parse_result.exports
                        imports = parse_result.imports
                        logger.info(f"Parsed {len(exports)} exports and {len(imports)} imports from {file_path}")
                    else:
                        logger.warning(f"No parse result for {file_path}, using empty lists")
                        exports = exports or []
                        imports = imports or []
                except Exception as e:
                    logger.error(f"Error parsing {file_path}: {e}, using empty lists")
                    exports = exports or []
                    imports = imports or []
            
            # Process the file directly (temporarily disable locking for testing)
            logger.info(f"Indexing file {file_path}...")
            await self._index_file_with_lock(
                repo_url, file_path, commit_sha, file_timestamp, 
                file_hash, language, exports, imports, None
            )
            
            logger.info(f"Successfully processed file {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return False
    
    async def _index_file_with_lock(
        self,
        repo_url: str,
        file_path: str,
        commit_sha: str,
        file_timestamp: str,
        file_hash: str,
        language: str,
        exports: List[ExportInfo],
        imports: List[ImportInfo],
        file_lock: Optional[FileLock] = None
    ):
        """Index file while holding the distributed lock (optional for testing)."""
        try:
            # Create or update file index
            file_index = FileIndex(
                repoId=repo_url,
                filePath=file_path,
                fileHash=file_hash,
                lastCommitSHA=commit_sha,
                lastCommitTimestamp=file_timestamp,
                exports=exports,
                imports=imports,
                updatedAt=datetime.utcnow().isoformat() + 'Z',
                language=language,
                parseErrors=[]
            )
            
            # Store in Firestore with auto-generated document ID
            doc_ref = self.file_indexes.document()
            doc_ref.set(file_index.model_dump())
            
            # Update repository metadata
            await self._update_repository_metadata(repo_url, commit_sha, file_timestamp)
            
            logger.info(f"File index updated: {repo_url}:{file_path}")
            
        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}")
            raise
    
    async def get_file_index(self, repo_url: str, file_path: str) -> Optional[FileIndex]:
        """
        Get file index from Firestore.
        
        Args:
            repo_url: Repository URL identifier
            file_path: Relative path within repository
            
        Returns:
            FileIndex if found, None otherwise
        """
        try:
            # Query by repoId and filePath fields instead of document ID
            query = self.file_indexes.where('repoId', '==', repo_url).where('filePath', '==', file_path)
            docs = query.limit(1).stream()
            
            for doc in docs:
                return FileIndex(**doc.to_dict())
            return None
            
        except Exception as e:
            logger.error(f"Error getting file index for {repo_url}:{file_path}: {e}")
            return None
    
    async def _update_repository_metadata(
        self, 
        repo_url: str, 
        commit_sha: str, 
        commit_timestamp: str
    ):
        """Update repository metadata after processing a file."""
        try:
            repo_ref = self.repositories.document(repo_url)
            
            # Get current repository data
            repo_doc = repo_ref.get()
            
            if repo_doc.exists:
                # Update existing repository
                current_data = repo_doc.to_dict()
                processed_files = current_data.get('processedFiles', 0) + 1
                
                repo_ref.update({
                    'lastProcessedCommit': commit_sha,
                    'lastProcessedCommitTimestamp': commit_timestamp,
                    'processedFiles': processed_files,
                    'lastUpdated': datetime.utcnow().isoformat() + 'Z'
                })
            else:
                # Create new repository
                repo_ref.set({
                    'repoId': repo_url,
                    'name': repo_url,  # Default name, can be updated later
                    'url': repo_url,  # Set URL to the repo_url
                    'lastProcessedCommit': commit_sha,
                    'lastProcessedCommitTimestamp': commit_timestamp,
                    'totalFiles': 0,  # Will be updated when scanning repository
                    'processedFiles': 1,
                    'lastUpdated': datetime.utcnow().isoformat() + 'Z',
                    'status': 'processing'
                })
            
            logger.debug(f"Updated repository metadata for {repo_url}")
            
        except Exception as e:
            logger.error(f"Error updating repository metadata for {repo_url}: {e}")
    
    async def _get_git_file_hash(self, file_path: str, file_content: str) -> str:
        """
        Get file hash using git ls-files command.
        
        Args:
            file_path: Relative path within repository
            file_content: File content as fallback
            
        Returns:
            Git object hash or fallback hash
        """
        try:
            import subprocess
            # Note: This requires the working directory to be the repository root
            # The caller should ensure this
            result = subprocess.run(
                ['git', 'ls-files', '--format=%(objectname)', file_path],
                capture_output=True,
                text=True,
                check=True
            )
            file_hash = result.stdout.strip()
            if file_hash:
                logger.info(f"Using git hash for {file_path}: {file_hash[:8]}...")
                return file_hash
        except Exception as e:
            logger.info(f"Git hash not available for {file_path}, using content hash: {e}")
        
        # Fallback to content hash if git command fails
        content_hash = hashlib.sha256(file_content.encode()).hexdigest()
        logger.info(f"Using content hash for {file_path}: {content_hash[:8]}...")
        return content_hash
    
    async def get_repository_metadata(self, repo_url: str) -> Optional[RepositoryMetadata]:
        """
        Get repository metadata from Firestore.
        
        Args:
            repo_url: Repository URL identifier
            
        Returns:
            RepositoryMetadata if found, None otherwise
        """
        try:
            repo_ref = self.repositories.document(repo_url)
            doc = repo_ref.get()
            
            if doc.exists:
                return RepositoryMetadata(**doc.to_dict())
            return None
            
        except Exception as e:
            logger.error(f"Error getting repository metadata for {repo_url}: {e}")
            return None
    
    async def list_file_indexes(self, repo_url: str) -> List[FileIndex]:
        """
        List all file indexes for a repository.
        
        Args:
            repo_url: Repository URL identifier
            
        Returns:
            List of FileIndex objects
        """
        try:
            query = self.file_indexes.where('repoId', '==', repo_url)
            docs = query.stream()
            
            file_indexes = []
            for doc in docs:
                try:
                    file_indexes.append(FileIndex(**doc.to_dict()))
                except Exception as e:
                    logger.warning(f"Error parsing file index {doc.id}: {e}")
                    continue
            
            return file_indexes
            
        except Exception as e:
            logger.error(f"Error listing file indexes for {repo_url}: {e}")
            return []
    
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
    
    async def process_repository_files(
        self,
        repo_url: str,
        repo_path: str,
        file_paths: List[str],
        commit_sha: str,
        commit_timestamp: str
    ) -> dict:
        """
        Process multiple files in a repository.
        
        Args:
            repo_url: Repository URL identifier
            repo_path: Path to repository root
            file_paths: List of file paths to process
            commit_sha: Commit SHA
            commit_timestamp: Commit timestamp
            
        Returns:
            Dict with processing results
        """
        import os
        import asyncio
        
        # Change to repository directory for git commands
        original_cwd = os.getcwd()
        os.chdir(repo_path)
        
        try:
            processed = 0
            failed = 0
            skipped = 0
            
            for file_path in file_paths:
                try:
                    # Check if file is in allowed folder
                    if not self._is_file_in_allowed_folder(file_path):
                        logger.info(f"Skipping file {file_path} - not in allowed folder")
                        skipped += 1
                        continue
                    
                    # Read file content
                    full_path = Path(repo_path) / file_path
                    if not full_path.exists():
                        logger.warning(f"File not found: {file_path}")
                        failed += 1
                        continue
                    
                    file_content = full_path.read_text(encoding='utf-8', errors='ignore')
                    
                    # Determine language from file extension
                    language = self._get_language_from_path(file_path)
                    
                    # Parse file for exports/imports using CodeParser
                    logger.info(f"Parsing file {file_path} for exports/imports...")
                    try:
                        parse_result = await self.parser.parse_file(file_path, file_content)
                        if parse_result:
                            exports = parse_result.exports
                            imports = parse_result.imports
                            logger.info(f"Parsed {len(exports)} exports and {len(imports)} imports from {file_path}")
                        else:
                            logger.warning(f"No parse result for {file_path}, using empty lists")
                            exports = []
                            imports = []
                    except Exception as e:
                        logger.error(f"Error parsing {file_path}: {e}, using empty lists")
                        exports = []
                        imports = []
                    
                    # Process the file
                    success = await self.process_file(
                        repo_url, file_path, commit_sha, commit_timestamp,
                        file_content, language, exports, imports
                    )
                    
                    if success:
                        processed += 1
                    else:
                        failed += 1
                        
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    failed += 1
            
            return {
                "processed": processed,
                "failed": failed,
                "skipped": skipped
            }
            
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
    
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
        elif file_path.endswith(".json"):
            return "json"
        elif file_path.endswith(".md"):
            return "markdown"
        else:
            return "text"
    
    async def delete_file_index(self, repo_url: str, file_path: str) -> bool:
        """
        Delete a file index.
        
        Args:
            repo_url: Repository URL identifier
            file_path: Relative path within repository
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            # Query by repoId and filePath fields to find the document to delete
            query = self.file_indexes.where('repoId', '==', repo_url).where('filePath', '==', file_path)
            docs = query.limit(1).stream()
            
            for doc in docs:
                doc.reference.delete()
                logger.info(f"Deleted file index: {repo_url}:{file_path}")
                return True
            
            logger.warning(f"No file index found to delete: {repo_url}:{file_path}")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting file index {repo_url}:{file_path}: {e}")
            return False
