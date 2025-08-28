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
                if export.functionSignature:
                    print(f"       Function signature: {export.functionSignature}")
                if export.classInfo:
                    print(f"       Class info: {export.classInfo}")
        
        # Test TypeScript class parsing
        print("\n🏗️ Testing TypeScript class parsing...")
        ts_class_content = '''
export class MyClass {
    private name: string;
    
    constructor(name: string) {
        this.name = name;
    }
    
    public getName(): string {
        return this.name;
    }
    
    private setName(newName: string): void {
        this.name = newName;
    }
}
'''
        ts_class_result = await parser.parse_file("test_class.ts", ts_class_content)
        
        print(f"   Language: {ts_class_result.language}")
        print(f"   Exports: {len(ts_class_result.exports)}")
        print(f"   Imports: {len(ts_class_result.imports)}")
        print(f"   Errors: {ts_class_result.parse_errors}")
        
        if ts_class_result.exports:
            for export in ts_class_result.exports:
                print(f"     Export: {export.name} ({export.type})")
                if export.functionSignature:
                    print(f"       Function signature: {export.functionSignature}")
                if export.classInfo:
                    print(f"       Class info: {export.classInfo}")
                    if export.classInfo.methods:
                        print(f"         Methods: {len(export.classInfo.methods)}")
                        for method in export.classInfo.methods:
                            print(f"           Method: {method.name} ({method.type})")
                    if export.classInfo.properties:
                        print(f"         Properties: {len(export.classInfo.properties)}")
                        for prop in export.classInfo.properties:
                            print(f"           Property: {prop.name} ({prop.type})")
                else:
                    print(f"       ⚠️  Class info is null!")
        
        # Test with actual repository content
        print(f"\n🏗️ Testing with actual repository content...")
        actual_repo_content = '''/** 
 * TS-Array: A highly performant array-like object 
 * for push, pop, shift and unshift operations. 
 */ 
export class TsArray<T> { 
    private elements: T[] = []; 
    /** 
     * Pushes an element to the end of the array 
     * @param element - The element to add 
     * @returns The new length of the array 
     */ 
    push(element: T): number { 
        return this.elements.push(element); 
    } 
    /** 
     * Removes and returns the last element of the array 
     * @returns The last element or undefined if array is empty 
     */ 
    pop(): T | undefined { 
        return this.elements.pop(); 
    } 
    /** 
     * Removes and returns the first element of the array 
     * @returns The first element or undefined if array is empty 
     */ 
    shift(): T | undefined { 
        return this.elements.shift(); 
    } 
    /** 
     * Adds an element to the beginning of the array 
     * @param element - The element to add 
     * @returns The new length of the array 
     */ 
    unshift(element: T): number { 
        return this.elements.unshift(element); 
    } 
    /** 
     * Gets the length of the array 
     * @returns The number of elements in the array 
     */ 
    get length(): number { 
        return this.elements.length; 
    } 
    /** 
     * Gets an element at the specified index 
     * @param index - The index of the element 
     * @returns The element at the specified index 
     */ 
    get(index: number): T | undefined { 
        return this.elements[index]; 
    } 
} 
export default TsArray;'''
        
        actual_result = await parser.parse_file("actual_repo.ts", actual_repo_content)
        
        print(f"   Language: {actual_result.language}")
        print(f"   Exports: {len(actual_result.exports)}")
        print(f"   Imports: {len(actual_result.imports)}")
        print(f"   Errors: {actual_result.parse_errors}")
        
        if actual_result.exports:
            for export_info in actual_result.exports:
                print(f"     Export: {export_info.name} ({export_info.type})")
                if export_info.functionSignature:
                    print(f"       Function signature: {export_info.functionSignature}")
                if export_info.classInfo:
                    print(f"       Class info: {export_info.classInfo}")
                    if export_info.classInfo.methods:
                        print(f"         Methods: {len(export_info.classInfo.methods)}")
                        for method in export_info.classInfo.methods:
                            print(f"           Method: {method.name} ({method.type})")
                    if export_info.classInfo.properties:
                        print(f"         Properties: {len(export_info.classInfo.properties)}")
                        for prop in export_info.classInfo.properties:
                            print(f"           Property: {prop.name} ({prop.type})")
                else:
                    print(f"       ⚠️  Class info is null!")
        
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
