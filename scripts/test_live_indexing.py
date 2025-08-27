#!/usr/bin/env python3
"""
Standalone script to test live repository indexing with Firestore emulator.
"""

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List

import git

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.config import get_settings
from src.core.database import FirestoreDatabase
from src.core.indexer import FileIndexer
from src.models.repository import RepositoryMetadata


class LiveRepositoryIndexer:
    """Live repository indexer using Firestore emulator."""
    
    def __init__(self):
        self.emulator_port = 8080  # Use existing Firebase emulator port
        self.project_id = "code-index-dev"  # Use default Firebase emulator project
        self.temp_dir: Optional[Path] = None
        self.repo_path: Optional[Path] = None
        
    async def run(self):
        """Run the live indexing test."""
        try:
            print("🚀 Starting Live Repository Indexing Test")
            print("=" * 60)
            
            # Setup
            await self.setup()
            
            # Run the indexing
            await self.index_repository()
            
            # Show results
            await self.show_results()
            
        finally:
            # Cleanup
            await self.cleanup()
    
    async def setup(self):
        """Set up Firestore emulator and clone repository."""
        print("📋 Setting up environment...")
        
        # Start Firestore emulator
        self.start_firestore_emulator()
        
        # Clone repository
        self.clone_repository()
        
        print("✅ Setup completed")
    
    def start_firestore_emulator(self):
        """Connect to existing Firebase emulator."""
        try:
            # Set environment variables for existing emulator
            os.environ["FIRESTORE_EMULATOR_HOST"] = f"localhost:{self.emulator_port}"
            os.environ["GCP_PROJECT_ID"] = self.project_id
            os.environ["GOOGLE_CLOUD_PROJECT"] = self.project_id
            os.environ["FIRESTORE_COLLECTION_PREFIX"] = ""  # Override config to use no prefix
            os.environ["FIRESTORE_DATABASE_ID"] = "(default)"  # Explicitly use default database
            
            print(f"🔗 Connecting to existing Firebase emulator on port {self.emulator_port}...")
            print(f"✅ Connected to Firebase emulator on port {self.emulator_port}")
            print(f"📊 Using project: {self.project_id}")
            print(f"📁 Using collections with no prefix")
            print(f"🗄️ Using database: (default)")
            
        except Exception as e:
            print(f"❌ Failed to connect to Firebase emulator: {e}")
            raise
    
    def clone_repository(self):
        """Clone the ts-array repository."""
        try:
            # Create temporary directory
            self.temp_dir = Path(tempfile.mkdtemp())
            self.repo_path = self.temp_dir / "ts-array"
            
            print(f"📥 Cloning ts-array repository to: {self.repo_path}")
            
            # Clone the repository
            repo = git.Repo.clone_from(
                "https://github.com/Jassu225/ts-array.git",
                self.repo_path,
                depth=1  # Shallow clone for speed
            )
            
            print(f"✅ Repository cloned successfully")
            print(f"   Latest commit: {repo.head.commit.hexsha[:8]}")
            print(f"   Commit message: {repo.head.commit.message.strip()}")
            
        except Exception as e:
            print(f"❌ Failed to clone repository: {e}")
            raise
    
    async def index_repository(self):
        """Index the cloned repository using the backend FileIndexer."""
        print("\n🔍 Starting repository indexing...")
        
        # Repository details
        repo_id = "ts-array-live"
        repo_url = "https://github.com/Jassu225/ts-array"
        
        # Initialize services
        db = FirestoreDatabase()
        
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
        print(f"🔍 Creating repository in database...")
        success = await db.create_repository(repo_metadata)
        if success:
            print(f"✅ Repository {repo_id} created in database")
        else:
            print(f"❌ Failed to create repository {repo_id} in database")
            return
        
        # Get files to process (only allowed folders)
        repository_files = self.get_repository_files()
        print(f"📁 Found {len(repository_files)} files to process")
        
        # Repository URL for metadata
        repo_url = f"https://github.com/test/{repo_id}"
        
        # Initialize RepositoryIndexer for first-time indexing
        from google.cloud import firestore
        from src.core.repository_indexer import RepositoryIndexer
        
        firestore_client = firestore.Client(
            project="code-index-dev",
            database="(default)"
        )
        repo_indexer = RepositoryIndexer(firestore_client)
        
        # Index repository using RepositoryIndexer
        print(f"🔧 Indexing repository with RepositoryIndexer...")
        results = await repo_indexer.index_repository(
            repo_url=repo_url,
            branch="main"
        )
        
        processed_files = results["processed"]
        failed_files = results["failed"]
        skipped_files = results["skipped"]
        
        # Update repository status
        await db.update_repository(repo_id, {
            "status": "completed",
            "totalFiles": len(repository_files),
            "processedFiles": processed_files,
            "lastUpdated": "2025-01-26T00:00:00Z"
        })
        
        print(f"\n🎉 Repository indexing completed!")
        print(f"   Total files found: {len(repository_files)}")
        print(f"   Successfully processed: {processed_files}")
        print(f"   Failed to process: {failed_files}")
        print(f"   Skipped (not in allowed folders): {skipped_files}")
        
        # Store results for later display
        self.repo_id = repo_id
        self.processed_files = processed_files
        self.total_files = len(repository_files)
    
    def get_repository_files(self) -> List[Path]:
        """Get all relevant files from the cloned repository."""
        if not self.repo_path:
            return []
        
        # File extensions to process
        extensions = {'.ts', '.js', '.tsx', '.jsx', '.json', '.md'}
        
        # Only process files in specific folders
        allowed_folders = {'src', 'app', 'packages'}
        
        files = []
        for file_path in self.repo_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in extensions:
                # Get relative path from repository root
                relative_path = file_path.relative_to(self.repo_path)
                
                # Check if file is in one of the allowed folders or in root
                path_parts = relative_path.parts
                if len(path_parts) == 1 or path_parts[0] in allowed_folders:
                    files.append(relative_path)
        
        # Sort files for consistent processing order
        files.sort()
        return files
    

    
    async def show_results(self):
        """Show detailed results of the indexing."""
        print("\n📊 Indexing Results:")
        print("=" * 60)
        
        # Get repository info
        db = FirestoreDatabase()
        final_repo = await db.get_repository(self.repo_id)
        
        if final_repo:
            print(f"Repository: {final_repo.name}")
            print(f"Status: {final_repo.status}")
            print(f"Total Files: {final_repo.totalFiles}")
            print(f"Processed Files: {final_repo.processedFiles}")
            print(f"Last Updated: {final_repo.lastUpdated}")
        
        # Get all file indices
        file_indices = await db.list_file_indexes(self.repo_id)
        
        # Language distribution
        languages = {}
        total_exports = 0
        total_imports = 0
        
        for file_index in file_indices:
            lang = file_index.language
            languages[lang] = languages.get(lang, 0) + 1
            
            total_exports += len(file_index.exports)
            total_imports += len(file_index.imports)
        
        print(f"\nLanguages found:")
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
    
    async def cleanup(self):
        """Clean up resources."""
        print("\n🧹 Cleaning up...")
        
        # Note: Firebase emulator is managed externally, no need to stop it
        
        # Clean up repository
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
            print("✅ Repository cleanup completed")


async def main():
    """Main entry point."""
    indexer = LiveRepositoryIndexer()
    await indexer.run()


if __name__ == "__main__":
    asyncio.run(main())
