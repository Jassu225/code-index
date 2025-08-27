# Serverless Code Index System - Technical Specification

## Overview

The Serverless Code Index System is a scalable backend solution designed to track exported and imported variables across files in git repositories. The system processes commits incrementally and maintains an up-to-date index of all public and private variables along with their types, enabling efficient code analysis and dependency tracking.

## Architecture & Technology Stack

### Compute Platform

- **Cloud Run**: Primary compute platform for processing files
  - Better suited than Cloud Functions for longer execution times
  - Supports concurrent processing with configurable concurrency limits
  - Auto-scaling based on queue depth
  - **Backend Framework**: FastAPI (Python)
    - High-performance async web framework
    - Automatic API documentation with OpenAPI/Swagger
    - Built-in data validation and serialization
    - Excellent async support for concurrent file processing

### Queue Management

- **Cloud Run Jobs**: Batch processing for large repositories
  - Handles entire repositories in single long-running jobs
  - Better suited for CPU-intensive parsing operations
  - Configurable resource limits (CPU, memory, timeout)
  - Progress tracking and status updates via Firestore
- **Direct Processing**: Immediate processing for small repositories
  - Synchronous processing for repos with < 100 files
  - Fast response times for quick indexing
  - No queue overhead for small workloads

### Data Storage

- **Cloud Firestore**: Primary data store for index data
  - Document-based storage for flexible schema
  - Real-time updates and offline support
  - Automatic scaling and global distribution

### Distributed Locking

- **Firestore Transactions**: File-level distributed locks
  - Prevents multiple instances from processing the same file simultaneously
  - TTL-based lock expiration for automatic cleanup
  - Atomic lock acquire/release operations

### Event Triggers

- **Cloud Build Triggers**: Primary trigger mechanism
  - Automatically triggered on git commits
  - Alternative: GitHub webhooks for direct integration
  - Configurable trigger conditions and filters

### Code Parsing

- **Tree-sitter Parsers**: Multi-language AST analysis
  - Support for JavaScript, TypeScript, and other strongly-typed languages
  - Accurate syntax tree generation for reliable parsing
  - Extensible parser ecosystem
  - **Python Integration**:
    - Tree-sitter Python bindings for efficient parsing
    - Async processing capabilities for large files
    - Integration with Python's type system for enhanced analysis

## Core Processing Flow

### 1. Commit Reception

- Git commit event triggers the system
- Cloud Build or GitHub webhook initiates processing
- System queues individual changed files for processing

### 2. File Processing Strategy

- **Small Repositories (< 100 files)**: Direct synchronous processing
  - Files processed immediately in the API request
  - Fast response times for quick indexing
  - No queue overhead or delays
- **Large Repositories (> 100 files)**: Cloud Run Jobs for batch processing
  - Entire repository processed in single long-running job
  - Progress tracked and updated in Firestore
  - Better resource utilization and cost efficiency

### 3. Distributed Lock Acquisition

- File-level lock acquired using key: `${repoId}:${filePath}`
- Lock key does NOT include commit SHA for stability
- Firestore transaction ensures atomic lock operations
- TTL-based expiration prevents deadlocks

### 4. Hash Comparison & Deduplication

- File content hash compared with last processed hash
- Processing skipped if file content unchanged
- **Commit timestamp validation**: Skip processing if commit timestamp is older than last processed commit
- SHA-based change detection for reliable state tracking
- Optimizes performance by avoiding unnecessary work and out-of-order commits

### 5. Code Parsing & Analysis

- Tree-sitter parser generates AST for the file
- Exports and imports extracted from syntax tree
- Type information captured where available
- Language-specific parsing rules applied
- **FastAPI Async Processing**:
  - Concurrent file processing using Python asyncio
  - Non-blocking I/O operations for file reading and parsing
  - Efficient memory management for large repositories

### 6. Atomic Data Update

- Results stored in Firestore using transactions
- File hash and commit SHA updated atomically
- Distributed lock released after successful processing
- Error handling ensures lock release on failures

## Data Structure

