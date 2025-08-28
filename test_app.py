#!/usr/bin/env python3
"""
Test script to debug the FastAPI app startup and route registration.
"""

import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_import():
    """Test basic imports"""
    try:
        from src.api.health import router as health_router
        print("✓ Health router imported successfully")
        print(f"  Routes: {len(health_router.routes)}")
        
        from src.api.files import router as files_router
        print("✓ Files router imported successfully")
        
        from src.api.repositories import router as repositories_router  
        print("✓ Repositories router imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        traceback.print_exc()
        return False

def test_app_creation():
    """Test FastAPI app creation"""
    try:
        # Import without lifespan to avoid GCP dependencies
        from fastapi import FastAPI
        from src.api.health import router as health_router
        from src.api.files import router as files_router
        from src.api.repositories import router as repositories_router
        
        app = FastAPI(title="Test App", version="0.1.0")
        
        # Include routers
        app.include_router(health_router, prefix="/health", tags=["health"])
        app.include_router(files_router, prefix="/files", tags=["files"])
        app.include_router(repositories_router, prefix="/repositories", tags=["repositories"])
        
        @app.get("/")
        async def root():
            return {"status": "ok"}
            
        print("✓ FastAPI app created successfully")
        print(f"  Routes: {len(app.routes)}")
        
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                print(f"    {list(route.methods)} {route.path}")
        
        return app
    except Exception as e:
        print(f"✗ App creation error: {e}")
        traceback.print_exc()
        return None

def test_full_app():
    """Test the full app from main.py"""
    try:
        from src.main import app
        print("✓ Full app from main.py imported successfully")
        print(f"  Routes: {len(app.routes)}")
        return app
    except Exception as e:
        print(f"✗ Full app import error: {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("=== Testing FastAPI App ===")
    
    print("\n1. Testing basic imports...")
    if not test_basic_import():
        exit(1)
    
    print("\n2. Testing simple app creation...")
    simple_app = test_app_creation()
    if not simple_app:
        exit(1)
    
    print("\n3. Testing full app with lifespan...")
    full_app = test_full_app()
    if not full_app:
        exit(1)
    
    print("\n✓ All tests passed!")