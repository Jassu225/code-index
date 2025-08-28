#!/usr/bin/env python3
"""
Debug script to see exactly what database configuration is being used.
"""

import os
import asyncio
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.database import FirestoreDatabase
from src.core.config import get_settings


async def debug_database():
    """Debug the database configuration."""
    print("🔍 Debugging Database Configuration...")
    
    # Set environment variables
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    os.environ["GCP_PROJECT_ID"] = "icode-94891"
    os.environ["FIRESTORE_COLLECTION_PREFIX"] = ""
    os.environ["FIRESTORE_DATABASE_ID"] = "(default)"
    
    print(f"📋 Environment Variables Set:")
    print(f"  FIRESTORE_EMULATOR_HOST: {os.environ.get('FIRESTORE_EMULATOR_HOST')}")
    print(f"  GCP_PROJECT_ID: {os.environ.get('GCP_PROJECT_ID')}")
    print(f"  FIRESTORE_COLLECTION_PREFIX: '{os.environ.get('FIRESTORE_COLLECTION_PREFIX')}'")
    print(f"  FIRESTORE_DATABASE_ID: {os.environ.get('FIRESTORE_DATABASE_ID')}")
    
    print(f"\n📊 Settings from Config:")
    settings = get_settings()
    print(f"  gcp_project_id: {settings.gcp_project_id}")
    print(f"  firestore_collection_prefix: '{settings.firestore_collection_prefix}'")
    print(f"  firestore_database_id: {settings.firestore_database_id}")
    
    print(f"\n🔗 Creating Database Client...")
    try:
        db = FirestoreDatabase()
        print(f"✅ Database client created")
        
        # Check what collections exist
        print(f"\n📚 Checking existing collections...")
        collections = list(db.client.collections())
        print(f"Found {len(collections)} collections:")
        for collection in collections:
            print(f"  - {collection.id}")
            
        # Try to create a test document in repositories collection
        print(f"\n🧪 Testing repository collection creation...")
        from src.models.repository import RepositoryMetadata
        
        test_repo = RepositoryMetadata(
            repoId="debug-test",
            name="debug-repo",
            url="https://github.com/test/debug",
            lastProcessedCommit="",
            lastProcessedCommitTimestamp="2025-01-26T00:00:00Z",
            totalFiles=0,
            processedFiles=0,
            lastUpdated="2025-01-26T00:00:00Z",
            status="pending"
        )
        
        success = await db.create_repository(test_repo)
        print(f"Repository creation: {'✅ Success' if success else '❌ Failed'}")
        
        # Check collections again
        print(f"\n📚 Checking collections after test...")
        collections = list(db.client.collections())
        print(f"Found {len(collections)} collections:")
        for collection in collections:
            print(f"  - {collection.id}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_database())
