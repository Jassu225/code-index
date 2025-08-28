#!/usr/bin/env python3
"""
Simple script to check what's in the Firebase emulator database.
"""

import os
import asyncio
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.database import FirestoreDatabase


async def check_database():
    """Check what's in the database."""
    print("🔍 Checking Firebase emulator database...")
    
    # Set environment variables
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    os.environ["GCP_PROJECT_ID"] = "icode-94891"
    os.environ["FIRESTORE_COLLECTION_PREFIX"] = ""  # Override config to use no prefix
    os.environ["FIRESTORE_DATABASE_ID"] = "(default)"  # Explicitly use default database
    
    try:
        # Initialize database
        db = FirestoreDatabase()
        print("✅ Database client initialized")
        
        # Check repositories
        print("\n📚 Checking repositories...")
        repositories = await db.list_repositories()
        print(f"Found {len(repositories)} repositories:")
        for repo in repositories:
            print(f"  - {repo.repoId}: {repo.name} ({repo.status})")
        
        # Check file indexes
        print("\n📁 Checking file indexes...")
        if repositories:
            repo_id = repositories[0].repoId
            file_indexes = await db.list_file_indexes(repo_id)
            print(f"Found {len(file_indexes)} file indexes for {repo_id}:")
            for file_idx in file_indexes[:5]:  # Show first 5
                print(f"  - {file_idx.filePath} ({file_idx.language})")
            if len(file_indexes) > 5:
                print(f"  ... and {len(file_indexes) - 5} more files")
        
        print("\n✅ Database check completed!")
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_database())