### File Index Document

```python
{
  "repoId": str,            # Repository identifier
  "filePath": str,          # Relative path within repository
  "fileHash": str,          # SHA hash of file content
  "lastCommitSHA": str,     # Last processed commit SHA
  "lastCommitTimestamp": str, # ISO 8601 UTC timestamp of last processed commit
  "exports": [               # Array of exported variables
    {
      "name": str,          # Variable/function name
      "type": str,          # Type information (e.g., 'function', 'class', 'variable', 'interface')
      "visibility": str,    # 'public' or 'private'
      "lineNumber": int,    # Line where export occurs
      "functionSignature": { # Function-specific details (only for functions)
        "parameters": [      # Array of function parameters in order
          {
            "name": str,     # Parameter name
            "type": str,     # Parameter type (e.g., 'string', 'number', 'User[]')
            "required": bool, # Whether parameter is required
            "defaultValue": str, # Default value if any (e.g., 'null', '[]', '{}')
            "description": str   # Optional parameter description
          }
        ],
        "returnType": str,   # Return type (e.g., 'Promise<User>', 'void', 'string')
        "isAsync": bool,     # Whether function is async
        "isGenerator": bool, # Whether function is a generator
        "overloads": [       # Function overloads if any
          {
            "parameters": [...], # Same structure as above
            "returnType": str,
            "isAsync": bool,
            "isGenerator": bool
          }
        ]
      },
      "classInfo": {         # Class-specific details (only for classes)
        "extends": str,      # Parent class if any
        "implements": [str], # Interfaces implemented
        "methods": [...],    # Class methods (same structure as exports)
        "properties": [...], # Class properties
        "constructors": [...] # Constructor methods
      },
      "interfaceInfo": {     # Interface-specific details (only for interfaces)
        "extends": [str],    # Parent interfaces if any
        "methods": [...],    # Interface methods
        "properties": [...], # Interface properties
        "indexSignatures": [...], # Index signatures
        "callSignatures": [...]   # Call signatures
      }
    }
  ],
  "imports": [               # Array of imported variables
    {
      "name": str,          # Imported variable name
      "source": str,        # Source module/path
      "lineNumber": int     # Line where import occurs
    }
  ],
  "updatedAt": str,         # ISO 8601 UTC timestamp
  "language": str,          # Programming language identifier
  "parseErrors": List[str]  # Any parsing errors encountered
}
```

### Repository Metadata

```python
{
  "repoId": str,            # Repository identifier
  "name": str,              # Repository name
  "url": str,               # Repository URL
  "lastProcessedCommit": str, # Last processed commit SHA
  "lastProcessedCommitTimestamp": str, # ISO 8601 UTC timestamp of last processed commit
  "totalFiles": int,        # Total files in repository
  "processedFiles": int,    # Number of successfully processed files
  "lastUpdated": str,       # ISO 8601 UTC timestamp
  "status": str             # Processing status
}
```

## Critical Requirements

### Concurrency Safety

- File-level distributed locks prevent race conditions
- Multiple instances can process different files simultaneously
- Lock acquisition and release are atomic operations
- TTL-based expiration prevents deadlocks

### Deduplication Strategy

- Hash-based change detection avoids reprocessing unchanged files
- **File-level timestamp validation** prevents processing older file modifications out of order
- File content SHA comparison for reliable change detection
- Commit SHA tracking for audit and debugging purposes
- Efficient processing of large repositories with temporal ordering

### Enhanced Data Structure for Complex Types

The system captures detailed information about exported items, including comprehensive function signatures, class definitions, and interface specifications. **Imports are kept minimal since exports already contain all type information**:

#### **Import Structure (Minimal)**

```python
# Imports only track what's imported, not how it's typed
"imports": [
  {
    "name": "UserService",        # What's imported
    "source": "./services/user",  # Where it's imported from
    "lineNumber": 15              # Where the import occurs
  }
]
```

#### **Export Structure (Comprehensive)**

