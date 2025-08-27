#!/usr/bin/env python3
"""
Simple test to see what's happening with Firestore connection.
"""

import os
from google.cloud import firestore


def test_firestore():
    """Test basic Firestore connection."""
    print("🔍 Testing Firestore connection...")
    
    # Set environment variables
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    os.environ["GCP_PROJECT_ID"] = "code-index-dev"
    os.environ["FIRESTORE_DATABASE_ID"] = "(default)"
    
    try:
        # Create client
        client = firestore.Client(
            project="code-index-dev",
            database="(default)"
        )
        print("✅ Firestore client created")
        
        # Try to create a simple document
        doc_ref = client.collection("test").document("hello")
        doc_ref.set({"message": "Hello World", "timestamp": "2025-08-27"})
        print("✅ Document created")
        
        # Try to read it back
        doc = doc_ref.get()
        if doc.exists:
            print(f"✅ Document read back: {doc.to_dict()}")
        else:
            print("❌ Document doesn't exist after creation")
            
        # List collections
        collections = list(client.collections())
        print(f"📚 Collections found: {len(collections)}")
        for collection in collections:
            print(f"  - {collection.id}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_firestore()
