# Serverless Code Index System

A serverless backend that tracks exported/imported variables across files in git repositories. The system provides an API for indexing repositories and searching through exported symbols.

The idea is to create a system which

- sets up github workflows that calls /commit/parse api on push to a branch
- uses repositories/index to clone the repo, create repo info in code_index_repositories and each file info (without processing) in code_index_file_indexes and then send batch requests (of 400 files, configurable) to /files/index which will parse the files and update file info. This is one-time.
- When new commits arrive to /commit/parse, we get the modified files info, store in firestore, then we send request to /files/process. If initial indexing is still going on, we skip those files (in initial indexing) that were already modified in the new commits.

Couldn't complete this system as I had other commitments. For now, the sytem can clone the real repo (tested only with Typescript), index the files' imports and exports.

> Important: Just storing export variables isn't enough, we have to store additional info like function signature (arguments), class signature (public methods & data members), object signure (not yet implemented) in order to catch issues better and with high confidentce. So tried to implement this too.

## Features

- **Repository Indexing**: Index Git repositories and track exported/imported variables
- **Multi-language Support**: Currently supports Python and TypeScript
- **Firestore Integration**: Uses Google Cloud Firestore for data storage
- **RESTful API**: FastAPI-based API for repository management
- **Live Testing**: Test with real repositories and Firestore emulator

## Prerequisites

- Python 3.11+
- Node.js 18+ (for Firestore emulator)
- Git
- Google Cloud SDK (optional, for production deployment)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Jassu225/code-index
cd code-index
```

### 2. Install Python Dependencies

This project uses `uv` for Python package management:

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### 3. Install Node.js Dependencies (for Firestore emulator)

```bash
npm install -g firebase-tools
```

### 4. Google Cloud CLI Setup

Install and authenticate with Google Cloud CLI:

```bash
# Install gcloud CLI (if not already installed)
# macOS with Homebrew:
brew install google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install

# Authenticate with your Google Cloud account
gcloud auth login

# Set your project (replace with your actual project ID)
gcloud config set project your-project-id

# Verify authentication
gcloud auth list
```

**Note**: For local development with the Firestore emulator, gcloud authentication is optional. However, it's required for:

- Production deployments
- Using real Google Cloud services

## Environment Setup

### 1. Create Environment Files

Copy the example environment file and create your test environment:

```bash
cp env.example .env.test
```

### 2. Configure .env.test

Edit `.env.test` with your configuration:

```bash
# GCP Project Configuration
GCP_PROJECT_ID=your-project-id #prefix with demo- for easier use, the project need not exist in gcp
GCP_REGION=europe-west4

# Firestore Configuration
FIRESTORE_COLLECTION_PREFIX=code_index
FIRESTORE_DATABASE_ID=code-index

# Cloud Run Jobs Configuration
CLOUD_RUN_JOBS_LOCATION=europe-west4
CLOUD_RUN_JOBS_TIMEOUT=86400
CLOUD_RUN_JOBS_CPU=2
CLOUD_RUN_JOBS_MEMORY=4Gi

# Authentication
USE_APPLICATION_DEFAULT_CREDENTIALS=true

# Processing Configuration
MAX_CONCURRENT_FILES=10
FILE_PROCESSING_TIMEOUT=300
FIRESTORE_BATCH_SIZE=500

# API Configuration
DEBUG=true
CORS_ORIGINS=["*"]
API_RATE_LIMIT=1000
```

### 3. VS Code Configuration (Optional)

If using VS Code, the debug configuration is already set up to use `.env.test`. The launch.json includes:

```json
{
  "name": "FastAPI Debug (Module)",
  "env": {
    "PYTHONPATH": "${workspaceFolder}",
    "ENV_FILE": ".env.test"
  }
}
```

## Running the System

### 1. Start Firestore Emulator

Start the Firestore emulator on port 8080:

```bash
firebase emulators:start --only firestore --project <your-project-id (must be same as the above one)>
```

The emulator will be available at `localhost:8080`.

### 2. Run the API Server

#### Option A: Direct Execution

```bash
uv run python run_server.py
```

#### Option B: Module Execution (recommended)

```bash
uv run python -m src
```

#### Option C: VS Code Debug

Use the "FastAPI Debug (Module)" configuration in VS Code.

The server will start on `http://localhost:8000` with auto-reload enabled.

### 3. Verify Server Status

Check the health endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "timestamp": "2025-08-28T21:30:00Z",
  "version": "0.1.0"
}
```

## Testing

### 1. Run Live Repository Tests

Test with a real repository:

```bash
uv run python tests/test_live_repository.py
```

### 2. Test API Endpoints

#### List Repositories

```bash
curl http://localhost:8000/repositories
```

#### Index a Repository

```bash
curl -X POST "http://localhost:8000/repositories/index" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/username/repo-name",
    "branch": "main"
  }'
```

#### Get Repository Files

```bash
curl "http://localhost:8000/repositories/{repo_id}/files"
```

#### Search Exports

```bash
curl "http://localhost:8000/repositories/{repo_id}/search?query=functionName"
```

## Project Structure

```
src/
├── api/                    # FastAPI endpoints
│   ├── files.py           # File operations
│   ├── health.py          # Health check
│   └── repositories.py    # Repository management
├── core/                  # Core business logic
│   ├── config.py          # Configuration management
│   ├── database.py        # Firestore operations
│   ├── indexer.py         # Repository indexing
│   ├── parser/            # Language parsers
│   └── repository_indexer.py
├── jobs/                  # Background job processing (not used and not tested)
└── models/                # Data models

tests/                     # Test files
scripts/                   # Utility scripts (Ignore)
```

## Configuration

### Environment Variables

| Variable                      | Description                       | Default       |
| ----------------------------- | --------------------------------- | ------------- |
| `GCP_PROJECT_ID`              | Google Cloud Project ID           | `icode-94891` |
| `FIRESTORE_COLLECTION_PREFIX` | Collection prefix                 | `code_index`  |
| `FIRESTORE_DATABASE_ID`       | Firestore database ID             | `code-index`  |
| `DEBUG`                       | Enable debug mode                 | `false`       |
| `MAX_CONCURRENT_FILES`        | Max files to process concurrently | `10`          |

### Collection Prefix

The system uses collection prefixes to organize data:

- Collections: `{prefix}_repositories`, `{prefix}_file_indexes`
- Example: `code_index_repositories`, `code_index_file_indexes`

## Troubleshooting

### Common Issues

1. **Environment Variables Not Loading**

   - Ensure `.env.test` exists and has correct values
   - Check that `ENV_FILE=.env.test` is set in debug configurations
   - Verify no `.env` file is interfering

2. **Firestore Connection Issues**

   - Ensure emulator is running on port 8080
   - Check `FIRESTORE_EMULATOR_HOST` environment variable
   - Verify project ID matches configuration

3. **Collection Prefix Not Working**

   - Check `FIRESTORE_COLLECTION_PREFIX` in `.env.test`
   - Verify collections are created with correct names
   - Check database logs for collection paths

4. **Server Won't Start**
   - Check Python version (requires 3.11+)
   - Verify all dependencies are installed with `uv sync`
   - Check configuration file syntax
