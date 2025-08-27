"""
Code parsing engine using Tree-sitter for multi-language support.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from tree_sitter import Language, Parser, Node

from ..models.file_index import ExportInfo, ImportInfo, FunctionSignature, Parameter, ClassInfo, InterfaceInfo

logger = logging.getLogger(__name__)


class ParseResult:
    """Result of parsing a file."""
    
    def __init__(self):
        self.exports: List[ExportInfo] = []
        self.imports: List[ImportInfo] = []
        self.language: str = ""
        self.parse_errors: List[str] = []


class LanguageParser:
    """Base class for language-specific parsers."""
    
    def __init__(self, language_name: str):
        self.language_name = language_name
        self.parser = Parser()
        self.language = None
        
    def set_language(self, language: Language):
        """Set the Tree-sitter language for this parser."""
        self.language = language
        self.parser.set_language(language)
    
    def parse(self, content: str) -> ParseResult:
        """Parse file content and extract exports/imports."""
        raise NotImplementedError("Subclasses must implement parse method")
    
    def detect_language(self, file_path: str) -> bool:
        """Check if this parser can handle the given file."""
        raise NotImplementedError("Subclasses must implement detect_language method")


class TypeScriptParser(LanguageParser):
    """TypeScript/JavaScript parser using Tree-sitter."""
    
    def __init__(self):
        super().__init__("typescript")
    
    def detect_language(self, file_path: str) -> bool:
        """Check if file is TypeScript/JavaScript."""
        ext = Path(file_path).suffix.lower()
        return ext in ['.ts', '.tsx', '.js', '.jsx']
    
    def parse(self, content: str) -> ParseResult:
        """Parse TypeScript/JavaScript content."""
        if not self.language:
            raise RuntimeError("Language not set for TypeScript parser")
        
        result = ParseResult()
        result.language = self.language_name
        
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
        """Extract export declarations from AST."""
        exports = []
        
        # Find export statements
        export_nodes = self._find_nodes_by_type(root_node, 'export_statement')
        
        for export_node in export_nodes:
            try:
                export_info = self._parse_export_node(export_node, content)
                if export_info:
                    exports.append(export_info)
            except Exception as e:
                logger.warning(f"Error parsing export node: {e}")
                continue
        
        return exports
    
    def _extract_imports(self, root_node: Node, content: str) -> List[ImportInfo]:
        """Extract import declarations from AST."""
        imports = []
        
        # Find import statements
        import_nodes = self._find_nodes_by_type(root_node, 'import_statement')
        
        for import_node in import_nodes:
            try:
                import_info = self._parse_import_node(import_node, content)
                if import_info:
                    imports.append(import_info)
            except Exception as e:
                logger.warning(f"Error parsing import node: {e}")
                continue
        
        return imports
    
    def _parse_export_node(self, export_node: Node, content: str) -> Optional[ExportInfo]:
        """Parse an export node into ExportInfo."""
        try:
            # Get line number
            line_number = export_node.start_point[0] + 1
            
            # Check export type
            if self._has_child_type(export_node, 'function_declaration'):
                return self._parse_function_export(export_node, content, line_number)
            elif self._has_child_type(export_node, 'class_declaration'):
                return self._parse_class_export(export_node, content, line_number)
            elif self._has_child_type(export_node, 'interface_declaration'):
                return self._parse_interface_export(export_node, content, line_number)
            elif self._has_child_type(export_node, 'variable_declaration'):
                return self._parse_variable_export(export_node, content, line_number)
            else:
                # Generic export
                return ExportInfo(
                    name=self._extract_export_name(export_node),
                    type="variable",
                    visibility="public",
                    lineNumber=line_number
                )
                
        except Exception as e:
            logger.warning(f"Error parsing export node: {e}")
            return None
    
    def _parse_function_export(self, export_node: Node, content: str, line_number: int) -> ExportInfo:
        """Parse a function export."""
        func_node = self._find_child_by_type(export_node, 'function_declaration')
        if not func_node:
            return None
        
        # Extract function name
        name = self._extract_function_name(func_node)
        
        # Parse function signature
        function_signature = self._parse_function_signature(func_node, content)
        
        return ExportInfo(
            name=name,
            type="function",
            visibility="public",
            lineNumber=line_number,
            functionSignature=function_signature
        )
    
    def _parse_function_signature(self, func_node: Node, content: str) -> FunctionSignature:
        """Parse function signature with parameters and return type."""
        # Extract parameters
        parameters = self._extract_function_parameters(func_node, content)
        
        # Extract return type
        return_type = self._extract_return_type(func_node, content)
        
        # Check if async
        is_async = self._is_async_function(func_node)
        
        # Check if generator
        is_generator = self._is_generator_function(func_node)
        
        return FunctionSignature(
            parameters=parameters,
            returnType=return_type or "any",
            isAsync=is_async,
            isGenerator=is_generator,
            overloads=[]
        )
    
    def _extract_function_parameters(self, func_node: Node, content: str) -> List[Parameter]:
        """Extract function parameters."""
        parameters = []
        
        # Find parameter list
        param_list = self._find_child_by_type(func_node, 'formal_parameters')
        if not param_list:
            return parameters
        
        # Extract individual parameters
        param_nodes = self._find_nodes_by_type(param_list, 'required_parameter')
        
        for param_node in param_nodes:
            try:
                param_name = self._extract_node_text(param_node, content)
                param_type = self._extract_parameter_type(param_node, content)
                
                parameters.append(Parameter(
                    name=param_name,
                    type=param_type or "any",
                    required=True,
                    defaultValue=None,
                    description=None
                ))
            except Exception as e:
                logger.warning(f"Error parsing parameter: {e}")
                continue
        
        return parameters
    
    def _extract_import_node(self, import_node: Node, content: str) -> Optional[ImportInfo]:
        """Parse an import node into ImportInfo."""
        try:
            # Get line number
            line_number = import_node.start_point[0] + 1
            
            # Extract import source
            source = self._extract_import_source(import_node, content)
            
            # Extract import names
            names = self._extract_import_names(import_node, content)
            
            # Create import info for each imported item
            imports = []
            for name in names:
                imports.append(ImportInfo(
                    name=name,
                    source=source,
                    lineNumber=line_number
                ))
            
            return imports
            
        except Exception as e:
            logger.warning(f"Error parsing import node: {e}")
            return None
    
    # Helper methods for AST traversal
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
    
    def _find_child_by_type(self, parent: Node, child_type: str) -> Optional[Node]:
        """Find first child node of a specific type."""
        for child in parent.children:
            if child.type == child_type:
                return child
        return None
    
    def _has_child_type(self, parent: Node, child_type: str) -> bool:
        """Check if parent has a child of specific type."""
        return self._find_child_by_type(parent, child_type) is not None
    
    def _extract_node_text(self, node: Node, content: str) -> str:
        """Extract text content from a node."""
        start_byte = node.start_byte
        end_byte = node.end_byte
        return content[start_byte:end_byte].strip()
    
    def _extract_export_name(self, export_node: Node) -> str:
        """Extract the name from an export statement."""
        # This is a simplified implementation
        # In practice, you'd need to handle different export patterns
        return "exported_item"
    
    def _extract_function_name(self, func_node: Node) -> str:
        """Extract function name from function declaration."""
        name_node = self._find_child_by_type(func_node, 'identifier')
        if name_node:
            return name_node.text.decode('utf8')
        return "anonymous_function"
    
    def _extract_parameter_type(self, param_node: Node, content: str) -> Optional[str]:
        """Extract parameter type annotation."""
        type_node = self._find_child_by_type(param_node, 'type_annotation')
        if type_node:
            return self._extract_node_text(type_node, content)
        return None
    
    def _extract_return_type(self, func_node: Node, content: str) -> Optional[str]:
        """Extract function return type."""
        # Look for return type annotation
        type_node = self._find_child_by_type(func_node, 'type_annotation')
        if type_node:
            return self._extract_node_text(type_node, content)
        return None
    
    def _is_async_function(self, func_node: Node) -> bool:
        """Check if function is async."""
        # Look for async modifier
        for child in func_node.children:
            if child.type == 'async' and child.text == b'async':
                return True
        return False
    
    def _is_generator_function(self, func_node: Node) -> bool:
        """Check if function is a generator."""
        # Look for generator syntax (*)
        for child in func_node.children:
            if child.type == '*' and child.text == b'*':
                return True
        return False
    
    def _extract_import_source(self, import_node: Node, content: str) -> str:
        """Extract import source path."""
        # Look for string literal in import
        string_node = self._find_child_by_type(import_node, 'string')
        if string_node:
            return self._extract_node_text(string_node, content).strip('"\'')
        return "unknown_source"
    
    def _extract_import_names(self, import_node: Node, content: str) -> List[str]:
        """Extract names from import statement."""
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
        
        # Simple regex patterns for common export statements
        export_patterns = [
            r'export\s+(?:const|let|var|function|class|interface|type)\s+(\w+)',
            r'export\s+{\s*(\w+)(?:\s*,\s*\w+)*\s*}',
            r'export\s+default\s+(\w+)',
            r'export\s+(\w+)\s*=\s*\w+',
        ]
        
        for pattern in export_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                name = match.group(1)
                if name:
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    exports.append(ExportInfo(
                        name=name,
                        type='variable',  # Default type
                        visibility='public',
                        lineNumber=line_num
                    ))
        
        return exports
    
    def _extract_imports_regex(self, content: str) -> List[ImportInfo]:
        """Extract imports using regex fallback."""
        import re
        imports = []
        
        # Simple regex pattern for import statements
        import_pattern = r'import\s+(?:\{[^}]*\}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        matches = re.finditer(import_pattern, content, re.MULTILINE)
        
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


class PythonParser(LanguageParser):
    """Python parser using Tree-sitter."""
    
    def __init__(self):
        super().__init__("python")
    
    def detect_language(self, file_path: str) -> bool:
        """Check if file is Python."""
        ext = Path(file_path).suffix.lower()
        return ext in ['.py', '.pyi']
    
    def parse(self, content: str) -> ParseResult:
        """Parse Python content."""
        if not self.language:
            raise RuntimeError("Language not set for Python parser")
        
        result = ParseResult()
        result.language = self.language_name
        
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
    



class CodeParser:
    """
    Main code parser that delegates to language-specific parsers.
    """
    
    def __init__(self):
        """Initialize the code parser with supported languages."""
        self.parsers: Dict[str, LanguageParser] = {
            'typescript': TypeScriptParser(),
            'python': PythonParser(),
        }
        
        # Initialize Tree-sitter languages
        self._initialize_languages()
    
    def _initialize_languages(self):
        """Initialize Tree-sitter languages."""
        try:
            # In a real implementation, you'd build and load the Tree-sitter grammars
            # For now, we'll create mock languages
            logger.info("Initializing Tree-sitter languages...")
            
            # This would normally load actual grammar files
            # For now, we'll skip the actual language loading
            
            # Set mock languages for basic functionality
            for parser in self.parsers.values():
                # Create a mock language object that won't crash
                class MockLanguage:
                    def __init__(self, name):
                        self.name = name
                
                parser.language = MockLanguage(parser.language_name)
            
        except Exception as e:
            logger.error(f"Error initializing Tree-sitter languages: {e}")
    
    def detect_language(self, file_path: str) -> str:
        """
        Detect programming language based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language identifier
        """
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.ts', '.tsx', '.js', '.jsx']:
            return 'typescript'
        elif ext in ['.py', '.pyi']:
            return 'python'
        elif ext in ['.go']:
            return 'go'
        elif ext in ['.java']:
            return 'java'
        elif ext in ['.cs']:
            return 'csharp'
        else:
            return 'unknown'
    
    async def parse_file(self, file_path: str, content: str) -> ParseResult:
        """
        Parse a file and extract exports/imports.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            ParseResult with extracted information
        """
        language = self.detect_language(file_path)
        
        if language == 'unknown':
            result = ParseResult()
            result.language = language
            result.parse_errors.append(f"Unsupported language for file: {file_path}")
            return result
        
        parser = self.parsers.get(language)
        if not parser:
            result = ParseResult()
            result.language = language
            result.parse_errors.append(f"No parser available for language: {language}")
            return result
        
        try:
            return parser.parse(content)
        except Exception as e:
            result = ParseResult()
            result.language = language
            result.parse_errors.append(f"Error parsing {language} file: {e}")
            return result
