#!/usr/bin/env python3
"""
Debug helper script for FastAPI server.
This script can be used to run the server with debugging enabled.
"""

import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    import uvicorn
    
    print("Starting FastAPI server in debug mode...")
    print(f"Python path: {sys.path}")
    print(f"Working directory: {os.getcwd()}")
    
    # You can set breakpoints in this file or in src/main.py
    # The debugger will stop at breakpoints when using VS Code/Cursor debugger
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )
