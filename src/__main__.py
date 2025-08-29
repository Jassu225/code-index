#!/usr/bin/env python3
"""
Main entry point for running the FastAPI server as a module.
This allows the package to be run with: python -m src
"""

import uvicorn

if __name__ == "__main__":
    print("Starting FastAPI server as module...")
    
    # Run the server using the module path
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
