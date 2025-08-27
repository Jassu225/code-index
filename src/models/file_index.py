"""
File index data models for tracking exported and imported variables.
"""

from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class Parameter(BaseModel):
    """Function parameter information."""
    
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (e.g., 'string', 'number', 'User[]')")
    required: bool = Field(..., description="Whether parameter is required")
    defaultValue: Optional[str] = Field(None, description="Default value if any (e.g., 'null', '[]', '{}')")
    description: Optional[str] = Field(None, description="Optional parameter description")


class FunctionSignature(BaseModel):
    """Function signature with parameters, return type, and metadata."""
    
    parameters: List[Parameter] = Field(default_factory=list, description="Array of function parameters in order")
    returnType: str = Field(..., description="Return type (e.g., 'Promise<User>', 'void', 'string')")
    isAsync: bool = Field(False, description="Whether function is async")
    isGenerator: bool = Field(False, description="Whether function is a generator")
    overloads: List["FunctionSignature"] = Field(default_factory=list, description="Function overloads if any")


class ClassInfo(BaseModel):
    """Class-specific information."""
    
    extends: Optional[str] = Field(None, description="Parent class if any")
    implements: List[str] = Field(default_factory=list, description="Interfaces implemented")
    methods: List["ExportInfo"] = Field(default_factory=list, description="Class methods")
    properties: List["ExportInfo"] = Field(default_factory=list, description="Class properties")
    constructors: List["ExportInfo"] = Field(default_factory=list, description="Constructor methods")


class InterfaceInfo(BaseModel):
    """Interface-specific information."""
    
    extends: List[str] = Field(default_factory=list, description="Parent interfaces if any")
    methods: List["ExportInfo"] = Field(default_factory=list, description="Interface methods")
    properties: List["ExportInfo"] = Field(default_factory=list, description="Interface properties")
    indexSignatures: List[dict] = Field(default_factory=list, description="Index signatures")
    callSignatures: List[dict] = Field(default_factory=list, description="Call signatures")


class ExportInfo(BaseModel):
    """Information about an exported variable, function, class, or interface."""
    
    name: str = Field(..., description="Variable/function/class/interface name")
    type: str = Field(..., description="Type (e.g., 'function', 'class', 'variable', 'interface')")
    visibility: str = Field(..., description="'public' or 'private'")
    lineNumber: int = Field(..., description="Line where export occurs")
    functionSignature: Optional[FunctionSignature] = Field(None, description="Function-specific details (only for functions)")
    classInfo: Optional[ClassInfo] = Field(None, description="Class-specific details (only for classes)")
    interfaceInfo: Optional[InterfaceInfo] = Field(None, description="Interface-specific details (only for interfaces)")
    
    @field_validator('visibility')
    @classmethod
    def validate_visibility(cls, v):
        """Validate visibility values."""
        if v not in ['public', 'private']:
            raise ValueError("Visibility must be 'public' or 'private'")
        return v


class ImportInfo(BaseModel):
    """Information about an imported variable."""
    
    name: str = Field(..., description="Imported variable name")
    source: str = Field(..., description="Source module/path")
    lineNumber: int = Field(..., description="Line where import occurs")


class FileIndex(BaseModel):
    """File index document storing exported and imported variables."""
    
    repoId: str = Field(..., description="Repository identifier")
    filePath: str = Field(..., description="Relative path within repository")
    fileHash: str = Field(..., description="SHA hash of file content")
    lastCommitSHA: str = Field(..., description="Last processed commit SHA")
    lastCommitTimestamp: str = Field(..., description="ISO 8601 UTC timestamp of last processed commit")
    exports: List[ExportInfo] = Field(default_factory=list, description="Array of exported variables")
    imports: List[ImportInfo] = Field(default_factory=list, description="Array of imported variables")
    updatedAt: str = Field(..., description="ISO 8601 UTC timestamp")
    language: str = Field(..., description="Programming language identifier")
    parseErrors: List[str] = Field(default_factory=list, description="Any parsing errors encountered")
    
    @field_validator('updatedAt', 'lastCommitTimestamp', mode='before')
    @classmethod
    def ensure_utc_timestamp(cls, v):
        """Ensure timestamps are in ISO 8601 UTC format."""
        if isinstance(v, datetime):
            return v.isoformat() + 'Z'
        return v
    
    @field_validator('fileHash', 'lastCommitSHA')
    @classmethod
    def validate_sha_format(cls, v):
        """Validate SHA format (basic check)."""
        if not v or len(v) < 7:  # SHA-1 is 40 chars, SHA-256 is 64 chars
            raise ValueError("Invalid SHA format")
        return v
    



# Update forward references
FunctionSignature.model_rebuild()
ClassInfo.model_rebuild()
InterfaceInfo.model_rebuild()
ExportInfo.model_rebuild()
