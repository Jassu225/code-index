"""
Live integration test that clones and indexes the actual ts-array repository.
"""

import asyncio
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, List

import pytest
import git

from src.core.config import get_settings
from src.core.database import FirestoreDatabase
from src.core.indexer import FileIndexer
from src.core.parser import CodeParser
from src.models.repository import RepositoryMetadata
from src.models.file_index import FileIndex


class TestLiveRepositoryIndexing:
    """Test indexing the actual ts-array repository by cloning it."""
    
    def __init__(self):
        self.emulator_process: Optional[subprocess.Popen] = None
        self.emulator_port = 8081  # Different port to avoid conflicts
        self.project_id = "test-project"
        self.temp_dir: Optional[Path] = None
        self.repo_path: Optional[Path] = None
        
    def setup_method(self):
        """Set up Firestore emulator and clone repository."""
        self.start_firestore_emulator()
        self.clone_repository()
        
    def teardown_method(self):
        """Clean up Firestore emulator and cloned repository."""
        self.stop_firestore_emulator()
        self.cleanup_repository()
    
    def start_firestore_emulator(self):
        """Start the Firestore emulator."""
        try:
            # Set environment variables for emulator
            os.environ["FIRESTORE_EMULATOR_HOST"] = f"localhost:{self.emulator_port}"
            os.environ["GCP_PROJECT_ID"] = self.project_id
            
            # Start emulator
            cmd = [
                "gcloud", "emulators", "firestore", "start",
                "--project", self.project_id,
                "--host-port", f"localhost:{self.emulator_port}"
            ]
            
            self.emulator_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for emulator to start
            time.sleep(5)
            print(f"Firestore emulator started on port {self.emulator_port}")
            
        except Exception as e:
            print(f"Failed to start Firestore emulator: {e}")
            raise
    
    def stop_firestore_emulator(self):
        """Stop the Firestore emulator."""
        if self.emulator_process:
            try:
                self.emulator_process.terminate()
                self.emulator_process.wait(timeout=10)
                print("Firestore emulator stopped")
            except subprocess.TimeoutExpired:
                self.emulator_process.kill()
                print("Firestore emulator forcefully stopped")
    
    def clone_repository(self):
        """Clone the ts-array repository."""
        try:
            # Create temporary directory
            self.temp_dir = Path(tempfile.mkdtemp())
            self.repo_path = self.temp_dir / "ts-array"
            
            print(f"Cloning repository to: {self.repo_path}")
            
            # Clone the repository
            repo = git.Repo.clone_from(
                "https://github.com/Jassu225/ts-array.git",
                self.repo_path,
                depth=1  # Shallow clone for speed
            )
            
            print(f"Repository cloned successfully. Latest commit: {repo.head.commit.hexsha[:8]}")
            
        except Exception as e:
            print(f"Failed to clone repository: {e}")
            raise
    
    def cleanup_repository(self):
        """Clean up the cloned repository."""
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
            print("Repository cleanup completed")
    
    def get_repository_files(self) -> List[Path]:
        """Get all relevant files from the cloned repository."""
        if not self.repo_path:
            return []
        
        # File extensions to process
        extensions = {'.ts', '.js', '.tsx', '.jsx', '.json', '.md'}
        
        files = []
        for file_path in self.repo_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in extensions:
                # Get relative path from repository root
                relative_path = file_path.relative_to(self.repo_path)
                files.append(relative_path)
        
        # Sort files for consistent processing order
        files.sort()
        return files
    
    @pytest.mark.asyncio
    async def test_live_index_ts_array_repository(self):
        """Test indexing the actual cloned ts-array repository."""
        # Repository details
        repo_id = "ts-array-live"
        repo_url = "https://github.com/Jassu225/ts-array"
        
        print(f"Starting live indexing of repository: {repo_id}")
        
        # Initialize services
        db = FirestoreDatabase()
        indexer = FileIndexer()
        parser = CodeParser()
        
        # Create repository metadata
        repo_metadata = RepositoryMetadata(
            repoId=repo_id,
            name="ts-array",
            url=repo_url,
            lastProcessedCommit="",
            lastProcessedCommitTimestamp="2025-01-26T00:00:00Z",
            totalFiles=0,
            processedFiles=0,
            lastUpdated="2025-01-26T00:00:00Z",
            status="pending"
        )
        
        # Store repository in database
        await db.create_repository(repo_metadata)
        print(f"Repository {repo_id} created in database")
        
        # Get actual files from repository
        repository_files = self.get_repository_files()
        print(f"Found {len(repository_files)} files in repository")
        
        # Process each file
        processed_files = 0
        failed_files = 0
        
        for file_path in repository_files:
            try:
                # Read actual file content
                full_path = self.repo_path / file_path
                file_content = full_path.read_text(encoding='utf-8', errors='ignore')
                
                print(f"Processing: {file_path} ({len(file_content)} chars)")
                
                # Parse the file
                parse_result = await parser.parse_file(str(file_path), file_content)
                
                if parse_result:
                    # Create file index
                    file_index = FileIndex(
                        repoId=repo_id,
                        filePath=str(file_path),
                        fileHash=f"live_hash_{file_path}",
                        lastCommitSHA="live_commit_sha",
                        lastCommitTimestamp="2025-01-26T00:00:00Z",
                        exports=parse_result.get("exports", []),
                        imports=parse_result.get("imports", []),
                        updatedAt="2025-01-26T00:00:00Z",
                        language=self._get_language_from_path(str(file_path)),
                        parseErrors=parse_result.get("errors", [])
                    )
                    
                    # Store in database
                    await db.create_or_update_file_index(repo_id, str(file_path), file_index)
                    processed_files += 1
                    print(f"✓ Processed: {file_path} ({len(parse_result.get('exports', []))} exports)")
                    
                else:
                    print(f"⚠ No parse result for: {file_path}")
                    failed_files += 1
                    
            except Exception as e:
                print(f"✗ Error processing {file_path}: {e}")
                failed_files += 1
        
        # Update repository status
        await db.update_repository(repo_id, {
            "status": "completed",
            "totalFiles": len(repository_files),
            "processedFiles": processed_files,
            "lastUpdated": "2025-01-26T00:00:00Z"
        })
        
        print(f"\nLive repository indexing completed!")
        print(f"Total files found: {len(repository_files)}")
        print(f"Successfully processed: {processed_files}")
        print(f"Failed to process: {failed_files}")
        
        # Verify results
        final_repo = await db.get_repository(repo_id)
        assert final_repo is not None
        assert final_repo.status == "completed"
        assert final_repo.processedFiles == processed_files
        
        # Get all file indices
        file_indices = await db.get_repository_files(repo_id)
        assert len(file_indices) == processed_files
        
        # Show some statistics
        self._print_indexing_statistics(file_indices)
        
        print(f"✓ Repository {repo_id} successfully indexed with {processed_files} files")
    
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
    
    def _print_indexing_statistics(self, file_indices: List[FileIndex]):
        """Print statistics about the indexed files."""
        print("\n📊 Indexing Statistics:")
        print("=" * 50)
        
        # Language distribution
        languages = {}
        total_exports = 0
        total_imports = 0
        
        for file_index in file_indices:
            lang = file_index.language
            languages[lang] = languages.get(lang, 0) + 1
            
            total_exports += len(file_index.exports)
            total_imports += len(file_index.imports)
        
        print(f"Languages found:")
        for lang, count in sorted(languages.items()):
            print(f"  {lang}: {count} files")
        
        print(f"\nTotal exports: {total_exports}")
        print(f"Total imports: {total_imports}")
        
        # Show some example exports
        if file_indices:
            print(f"\nExample exports from first file:")
            first_file = file_indices[0]
            if first_file.exports:
                for export in first_file.exports[:3]:  # Show first 3 exports
                    print(f"  - {export.name} ({export.type})")
            else:
                print("  No exports found")


if __name__ == "__main__":
    # Run the live test
    test = TestLiveRepositoryIndexing()
    test.setup_method()
    
    try:
        asyncio.run(test.test_live_index_ts_array_repository())
    finally:
        test.teardown_method()
