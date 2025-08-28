# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Install dependencies using uv (preferred) or poetry
uv sync
# or
poetry install

# Set up environment variables
cp env.example .env
# Edit .env with your GCP project details
```

### Local Development
```bash
# Run the application locally
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
# or
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8080

# Access API at http://localhost:8080/docs (Swagger UI)
```

### Testing
```bash
# Run all tests
poetry run pytest
# or
uv run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html
# or 
uv run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/test_models.py
# or
uv run pytest tests/test_models.py
```

### Code Quality
```bash
# Format code with Black
poetry run black src/
# or
uv run black src/

# Sort imports with isort
poetry run isort src/
# or
uv run isort src/

# Type checking with mypy
poetry run mypy src/
# or
uv run mypy src/

# Linting with flake8
poetry run flake8 src/
# or
uv run flake8 src/
```

### Deployment
```bash
# Deploy to GCP (requires gcloud CLI setup)
./deploy.sh

# Deploy to specific project and region
./deploy.sh your-project-id us-central1
```

## Architecture Overview

This is a **Serverless Code Index System** that tracks exported/imported variables across files in git repositories using **FastAPI** (Python) and **Google Cloud** services.

### Core Architecture
- **FastAPI**: Modern Python web framework for high-performance async API
- **Cloud Firestore**: Document database for storing file indexes and repository metadata  
- **Cloud Run**: Serverless compute platform for processing files
- **Cloud Run Jobs**: Batch processing for large repositories
- **Tree-sitter**: Multi-language AST parsing (TypeScript, JavaScript, Python, Go, Java, C#)

### Key Components

**API Layer** (`src/api/`):
- `repositories.py`: Repository management endpoints
- `files.py`: File processing endpoints
- `health.py`: Health checks and status endpoints

**Core Business Logic** (`src/core/`):
- `parser.py`: Multi-language code parsing engine using Tree-sitter
- `database.py`: Firestore database operations layer
- `indexer.py`: File indexing and processing logic
- `repository_indexer.py`: Repository-level processing coordination
- `cloud_run_jobs.py`: Cloud Run Jobs integration for batch processing
- `locks.py`: Distributed file-level locking using Firestore transactions
- `config.py`: Configuration management with environment variables

**Data Models** (`src/models/`):
- `file_index.py`: Complex data structures for exports/imports with full type information
- `repository.py`: Repository metadata and processing status

### Processing Flow
1. **Two-tier processing**: Small repos (<100 files) processed directly, large repos use Cloud Run Jobs
2. **File-level distributed locking**: Prevents race conditions using Firestore transactions
3. **Two-layer deduplication**: Content hash + file-level timestamp validation  
4. **Comprehensive type extraction**: Function signatures, class info, interface details
5. **Atomic operations**: All database updates use Firestore transactions

### Data Structure Philosophy
- **Exports contain full type information**: Complete function signatures, class definitions, interface specifications
- **Imports are minimal**: Only name, source, and line number (types come from exports)
- **File-level timestamp validation**: Prevents out-of-order commit processing
- **Language-specific parsing**: TypeScript/JavaScript (comprehensive), Python (comprehensive), others (basic)

### Configuration
Key environment variables in `.env`:
- `GCP_PROJECT_ID`: Your Google Cloud project
- `FIRESTORE_DATABASE_ID`: Firestore database (default: "(default)")
- `CLOUD_RUN_JOBS_LOCATION`: Location for batch processing jobs
- `MAX_CONCURRENT_FILES`: Concurrent file processing limit
- `USE_APPLICATION_DEFAULT_CREDENTIALS`: Use ADC vs service account key

### Development Notes
- Uses `uv` for fast Python package management (preferred) with `poetry` as fallback
- Async/await patterns throughout for high-performance concurrent processing
- Comprehensive error handling with structured logging
- Tree-sitter parsers for accurate AST-based code analysis
- File-level locking prevents race conditions in distributed processing
- Supports incremental processing - only processes changed files

### Testing Strategy
- Unit tests for individual components
- Integration tests for GCP services  
- E2E tests for complete workflows
- Performance tests for large repositories
- Test markers: `unit`, `integration`, `e2e`, `slow`