```python
# Exports contain full type information for what's available
"exports": [
  {
    "name": "UserService",
    "type": "class",
    "functionSignature": { ... },  # Full type details
    "classInfo": { ... }          # Complete class information
  }
]
```

**Rationale**: Since exports already contain complete type information, storing types in imports would be redundant and could lead to inconsistencies between the source of truth (exports) and the import references.

#### **Function Signature Capture**

```python
# Example: Function with parameters, types, and overloads
{
  "name": "createUser",
  "type": "function",
  "visibility": "public",
  "lineNumber": 45,
  "functionSignature": {
    "parameters": [
      {
        "name": "userData",
        "type": "UserCreateInput",
        "required": true,
        "defaultValue": null,
        "description": "User creation data"
      },
      {
        "name": "options",
        "type": "CreateUserOptions",
        "required": false,
        "defaultValue": "{}",
        "description": "Optional configuration"
      }
    ],
    "returnType": "Promise<User>",
    "isAsync": true,
    "isGenerator": false,
    "overloads": [
      {
        "parameters": [
          {"name": "email", "type": "string", "required": true, "defaultValue": null},
          {"name": "password", "type": "string", "required": true, "defaultValue": null}
        ],
        "returnType": "Promise<User>",
        "isAsync": true,
        "isGenerator": false
      }
    ]
  }
}
```

#### **Class Definition Capture**

```python
# Example: Class with inheritance and methods
{
  "name": "UserService",
  "type": "class",
  "visibility": "public",
  "lineNumber": 23,
  "classInfo": {
    "extends": "BaseService",
    "implements": ["IUserService", "ILoggable"],
    "methods": [
      {
        "name": "findById",
        "type": "function",
        "visibility": "public",
        "functionSignature": {
          "parameters": [
            {"name": "id", "type": "string", "required": true, "defaultValue": null}
          ],
          "returnType": "Promise<User | null>",
          "isAsync": true,
          "isGenerator": false
        }
      }
    ],
    "properties": [
      {
        "name": "userRepository",
        "type": "IUserRepository",
        "visibility": "private"
      }
    ]
  }
}
```

#### **Interface Definition Capture**

```python
# Example: Interface with method signatures
{
  "name": "IUserService",
  "type": "interface",
  "visibility": "public",
  "lineNumber": 15,
  "interfaceInfo": {
    "extends": ["IService"],
    "methods": [
      {
        "name": "createUser",
        "type": "function",
        "functionSignature": {
          "parameters": [
            {"name": "userData", "type": "UserCreateInput", "required": true}
          ],
          "returnType": "Promise<User>",
          "isAsync": true,
          "isGenerator": false
        }
      }
    ],
    "properties": [
      {
        "name": "version",
        "type": "string",
        "required": true
      }
    ]
  }
}
```

### Enhanced Deduplication with File-Level Timestamp Validation

The system implements a **two-layer deduplication strategy** to ensure optimal performance and data consistency. **Timestamp validation is done at the file level for better accuracy and granularity**:

#### **Layer 1: Content Hash Comparison**

```python
async def should_process_file(self, repo_url: str, file_path: str, file_hash: str) -> bool:
    # Check if file content has changed
    existing_file = await self.get_file_index(repo_url, file_path)
    if existing_file and existing_file.fileHash == file_hash:
        return False  # Skip unchanged files
    return True
```

#### **Layer 2: File-Level Timestamp Validation**

```python
async def should_process_file_by_timestamp(self, repo_url: str, file_path: str, file_timestamp: str) -> bool:
    # Get last processed timestamp for this specific file
    existing_file = await self.get_file_index(repo_url, file_path)
    if not existing_file or not existing_file.lastCommitTimestamp:
        return True  # First time processing this file, always process

    # Parse timestamps for comparison
    last_timestamp = datetime.fromisoformat(existing_file.lastCommitTimestamp.replace('Z', '+00:00'))
    current_timestamp = datetime.fromisoformat(file_timestamp.replace('Z', '+00:00'))

    # Skip if current file modification is older than last processed
    if current_timestamp < last_timestamp:
        logger.info(f"Skipping older file modification {file_path} (timestamp: {file_timestamp}) "
                   f"for repo {repo_url} - last processed: {existing_file.lastCommitTimestamp}")
        return False

    return True
```

