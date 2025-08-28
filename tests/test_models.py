"""
Tests for data models.
"""

import pytest
from datetime import datetime

from src.models.file_index import (
    Parameter, FunctionSignature, ExportInfo, ImportInfo, FileIndex
)
from src.models.repository import RepositoryMetadata


class TestParameter:
    """Test Parameter model."""
    
    def test_parameter_creation(self):
        """Test creating a parameter with all fields."""
        param = Parameter(
            name="userData",
            type="UserCreateInput",
            required=True,
            defaultValue=None,
            description="User creation data"
        )
        
        assert param.name == "userData"
        assert param.type == "UserCreateInput"
        assert param.required is True
        assert param.defaultValue is None
        assert param.description == "User creation data"
    
    def test_parameter_with_default_value(self):
        """Test creating a parameter with default value."""
        param = Parameter(
            name="options",
            type="CreateUserOptions",
            required=False,
            defaultValue="{}",
            description="Optional configuration"
        )
        
        assert param.name == "options"
        assert param.type == "CreateUserOptions"
        assert param.required is False
        assert param.defaultValue == "{}"
        assert param.description == "Optional configuration"


class TestFunctionSignature:
    """Test FunctionSignature model."""
    
    def test_function_signature_creation(self):
        """Test creating a function signature."""
        params = [
            Parameter(name="userData", type="UserCreateInput", required=True),
            Parameter(name="options", type="CreateUserOptions", required=False)
        ]
        
        sig = FunctionSignature(
            parameters=params,
            returnType="Promise<User>",
            isAsync=True,
            isGenerator=False,
            overloads=[]
        )
        
        assert len(sig.parameters) == 2
        assert sig.returnType == "Promise<User>"
        assert sig.isAsync is True
        assert sig.isGenerator is False
        assert len(sig.overloads) == 0


class TestExportInfo:
    """Test ExportInfo model."""
    
    def test_function_export_creation(self):
        """Test creating a function export."""
        sig = FunctionSignature(
            parameters=[],
            returnType="void",
            isAsync=False,
            isGenerator=False
        )
        
        export = ExportInfo(
            name="createUser",
            type="function",
            visibility="public",
            lineNumber=45,
            functionSignature=sig
        )
        
        assert export.name == "createUser"
        assert export.type == "function"
        assert export.visibility == "public"
        assert export.lineNumber == 45
        assert export.functionSignature == sig
        assert export.classInfo is None
        assert export.interfaceInfo is None


class TestImportInfo:
    """Test ImportInfo model."""
    
    def test_import_creation(self):
        """Test creating an import."""
        imp = ImportInfo(
            name="UserService",
            source="./services/user",
            lineNumber=15
        )
        
        assert imp.name == "UserService"
        assert imp.source == "./services/user"
        assert imp.lineNumber == 15


class TestFileIndex:
    """Test FileIndex model."""
    
    def test_file_index_creation(self):
        """Test creating a file index."""
        exports = [
            ExportInfo(
                name="createUser",
                type="function",
                visibility="public",
                lineNumber=45
            )
        ]
        
        imports = [
            ImportInfo(
                name="UserService",
                source="./services/user",
                lineNumber=15
            )
        ]
        
        file_index = FileIndex(
            repoId="example-repo",
            filePath="src/services/user.ts",
            fileHash="abc123def456",
            lastCommitSHA="commit123",
            lastCommitTimestamp="2025-01-26T00:00:00Z",
            exports=exports,
            imports=imports,
            updatedAt="2025-01-26T00:00:00Z",
            language="typescript",
            parseErrors=[]
        )
        
        assert file_index.repoId == "example-repo"
        assert file_index.filePath == "src/services/user.ts"
        assert file_index.fileHash == "abc123def456"
        assert file_index.lastCommitSHA == "commit123"
        assert file_index.lastCommitTimestamp == "2025-01-26T00:00:00Z"
        assert len(file_index.exports) == 1
        assert len(file_index.imports) == 1
        assert file_index.language == "typescript"
        assert len(file_index.parseErrors) == 0
    
    def test_file_index_validation(self):
        """Test file index validation."""
        # Test invalid SHA format
        with pytest.raises(ValueError, match="Invalid SHA format"):
            FileIndex(
                repoId="example-repo",
                filePath="src/test.ts",
                fileHash="abc",  # Too short (less than 7 characters)
                lastCommitSHA="commit123",
                lastCommitTimestamp="2025-01-26T00:00:00Z",
                exports=[],
                imports=[],
                updatedAt="2025-01-26T00:00:00Z",
                language="typescript",
                parseErrors=[]
            )
        
        # Test invalid visibility
        with pytest.raises(ValueError, match="Visibility must be 'public' or 'private'"):
            ExportInfo(
                name="test",
                type="function",
                visibility="invalid",  # Invalid visibility
                lineNumber=1
            )


class TestRepositoryMetadata:
    """Test RepositoryMetadata model."""
    
    def test_repository_metadata_creation(self):
        """Test creating repository metadata."""
        repo = RepositoryMetadata(
            repoId="example-repo",
            name="Example Repository",
            url="https://github.com/example/repo",
            lastProcessedCommit="commit123",
            lastProcessedCommitTimestamp="2025-01-26T00:00:00Z",
            totalFiles=100,
            processedFiles=85,
            lastUpdated="2025-01-26T00:00:00Z",
            status="processing"
        )
        
        assert repo.repoId == "example-repo"
        assert repo.name == "Example Repository"
        assert repo.url == "https://github.com/example/repo"
        assert repo.lastProcessedCommit == "commit123"
        assert repo.totalFiles == 100
        assert repo.processedFiles == 85
        assert repo.status == "processing"
    
    def test_repository_metadata_properties(self):
        """Test repository metadata computed properties."""
        repo = RepositoryMetadata(
            repoId="example-repo",
            name="Example Repository",
            url="https://github.com/example/repo",
            lastProcessedCommit="commit123",
            lastProcessedCommitTimestamp="2025-01-26T00:00:00Z",
            totalFiles=100,
            processedFiles=85,
            lastUpdated="2025-01-26T00:00:00Z",
            status="processing"
        )
        
        assert repo.processing_progress == 85.0
        assert repo.is_processing_complete is False
        assert repo.has_failures is True
    
    def test_repository_metadata_validation(self):
        """Test repository metadata validation."""
        # Test invalid status
        with pytest.raises(ValueError, match="Status must be one of"):
            RepositoryMetadata(
                repoId="example-repo",
                name="Example Repository",
                url="https://github.com/example/repo",
                lastProcessedCommit="commit123",
                lastProcessedCommitTimestamp="2025-01-26T00:00:00Z",
                totalFiles=100,
                processedFiles=85,
                lastUpdated="2025-01-26T00:00:00Z",
                status="invalid"  # Invalid status
            )
        
        # Test negative file counts
        with pytest.raises(ValueError, match="File counts cannot be negative"):
            RepositoryMetadata(
                repoId="example-repo",
                name="Example Repository",
                url="https://github.com/example/repo",
                lastProcessedCommit="commit123",
                lastProcessedCommitTimestamp="2025-01-26T00:00:00Z",
                totalFiles=-1,  # Invalid negative count
                processedFiles=0,
                lastUpdated="2025-01-26T00:00:00Z",
                status="pending"
            )
