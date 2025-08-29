from src.models.file_index import FunctionSignature, Parameter


class TypescriptFallbackParser:
    """Parser for TypeScript fallback scenarios when Tree-sitter fails."""
    
    def __init__(self):
        pass
    
    def parse_function_signature(self, func_name: str, content: str, line_num: int) -> FunctionSignature:
        """Parse function signature using regex fallback."""
        import re
        
        # Find the function definition
        func_pattern = rf'export\s+function\s+{re.escape(func_name)}\s*\(([^)]*)\)\s*(?::\s*(\w+))?'
        func_match = re.search(func_pattern, content)
        
        if not func_match:
            return FunctionSignature(
                parameters=[],
                returnType="any",
                isAsync=False,
                isGenerator=False,
                overloads=[]
            )
        
        # Extract parameters
        params_text = func_match.group(1)
        parameters = []
        if params_text.strip():
            param_names = [p.strip().split(':')[0].strip() for p in params_text.split(',')]
            for param_name in param_names:
                if param_name:
                    parameters.append(Parameter(
                        name=param_name,
                        type="any",
                        required=True,
                        defaultValue=None,
                        description=None
                    ))
        
        # Extract return type
        return_type = func_match.group(2) if func_match.group(2) else "any"
        
        # Check if async
        is_async = 'async' in content[:func_match.start()]
        
        # Check if generator
        is_generator = '*' in content[:func_match.start()]
        
        return FunctionSignature(
            parameters=parameters,
            returnType=return_type,
            isAsync=is_async,
            isGenerator=is_generator,
            overloads=[]
        )