#### **Combined Validation in File Processing**

```python
async def process_file(self, repo_url: str, file_path: str, commit_sha: str, file_timestamp: str):
    # First: Validate file modification timestamp
    if not await self.should_process_file_by_timestamp(repo_url, file_path, file_timestamp):
        logger.info(f"Skipping file {file_path} with older modification timestamp {file_timestamp}")
        return

    # Second: Check file content hash
    file_content = await self.get_file_content(repo_url, file_path, commit_sha)
    file_hash = hashlib.sha256(file_content.encode()).hexdigest()

    if not await self.should_process_file(repo_url, file_path, file_hash):
        logger.info(f"Skipping unchanged file {file_path}")
        return

    # Process the file...
    await self.parse_and_index_file(repo_url, file_path, commit_sha, file_timestamp, file_hash)
```

### Atomic Operations

- Firestore transactions ensure data consistency
- All related updates happen atomically
- Rollback capability on transaction failures
- Consistent state across all operations

### Error Isolation

- Failed file processing doesn't block other files
- Individual file failures logged and reported
- Dead letter queue for failed tasks
- Comprehensive error tracking and monitoring

## Parsing Capabilities

### Supported Languages

- **JavaScript (ES6+)**: Modern JS syntax with modules
- **TypeScript**: Full type system support
- **Python**: Import/export statements and type hints (native support)
- **Go**: Package imports and exports
- **Java**: Class and interface declarations
- **C#**: Namespace and class definitions

### Parsing Goals

- Track all exported variables (public and private) with **comprehensive type information**
- Track all imported variables per file (**minimal info - name, source, location**)
- **Extract comprehensive function signatures** including parameters, types, and order
- **Capture class and interface definitions** with inheritance and implementation details
- **Parse method overloads** and complex type expressions
- Support for strongly-typed languages
- No cycle detection required
- No variable usage tracking within files

**Note**: Imports are kept minimal since the complete type information is already available in the corresponding exports from the source files.

### Type Information

- Extract type annotations where available
- Infer types from context when possible
- Support for generic types and interfaces
- Handle union types and complex type expressions
- **Comprehensive Function Signature Extraction**:
  - Parameter names, types, and order preservation
  - Default values and required/optional flags
  - Return types including complex types (Promise<T>, Union types)
  - Async/await and generator function detection
  - Function overloads and multiple signatures
- **Advanced Type System Support**:
  - Generic types with type parameters
  - Union and intersection types
  - Conditional and mapped types
  - Template literal types
  - Index signatures and call signatures
- **Python Type System Integration**:
  - Leverage Python's built-in typing module
  - Support for type hints, generics, and Union types
  - Integration with mypy for enhanced type checking
  - Async type support for concurrent operations

## Cloud Run Jobs Configuration

### Job Settings

- **CPU**: 2-4 vCPUs for parsing operations
- **Memory**: 4-8 GB for large file processing
- **Timeout**: Up to 24 hours for large repositories
- **Concurrency**: Single job per repository for consistency

### Resource Management

- **Auto-scaling**: Jobs scale based on repository size
- **Progress Tracking**: Real-time updates via Firestore
- **Error Handling**: Comprehensive error logging and recovery
- **Cost Optimization**: Pay only for actual processing time

### Job Lifecycle

- **Creation**: Triggered when repository size > 100 files
- **Execution**: Processes all files with progress updates
- **Completion**: Updates repository status and metadata
- **Cleanup**: Automatic resource cleanup after completion

## Security Considerations

### Authentication & Authorization

- Service account-based authentication
- IAM roles for least privilege access
- Repository access controls
- Audit logging for all operations

### Data Privacy

- No source code content stored
- Only metadata and structural information indexed
- Encrypted storage at rest
- Secure transmission of all data

## Monitoring & Observability

### Metrics

