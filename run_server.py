#!/usr/bin/env python3
"""
Entry point script for running the FastAPI server.
This script handles the Python path correctly for direct execution.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set environment variable to indicate we're running directly
os.environ["RUNNING_DIRECTLY"] = "true"

if __name__ == "__main__":
    import uvicorn
    
    print("Starting FastAPI server...")
    print(f"Python path: {sys.path}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Source path: {src_path}")
    
    # Import the app after setting up the path
    try:
        from main import app
        print("FastAPI app imported successfully!")
        
        # Start the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        print(f"Import error: {e}")
        print("Available modules in src:")
        for item in src_path.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                print(f"  - {item.name}")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
