"""
Python parser using Tree-sitter.
"""

import logging
from pathlib import Path
from typing import Final, List, Optional
from tree_sitter import Node

from src.models.file_index import ExportInfo, ImportInfo, FunctionSignature, Parameter, ClassInfo
from .base import LanguageParser, ParseResult

logger = logging.getLogger(__name__)

PYTHON_EXPORT_QUERIES: Final[str] = """
(function_definition 
  name: (identifier) @export.function.name)

(class_definition 
  name: (identifier) @export.class.name
  body: (block 
    (function_definition 
      name: (identifier) @export.class.method.name)))

(assignment 
  left: (identifier) @export.variable.name)
"""

class PythonParser(LanguageParser):
    """Python parser using Tree-sitter."""

    EXTENSIONS: Final[List[str]] = ['.py', '.pyi']
    LANGUAGE_NAME: Final[str] = 'python'
    
    def __init__(self):
        super().__init__()
    
    def detect_language(self, file_path: str) -> bool:
        """Check if file is Python."""
        ext = Path(file_path).suffix.lower()
        return ext in PythonParser.EXTENSIONS
    
    def parse(self, content: str) -> ParseResult:
        """Parse Python content."""
        if not self.language:
            raise RuntimeError("Language not set for Python parser")
        
        result = ParseResult()
        result.language = PythonParser.LANGUAGE_NAME
        
        try:
            # Try Tree-sitter parsing first
            tree = self.parser.parse(bytes(content, 'utf8'))
            root_node = tree.root_node
            
            # Extract exports and imports
            result.exports = self._extract_exports(root_node, content)
            result.imports = self._extract_imports(root_node, content)
            
        except Exception as e:
            logger.info(f"Tree-sitter parsing failed, using regex fallback: {e}")
            # Fallback to simple regex parsing
            result.exports = self._extract_exports_regex(content)
            result.imports = self._extract_imports_regex(content)
        
        return result
    
    def _extract_exports(self, root_node: Node, content: str) -> List[ExportInfo]:
        """Extract exports from Python AST."""
        exports = []
        
        # Python doesn't have explicit exports like TypeScript
        # We'll look for function definitions, class definitions, and variable assignments
        # that are at module level (not inside functions/classes)
        
        # Find function definitions
        func_nodes = self._find_nodes_by_type(root_node, 'function_definition')
        for func_node in func_nodes:
            try:
                export_info = self._parse_python_function(func_node, content)
                if export_info:
                    exports.append(export_info)
            except Exception as e:
                logger.warning(f"Error parsing Python function: {e}")
                continue
        
        # Find class definitions
        class_nodes = self._find_nodes_by_type(root_node, 'class_definition')
        for class_node in class_nodes:
            try:
                export_info = self._parse_python_class(class_node, content)
                if export_info:
                    exports.append(export_info)
            except Exception as e:
                logger.warning(f"Error parsing Python class: {e}")
                continue
        
        return exports
    
    def _extract_imports(self, root_node: Node, content: str) -> List[ImportInfo]:
        """Extract imports from Python AST."""
        imports = []
        
        # Find import statements
        import_nodes = self._find_nodes_by_type(root_node, 'import_statement')
        
        for import_node in import_nodes:
            try:
                import_info = self._parse_python_import(import_node, content)
                if import_info:
                    imports.extend(import_info)
            except Exception as e:
                logger.warning(f"Error parsing Python import: {e}")
                continue
        
        return imports
    
    def _parse_python_function(self, func_node: Node, content: str) -> Optional[ExportInfo]:
        """Parse a Python function definition."""
        try:
            # Get line number
            line_number = func_node.start_point[0] + 1
            
            # Extract function name
            name = self._extract_python_function_name(func_node)
            
            # Parse function signature
            function_signature = self._parse_python_function_signature(func_node, content)
            
            return ExportInfo(
                name=name,
                type="function",
                visibility="public",
                lineNumber=line_number,
                functionSignature=function_signature
            )
            
        except Exception as e:
            logger.warning(f"Error parsing Python function: {e}")
            return None
    
    def _parse_python_class(self, class_node: Node, content: str) -> Optional[ExportInfo]:
        """Parse a Python class definition."""
        try:
            # Get line number
            line_number = class_node.start_point[0] + 1
            
            # Extract class name
            name = self._extract_python_class_name(class_node)
            
            # Parse class information
            class_info = self._parse_python_class_info(class_node, content)
            
            return ExportInfo(
                name=name,
                type="class",
                visibility="public",
                lineNumber=line_number,
                classInfo=class_info
            )
            
        except Exception as e:
            logger.warning(f"Error parsing Python class: {e}")
            return None
    
    # Helper methods for Python parsing
    def _find_nodes_by_type(self, root: Node, node_type: str) -> List[Node]:
        """Find all nodes of a specific type in the AST."""
        nodes = []
        
        def traverse(node):
            if node.type == node_type:
                nodes.append(node)
            for child in node.children:
                traverse(child)
        
        traverse(root)
        return nodes
    
    def _extract_python_function_name(self, func_node: Node) -> str:
        """Extract function name from Python function definition."""
        name_node = self._find_child_by_type(func_node, 'identifier')
        if name_node:
            return name_node.text.decode('utf8')
        return "anonymous_function"
    
    def _extract_python_class_name(self, class_node: Node) -> str:
        """Extract class name from Python class definition."""
        name_node = self._find_child_by_type(class_node, 'identifier')
        if name_node:
            return name_node.text.decode('utf8')
        return "anonymous_class"
    
    def _find_child_by_type(self, parent: Node, child_type: str) -> Optional[Node]:
        """Find first child node of a specific type."""
        for child in parent.children:
            if child.type == child_type:
                return child
        return None
    
    def _parse_python_function_signature(self, func_node: Node, content: str) -> FunctionSignature:
        """Parse Python function signature."""
        # Extract parameters
        parameters = self._extract_python_parameters(func_node, content)
        
        # Extract return type annotation
        return_type = self._extract_python_return_type(func_node, content)
        
        return FunctionSignature(
            parameters=parameters,
            returnType=return_type or "any",
            isAsync=False,  # Python async functions would need additional parsing
            isGenerator=False,
            overloads=[]
        )
    
    def _extract_python_parameters(self, func_node: Node, content: str) -> List[Parameter]:
        """Extract parameters from Python function."""
        parameters = []
        
        # Find parameter list
        param_list = self._find_child_by_type(func_node, 'parameters')
        if not param_list:
            return parameters
        
        # Extract individual parameters
        param_nodes = self._find_nodes_by_type(param_list, 'typed_parameter')
        
        for param_node in param_nodes:
            try:
                param_name = self._extract_node_text(param_node, content)
                param_type = self._extract_python_parameter_type(param_node, content)
                
                parameters.append(Parameter(
                    name=param_name,
                    type=param_type or "any",
                    required=True,
                    defaultValue=None,
                    description=None
                ))
            except Exception as e:
                logger.warning(f"Error parsing Python parameter: {e}")
                continue
        
        return parameters
    
    def _extract_node_text(self, node: Node, content: str) -> str:
        """Extract text content from a node."""
        start_byte = node.start_byte
        end_byte = node.end_byte
        return content[start_byte:end_byte].strip()
    
    def _extract_python_parameter_type(self, param_node: Node, content: str) -> Optional[str]:
        """Extract parameter type annotation from Python parameter."""
        type_node = self._find_child_by_type(param_node, 'type')
        if type_node:
            return self._extract_node_text(type_node, content)
        return None
    
    def _extract_python_return_type(self, func_node: Node, content: str) -> Optional[str]:
        """Extract return type annotation from Python function."""
        # Look for return type annotation
        type_node = self._find_child_by_type(func_node, 'type')
        if type_node:
            return self._extract_node_text(type_node, content)
        return None
    
    def _parse_python_class_info(self, class_node: Node, content: str) -> ClassInfo:
        """Parse Python class information."""
        # Extract methods
        methods = []
        method_nodes = self._find_nodes_by_type(class_node, 'function_definition')
        
        for method_node in method_nodes:
            try:
                method_info = self._parse_python_function(method_node, content)
                if method_info:
                    methods.append(method_info)
            except Exception as e:
                logger.warning(f"Error parsing Python class method: {e}")
                continue
        
        return ClassInfo(
            extends=None,  # Python inheritance would need additional parsing
            implements=[],
            methods=methods,
            properties=[],
            constructors=[]
        )
    
    def _parse_python_import(self, import_node: Node, content: str) -> List[ImportInfo]:
        """Parse Python import statement."""
        imports = []
        
        try:
            # Get line number
            line_number = import_node.start_point[0] + 1
            
            # Extract import source
            source = self._extract_python_import_source(import_node, content)
            
            # Extract import names
            names = self._extract_python_import_names(import_node, content)
            
            # Create import info for each imported item
            for name in names:
                imports.append(ImportInfo(
                    name=name,
                    source=source,
                    lineNumber=line_number
                ))
            
        except Exception as e:
            logger.warning(f"Error parsing Python import: {e}")
        
        return imports
    
    def _extract_python_import_source(self, import_node: Node, content: str) -> str:
        """Extract import source from Python import statement."""
        # Look for dotted name or identifier
        dotted_name = self._find_child_by_type(import_node, 'dotted_name')
        if dotted_name:
            return self._extract_node_text(dotted_name, content)
        
        identifier = self._find_child_by_type(import_node, 'identifier')
        if identifier:
            return self._extract_node_text(identifier, content)
        
        return "unknown_source"
    
    def _extract_python_import_names(self, import_node: Node, content: str) -> List[str]:
        """Extract names from Python import statement."""
        names = []
        
        # Look for import specifiers
        specifier_list = self._find_child_by_type(import_node, 'import_specifier')
        if specifier_list:
            for specifier in specifier_list.children:
                if specifier.type == 'identifier':
                    names.append(specifier.text.decode('utf8'))
        
        return names
    
    def _extract_exports_regex(self, content: str) -> List[ExportInfo]:
        """Extract exports using regex fallback."""
        import re
        exports = []
        
        # Simple regex patterns for Python exports
        export_patterns = [
            r'def\s+(\w+)\s*\(',
            r'class\s+(\w+)',
            r'(\w+)\s*=\s*\w+',  # Variable assignments
        ]
        
        for pattern in export_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                name = match.group(1)
                if name:
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    # Determine type based on pattern
                    if 'def' in pattern:
                        export_type = 'function'
                    elif 'class' in pattern:
                        export_type = 'class'
                    else:
                        export_type = 'variable'
                    
                    exports.append(ExportInfo(
                        name=name,
                        type=export_type,
                        visibility='public',
                        lineNumber=line_num
                    ))
        
        return exports
    
    def _extract_imports_regex(self, content: str) -> List[ImportInfo]:
        """Extract imports using regex fallback."""
        import re
        imports = []
        
        # Simple regex pattern for Python imports
        import_patterns = [
            r'import\s+(\w+)',
            r'from\s+([\w.]+)\s+import',
        ]
        
        for pattern in import_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                source = match.group(1)
                if source:
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    imports.append(ImportInfo(
                        name='import',  # Default name
                        source=source,
                        lineNumber=line_num
                    ))
        
        return imports
