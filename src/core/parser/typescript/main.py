"""
TypeScript/JavaScript parser using Tree-sitter.
"""

import logging
from pathlib import Path
from typing import Final, List, Optional
from tree_sitter import Language, Node, Parser
import tree_sitter_typescript as ts_typescript

from src.models.file_index import ExportInfo, ImportInfo, FunctionSignature, Parameter, ClassInfo, InterfaceInfo
from ..base import LanguageParser, ParseResult
from .class_parser import TypescriptClassParser
from .fallback import TypescriptFallbackParser

logger = logging.getLogger(__name__)


class TypeScriptParser(LanguageParser):
    """TypeScript/JavaScript parser using Tree-sitter."""

    EXTENSIONS: Final[List[str]] = ['.ts', '.tsx', '.js', '.jsx']
    LANGUAGE_NAME: Final[str] = 'typescript'
    LANGUAGE: Final[Language] = Language(ts_typescript.language_typescript())
    
    def __init__(self):
        super().__init__()
        self.parser = Parser(language=TypeScriptParser.LANGUAGE)
        self.class_parser = TypescriptClassParser()
        self.fallback_parser = TypescriptFallbackParser()
    
    def detect_language(self, file_path: str) -> bool:
        """Check if file is TypeScript."""
        ext = Path(file_path).suffix.lower()
        return ext in TypeScriptParser.EXTENSIONS
    
    def parse(self, content: str) -> ParseResult:
        """Parse TypeScript content."""
        result = ParseResult()
        result.language = TypeScriptParser.LANGUAGE_NAME
        
        try:
            # Try Tree-sitter parsing first
            tree = self.parser.parse(content.encode('utf8'))
            root_node = tree.root_node
            logger.info("---------------TREEE-----------------")
            logger.info(tree)
            
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
                print("function declaration")
                return self._parse_function_export(export_node, content, line_number)
            elif self._has_child_type(export_node, 'class_declaration'):
                print("class declaration")
                return self._parse_class_export(export_node, content, line_number)
            elif self._has_child_type(export_node, 'interface_declaration'):
                print("interface declaration")
                return self._parse_interface_export(export_node, content, line_number)
            elif self._has_child_type(export_node, 'variable_declaration'):
                print("variable declaration")
                return self._parse_variable_export(export_node, content, line_number)
            else:
                # Generic export
                print("generic export")
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
    
    def _parse_class_export(self, export_node: Node, content: str, line_number: int) -> ExportInfo:
        """Parse a class export."""
        class_node = self._find_child_by_type(export_node, 'class_declaration')
        if not class_node:
            return None
        
        # Extract class name
        name = self._extract_class_name(class_node)
        
        # Parse class information
        class_info = self._parse_typescript_class_info(class_node, content)
        
        return ExportInfo(
            name=name,
            type="class",
            visibility="public",
            lineNumber=line_number,
            classInfo=class_info
        )
    
    def _parse_interface_export(self, export_node: Node, content: str, line_number: int) -> ExportInfo:
        """Parse an interface export."""
        interface_node = self._find_child_by_type(export_node, 'interface_declaration')
        if not interface_node:
            return None
        
        # Extract interface name
        name = self._extract_interface_name(interface_node)
        
        # Parse interface information
        interface_info = self._parse_typescript_interface_info(interface_node, content)
        
        return ExportInfo(
            name=name,
            type="interface",
            visibility="public",
            lineNumber=line_number,
            interfaceInfo=interface_info
        )
    
    def _parse_variable_export(self, export_node: Node, content: str, line_number: int) -> ExportInfo:
        """Parse a variable export."""
        var_node = self._find_child_by_type(export_node, 'variable_declaration')
        if not var_node:
            return None
        
        # Extract variable name
        name = self._extract_variable_name(var_node)
        
        return ExportInfo(
            name=name,
            type="variable",
            visibility="public",
            lineNumber=line_number
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
    
    def _extract_class_name(self, class_node: Node) -> str:
        """Extract class name from class declaration."""
        name_node = self._find_child_by_type(class_node, 'type_identifier')
        if name_node:
            return name_node.text.decode('utf8')
        return "anonymous_class"
    
    def _extract_interface_name(self, interface_node: Node) -> str:
        """Extract interface name from interface declaration."""
        name_node = self._find_child_by_type(interface_node, 'identifier')
        if name_node:
            return name_node.text.decode('utf8')
        return "anonymous_interface"
    
    def _extract_variable_name(self, var_node: Node) -> str:
        """Extract variable name from variable declaration."""
        # Look for variable declarator
        declarator = self._find_child_by_type(var_node, 'variable_declarator')
        if declarator:
            name_node = self._find_child_by_type(declarator, 'identifier')
            if name_node:
                return name_node.text.decode('utf8')
        return "anonymous_variable"
    
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
    
    def _parse_typescript_class_info(self, class_node: Node, content: str) -> ClassInfo:
        """Parse TypeScript class information."""
        try:
            # Extract extends clause
            extends_clause = self._find_child_by_type(class_node, 'extends_clause')
            extends_class = None
            if extends_clause:
                extends_class = self._extract_node_text(extends_clause, content)
            
            # Extract implements clause
            implements_clause = self._find_child_by_type(class_node, 'implements_clause')
            implements_interfaces = []
            if implements_clause:
                # Extract interface names from implements clause
                interface_list = self._find_child_by_type(implements_clause, 'interface_list')
                if interface_list:
                    for child in interface_list.children:
                        if child.type == 'type_identifier':
                            implements_interfaces.append(child.text.decode('utf8'))
            
            # Extract methods, properties, and constructors
            methods = []
            properties = []
            constructors = []
            
            # Parse class body
            class_body = self._find_child_by_type(class_node, 'class_body')
            if class_body:
                for child in class_body.children:
                    if child.type == 'method_definition':
                        method_info = self._parse_class_method(child, content)
                        if method_info:
                            methods.append(method_info)
                    elif child.type == 'public_field_definition':
                        property_info = self._parse_class_property(child, content)
                        if property_info:
                            properties.append(property_info)
                    elif child.type == 'constructor':
                        constructor_info = self._parse_constructor(child, content)
                        if constructor_info:
                            constructors.append(constructor_info)
            
            return ClassInfo(
                extends=extends_class,
                implements=implements_interfaces,
                methods=methods,
                properties=properties,
                constructors=constructors
            )
            
        except Exception as e:
            logger.warning(f"Error parsing class info: {e}")
            return ClassInfo(
                extends=None,
                implements=[],
                methods=[],
                properties=[],
                constructors=[]
            )
    
    def _parse_typescript_interface_info(self, interface_node: Node, content: str) -> InterfaceInfo:
        """Parse TypeScript interface information."""
        try:
            # Extract extends clause
            extends_clause = self._find_child_by_type(interface_node, 'extends_clause')
            extends_interfaces = []
            if extends_clause:
                # Extract interface names from extends clause
                interface_list = self._find_child_by_type(extends_clause, 'interface_list')
                if interface_list:
                    for child in interface_list.children:
                        if child.type == 'type_identifier':
                            extends_interfaces.append(child.text.decode('utf8'))
            
            # Extract methods and properties
            methods = []
            properties = []
            
            # Parse interface body
            interface_body = self._find_child_by_type(interface_node, 'object_type')
            if interface_body:
                for child in interface_body.children:
                    if child.type == 'method_signature':
                        method_info = self._parse_interface_method(child, content)
                        if method_info:
                            methods.append(method_info)
                    elif child.type == 'property_signature':
                        property_info = self._parse_interface_property(child, content)
                        if property_info:
                            properties.append(property_info)
            
            return InterfaceInfo(
                extends=extends_interfaces,
                methods=methods,
                properties=properties,
                indexSignatures=[],
                callSignatures=[]
            )
            
        except Exception as e:
            logger.warning(f"Error parsing interface info: {e}")
            return InterfaceInfo(
                extends=[],
                methods=[],
                properties=[],
                indexSignatures=[],
                callSignatures=[]
            )
    
    def _parse_class_method(self, method_node: Node, content: str) -> ExportInfo:
        """Parse a class method."""
        try:
            # Extract method name
            name_node = self._find_child_by_type(method_node, 'property_identifier')
            if not name_node:
                return None
            
            name = name_node.text.decode('utf8')
            line_number = method_node.start_point[0] + 1
            
            # Parse function signature if it's a method
            function_signature = None
            if self._has_child_type(method_node, 'formal_parameters'):
                function_signature = self._parse_function_signature(method_node, content)
            
            return ExportInfo(
                name=name,
                type="function",
                visibility="public",  # Default to public for class methods
                lineNumber=line_number,
                functionSignature=function_signature
            )
        except Exception as e:
            logger.warning(f"Error parsing class method: {e}")
            return None
    
    def _parse_class_property(self, property_node: Node, content: str) -> ExportInfo:
        """Parse a class property."""
        try:
            modifier = self._find_child_by_type(property_node, 'accessibility_modifier')
            visibility = "public"
            if modifier:
                visibility = modifier.text.decode('utf8')
            
            if visibility != "public":
                return None
                
            # Extract property name
            name_node = self._find_child_by_type(property_node, 'property_identifier')
            if not name_node:
                return None
            
            name = name_node.text.decode('utf8')
            line_number = property_node.start_point[0] + 1
            
            return ExportInfo(
                name=name,
                type="variable",
                visibility="public",  # Default to public for class properties
                lineNumber=line_number
            )
        except Exception as e:
            logger.warning(f"Error parsing class property: {e}")
            return None
    
    def _parse_constructor(self, constructor_node: Node, content: str) -> ExportInfo:
        """Parse a constructor method."""
        try:
            name = "constructor"
            line_number = constructor_node.start_point[0] + 1
            
            # Parse function signature
            function_signature = self._parse_function_signature(constructor_node, content)
            
            return ExportInfo(
                name=name,
                type="function",
                visibility="public",
                lineNumber=line_number,
                functionSignature=function_signature
            )
        except Exception as e:
            logger.warning(f"Error parsing constructor: {e}")
            return None
    
    def _parse_interface_method(self, method_node: Node, content: str) -> ExportInfo:
        """Parse an interface method signature."""
        try:
            # Extract method name
            name_node = self._find_child_by_type(method_node, 'property_identifier')
            if not name_node:
                return None
            
            name = name_node.text.decode('utf8')
            line_number = method_node.start_point[0] + 1
            
            # Parse function signature
            function_signature = self._parse_function_signature(method_node, content)
            
            return ExportInfo(
                name=name,
                type="function",
                visibility="public",
                lineNumber=line_number,
                functionSignature=function_signature
            )
        except Exception as e:
            logger.warning(f"Error parsing interface method: {e}")
            return None
    
    def _parse_interface_property(self, property_node: Node, content: str) -> ExportInfo:
        """Parse an interface property signature."""
        try:
            # Extract property name
            name_node = self._find_child_by_type(property_node, 'property_identifier')
            if not name_node:
                return None
            
            name = name_node.text.decode('utf8')
            line_number = property_node.start_point[0] + 1
            
            return ExportInfo(
                name=name,
                type="variable",
                visibility="public",
                lineNumber=line_number
            )
        except Exception as e:
            logger.warning(f"Error parsing interface property: {e}")
            return None
    
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
        
        # More specific regex patterns to detect export types
        export_patterns = [
            (r'export\s+function\s+(\w+)', 'function'),
            (r'export\s+class\s+(\w+)', 'class'),
            (r'export\s+interface\s+(\w+)', 'interface'),
            (r'export\s+(?:const|let|var)\s+(\w+)', 'variable'),
            (r'export\s+type\s+(\w+)', 'type'),
            (r'export\s+{\s*(\w+)(?:\s*,\s*\w+)*\s*}', 'variable'),
            (r'export\s+default\s+(\w+)', 'variable'),
            (r'export\s+(\w+)\s*=\s*\w+', 'variable'),
        ]
        
        for pattern, export_type in export_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                name = match.group(1)
                if name:
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # Create export info with proper type
                    export_info = ExportInfo(
                        name=name,
                        type=export_type,
                        visibility='public',
                        lineNumber=line_num
                    )
                    
                    # Add type-specific information for classes
                    if export_type == 'class':
                        class_info = self.class_parser.parse_class_info(name, content, line_num)
                        export_info.classInfo = class_info
                    elif export_type == 'function':
                        function_signature = self.fallback_parser.parse_function_signature(name, content, line_num)
                        export_info.functionSignature = function_signature
                    
                    exports.append(export_info)
        
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
