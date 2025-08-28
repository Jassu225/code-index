"""
Base classes for language-specific parsers.
"""

import logging
from typing import List
from tree_sitter import Language, Parser

logger = logging.getLogger(__name__)


class ParseResult:
    """Result of parsing a file."""
    
    def __init__(self):
        self.exports: List = []
        self.imports: List = []
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
