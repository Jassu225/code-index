"""
Main code parser that delegates to language-specific parsers.
"""

import logging
from pathlib import Path
from typing import Dict

from .base import LanguageParser, ParseResult
from .typescript import TypeScriptParser
from .python import PythonParser

logger = logging.getLogger(__name__)


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
        
        if ext in TypeScriptParser.EXTENSIONS:
            return TypeScriptParser.LANGUAGE_NAME
        elif ext in PythonParser.EXTENSIONS:
            return PythonParser.LANGUAGE_NAME
        # elif ext in ['.go']:
        #     return 'go'
        # elif ext in ['.java']:
        #     return 'java'
        # elif ext in ['.cs']:
        #     return 'csharp'
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
            print(f"Parsing {file_path} with {language} parser")
            return parser.parse(content)
        except Exception as e:
            result = ParseResult()
            result.language = language
            result.parse_errors.append(f"Error parsing {language} file: {e}")
            return result
