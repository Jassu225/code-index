#!/usr/bin/env python3
"""
Test script to debug CodeParser directly.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.parser import CodeParser

async def test_parser():
    """Test CodeParser directly."""
    print("🧪 Testing CodeParser directly...")
    
    try:
        # Create CodeParser
        parser = CodeParser()
        
        # Test TypeScript parsing
        print("\n📝 Testing TypeScript parsing...")
        ts_content = 'export function hello() { return "Hello World"; }'
        ts_result = await parser.parse_file("test.ts", ts_content)
        
        print(f"   Language: {ts_result.language}")
        print(f"   Exports: {len(ts_result.exports)}")
        print(f"   Imports: {len(ts_result.imports)}")
        print(f"   Errors: {ts_result.parse_errors}")
        
        if ts_result.exports:
            for export in ts_result.exports:
                print(f"     Export: {export.name} ({export.type})")
        
        # Test Python parsing
        print("\n🐍 Testing Python parsing...")
        py_content = 'def hello():\n    return "Hello World"\n\nexport = hello'
        py_result = await parser.parse_file("test.py", py_content)
        
        print(f"   Language: {py_result.language}")
        print(f"   Exports: {len(py_result.exports)}")
        print(f"   Imports: {len(py_result.imports)}")
        print(f"   Errors: {py_result.parse_errors}")
        
        if py_result.exports:
            for export in py_result.exports:
                print(f"     Export: {export.name} ({export.type})")
                
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_parser())