- Processing latency per file
- Queue depth and processing rates
- Error rates and failure patterns
- Lock acquisition times

### Logging

- Structured logging for all operations
- Request tracing across components
- Error details with context
- Performance metrics logging

### Alerting

- High error rates
- Queue depth thresholds
- Processing latency spikes
- Lock acquisition failures

## Performance Considerations

### Scalability

- Horizontal scaling based on queue depth
- Efficient file processing algorithms
- Optimized Firestore queries
- Connection pooling and resource management

### Optimization

- Batch operations where possible
- Efficient lock management
- Smart retry strategies
- Resource cleanup and garbage collection

## Python/FastAPI Implementation

### Framework Architecture

- **FastAPI**: Modern, fast web framework for building APIs
  - Built on top of Starlette and Pydantic
  - Automatic request/response validation
  - OpenAPI documentation generation
  - WebSocket support for real-time updates

### Core Dependencies

- **FastAPI**: Web framework and API development
- **Pydantic**: Data validation and serialization
- **Uvicorn**: ASGI server for production deployment
- **Tree-sitter**: Language parsing and AST generation
- **Google Cloud**: Firestore, Cloud Tasks, Cloud Run integration
- **asyncio**: Asynchronous programming support

### Project Structure

```
src/
├── main.py                 # FastAPI application entry point
├── api/                    # API route definitions
│   ├── __init__.py
│   ├── files.py           # File processing endpoints
│   ├── repositories.py    # Repository management
│   └── health.py          # Health check endpoints
├── core/                   # Core business logic
│   ├── __init__.py
│   ├── parser.py          # Code parsing engine
│   ├── indexer.py         # Index management
│   └── locks.py           # Distributed locking
├── models/                 # Pydantic data models
│   ├── __init__.py
│   ├── file_index.py      # File index schemas
│   └── repository.py      # Repository schemas
├── services/               # External service integrations
│   ├── __init__.py
│   ├── firestore.py       # Firestore operations
│   ├── cloud_run_jobs.py  # Cloud Run Jobs management
│   └── git.py             # Git operations
└── utils/                  # Utility functions
    ├── __init__.py
    ├── hashing.py         # File hash utilities
    └── logging.py         # Logging configuration
```

### Async Processing Patterns

- **File Processing**: Concurrent processing using asyncio
- **Lock Management**: Async Firestore transactions
- **Job Management**: Async Cloud Run Jobs integration
- **Error Handling**: Comprehensive async error handling

## Deployment & Operations

### Environment Configuration

- Environment-specific settings
- Feature flags for gradual rollouts
- Configuration management
- Secrets management

### Deployment Strategy

- Blue-green deployments
- Rolling updates with health checks
- Automatic rollback on failures
- Zero-downtime deployments

### Backup & Recovery

- Regular data backups
- Disaster recovery procedures
- Data retention policies
- Recovery time objectives

## Future Enhancements

### Planned Features

- Support for additional programming languages
- Advanced type inference algorithms
- Dependency graph visualization
- Integration with IDEs and editors
- **Python Ecosystem Integration**:
  - Poetry for dependency management
  - Pre-commit hooks for code quality
  - Integration with popular Python IDEs (PyCharm, VS Code)
  - Support for Jupyter notebooks and data science workflows

### Scalability Improvements

- Multi-region deployment
- Advanced caching strategies
- Machine learning for type inference
- Real-time collaboration features
- **Python Performance Optimizations**:
  - Cython integration for performance-critical sections
  - Async/await patterns for I/O-bound operations
  - Memory profiling and optimization
  - Integration with Python performance monitoring tools

## Conclusion

The Serverless Code Index System provides a robust, scalable solution for tracking code dependencies and variable usage across git repositories. Through careful design of distributed locking, incremental processing, and atomic operations, the system ensures reliable and efficient processing while maintaining data consistency and preventing race conditions.

The architecture leverages modern cloud-native technologies to provide a maintainable and extensible foundation for code analysis and dependency tracking, enabling developers to better understand and manage their codebases.
