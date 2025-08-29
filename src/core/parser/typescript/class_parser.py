from src.models.file_index import ClassInfo, ExportInfo


class TypescriptClassParser:
    """Dedicated parser for TypeScript class information."""
    
    def __init__(self):
        pass
    
    def parse_class_info(self, class_name: str, content: str, line_num: int) -> ClassInfo:
        """Parse TypeScript class information from content."""
        import re
        
        # Find the class definition block - handle generic types like TsArray<T>
        class_start_pattern = rf'export\s+class\s+{re.escape(class_name)}(?:\s*<[^>]*>)?\s*{{'
        class_start_match = re.search(class_start_pattern, content)
        
        if not class_start_match:
            return ClassInfo(
                extends=None,
                implements=[],
                methods=[],
                properties=[],
                constructors=[]
            )
        
        # Find the matching closing brace by counting braces
        start_pos = class_start_match.end() - 1  # Position of the opening brace
        brace_count = 0
        end_pos = start_pos
        
        for i, char in enumerate(content[start_pos:], start_pos):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i
                    break
        
        if brace_count != 0:
            return ClassInfo(
                extends=None,
                implements=[],
                methods=[],
                properties=[],
                constructors=[]
            )
        
        class_body = content[start_pos + 1:end_pos]
        
        # Extract methods (public methods) - comprehensive pattern
        # Handle methods with and without return types, with and without parameters
        method_pattern = r'(?:public\s+|private\s+)?(?:get\s+)?(\w+)\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*{'
        methods = []
        seen_methods = set()
        
        for match in re.finditer(method_pattern, class_body):
            method_name = match.group(1)
            if (method_name != class_name and 
                method_name != 'constructor' and 
                method_name not in seen_methods):  # Skip duplicates
                seen_methods.add(method_name)
                # Calculate actual line number within class body
                method_line = line_num + class_body[:match.start()].count('\n') + 1
                methods.append(ExportInfo(
                    name=method_name,
                    type="function",
                    visibility="public",
                    lineNumber=method_line
                ))
        
        # Extract properties (avoid duplicates and parameter confusion)
        # Look for class properties with more specific patterns
        property_patterns = [
            r'(?:public\s+|private\s+)?(\w+)\s*:\s*\w+(?:\s*=\s*[^;]+)?;',  # Class properties
            r'(?:public\s+|private\s+)?(\w+)\s*:\s*\w+\[\]',  # Array properties
        ]
        properties = []
        seen_properties = set()
        
        for pattern in property_patterns:
            for match in re.finditer(pattern, class_body):
                prop_name = match.group(1)
                # Skip if it's a reserved word, already seen, or looks like a parameter
                if (prop_name not in ['extends', 'implements'] and 
                    prop_name not in seen_properties and
                    prop_name not in ['element', 'index', 'newName'] and  # Skip parameter names
                    not re.search(rf'\b{re.escape(prop_name)}\s*\(', class_body)):  # Skip if it's a method
                    seen_properties.add(prop_name)
                    # Calculate actual line number within class body
                    prop_line = line_num + class_body[:match.start()].count('\n') + 1
                    properties.append(ExportInfo(
                        name=prop_name,
                        type="variable",
                        visibility="public",
                        lineNumber=prop_line
                    ))
        
        # Extract constructor
        constructor_pattern = rf'constructor\s*\([^)]*\)\s*{{'
        constructors = []
        constructor_match = re.search(constructor_pattern, class_body)
        if constructor_match:
            # Calculate actual line number within class body
            constructor_line = line_num + class_body[:constructor_match.start()].count('\n') + 1
            constructors.append(ExportInfo(
                name="constructor",
                type="function",
                visibility="public",
                lineNumber=constructor_line
            ))
        
        return ClassInfo(
            extends=None,  # Would need more complex parsing for extends
            implements=[],  # Would need more complex parsing for implements
            methods=methods,
            properties=properties,
            constructors=constructors
        )

