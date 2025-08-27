# Serverless Code Index System

A serverless backend that tracks exported/imported variables across files in git repositories. The system processes commits incrementally and maintains an up-to-date index of all public/private variables and their types.

## 🏗️ Architecture

- **Compute**: Cloud Run (better than Cloud Functions for longer execution times)
- **Queue**: Cloud Run Jobs (batch processing for large repositories)
- **Storage**: Cloud Firestore for index data
- **Locking**: Firestore transactions for distributed file-level locks
- **Triggers**: Cloud Build triggers or GitHub webhooks for git events
- **Parsing**: Tree-sitter parsers for multi-language AST analysis
- **Backend**: FastAPI (Python) for high-performance async processing

## ✨ Features

- **Two-Layer Deduplication**: Content hash + file-level timestamp validation
- **Distributed Locking**: File-level locks prevent race conditions
- **Multi-Language Support**: TypeScript, JavaScript, Python, Go, Java, C#
- **Comprehensive Function Signatures**: Parameters, types, order, overloads
- **Incremental Processing**: Only process changed files
- **Async Processing**: High-performance concurrent file processing
- **Real-time Indexing**: Live updates as code changes

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- Google Cloud SDK (for deployment)
- Docker (for containerization)

### Local Development

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd code-index
   ```

2. **Install dependencies**

   ```bash
   poetry install
   ```

3. **Set up environment variables**

   ```bash
   cp env.example .env
   # Edit .env with your GCP project details
   ```

4. **Set up GCP authentication**

   ```bash
   # Option 1: Use Application Default Credentials (recommended)
   gcloud auth application-default login

   # Option 2: Use service account key
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account.json"
   ```

5. **Run the application locally**

   ```bash
   poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
   ```

6. **Access the API**
   - API Documentation: http://localhost:8080/docs
   - Health Check: http://localhost:8080/health
   - Root Endpoint: http://localhost:8080/
   - System Status: http://localhost:8080/status

## 🚀 GCP Deployment

### Automated Deployment

Use the provided deployment script for quick setup:

```bash
# Deploy to your current GCP project
./deploy.sh

# Deploy to a specific project and region
./deploy.sh your-project-id us-central1
```

The script will:

- Enable required GCP APIs
- Create Firestore database
- Set up Cloud Run Jobs service account
- Build and deploy to Cloud Run
- Configure service accounts and permissions

### Manual Deployment

1. **Enable GCP APIs**

   ```bash
   gcloud services enable \
       cloudbuild.googleapis.com \
       run.googleapis.com \
       firestore.googleapis.com \
       cloudtasks.googleapis.com
   ```

2. **Create Firestore database**

   ```bash
   gcloud firestore databases create --region=us-central1
   ```

3. **Create Cloud Run Jobs service account**

   ```bash
   gcloud iam service-accounts create code-index-jobs \
       --display-name="Code Index System Cloud Run Jobs Service Account" \
       --description="Service account for Cloud Run Jobs processing"
   ```

4. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy code-index-system \
       --source . \
       --platform managed \
       --region us-central1 \
       --allow-unauthenticated \
       --memory 2Gi \
       --cpu 2 \
       --timeout 300
   ```

### Service Account Setup

For production deployments, create a dedicated service account:

```bash
# Create service account
gcloud iam service-accounts create code-index-sa \
    --display-name="Code Index System Service Account"

# Grant necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:code-index-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:code-index-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.invoker"

# Download service account key
gcloud iam service-accounts keys create key.json \
    --iam-account=code-index-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

## 📁 Project Structure

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
│   ├── config.py          # Configuration management
│   ├── database.py        # Firestore database layer
│   ├── cloud_run_jobs.py  # Cloud Run Jobs service
│   ├── parser.py          # Code parsing engine
│   ├── indexer.py         # Index management
│   └── locks.py           # Distributed locking
├── models/                 # Pydantic data models
│   ├── __init__.py
│   ├── file_index.py      # File index schemas
│   └── repository.py      # Repository schemas
└── tests/                  # Test suite
    ├── __init__.py
    └── test_models.py     # Model tests
```

## 🧪 Testing

### Local Testing with Cloud Run Jobs

You can test the Cloud Run Jobs locally using `gcloud beta code dev`:

```bash
# Test the main service locally
gcloud beta code dev --dockerfile=Dockerfile --application-default-credential

# Test with custom configuration
gcloud beta code dev --dockerfile=Dockerfile --service-account=your-service-account@your-project.iam.gserviceaccount.com
```

The service will be available at http://localhost:8080 with the configuration from `service.dev.yaml`.

### Local Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/test_models.py
```

### Testing GCP Integration

1. **Set up test environment**

   ```bash
   # Use a test GCP project or local emulator
   export GCP_PROJECT_ID="your-test-project-id"
   ```

2. **Test Firestore operations**

   ```bash
   # Test database operations
   poetry run python -c "
   from src.core.database import get_database
   import asyncio

   async def test_db():
       db = get_database()
       print('Database initialized successfully')

   asyncio.run(test_db())
   "
   ```

3. **Test Cloud Run Jobs**

   ```bash
   # Test task creation
   poetry run python -c "
   from src.core.tasks import get_tasks_service
   import asyncio

   async def test_tasks():
       tasks = get_tasks_service()
       print('Cloud Run Jobs service initialized successfully')

   asyncio.run(test_tasks())
   "
   ```

## 🔧 Configuration

### Environment Variables

The system uses environment variables for configuration. Copy `env.example` to `.env` and fill in your values:

| Variable                              | Description                       | Default                 | Required |
| ------------------------------------- | --------------------------------- | ----------------------- | -------- |
| `GCP_PROJECT_ID`                      | Your Google Cloud Project ID      | -                       | ✅       |
| `GCP_REGION`                          | GCP region for services           | `us-central1`           | ❌       |
| `FIRESTORE_COLLECTION_PREFIX`         | Prefix for Firestore collections  | `code_index`            | ❌       |
| `FIRESTORE_DATABASE_ID`               | Firestore database ID (optional)  | -                       | ❌       |
| `CLOUD_RUN_JOBS_LOCATION`             | Cloud Run Jobs location           | `europe-west4`          | ❌       |
| `CLOUD_RUN_JOBS_TIMEOUT`              | Cloud Run Jobs timeout (seconds) | `86400`                | ❌       |
| `USE_APPLICATION_DEFAULT_CREDENTIALS` | Use ADC for authentication        | `true`                  | ❌       |
| `GOOGLE_APPLICATION_CREDENTIALS`      | Path to service account JSON      | -                       | ❌       |
| `MAX_CONCURRENT_FILES`                | Max concurrent file processing    | `10`                    | ❌       |
| `FILE_PROCESSING_TIMEOUT`             | File processing timeout (seconds) | `300`                   | ❌       |
| `FIRESTORE_BATCH_SIZE`                | Firestore batch write size        | `500`                   | ❌       |
| `DEBUG`                               | Enable debug mode                 | `false`                 | ❌       |
| `CORS_ORIGINS`                        | CORS allowed origins              | `["*"]`                 | ❌       |
| `API_RATE_LIMIT`                      | API rate limit (req/min)          | `1000`                  | ❌       |
| `FIRESTORE_PROJECT_ID`                | Google Cloud project ID           | Required                |
| `CLOUD_RUN_JOBS_LOCATION`             | Cloud Run Jobs location           | Required                |
| `PORT`                                | Application port                  | 8080                    |
| `LOG_LEVEL`                           | Logging level                     | INFO                    |

### Google Cloud Services

1. **Enable required APIs**

   ```bash
   gcloud services enable \
     firestore.googleapis.com \
     cloudtasks.googleapis.com \
     run.googleapis.com \
     cloudbuild.googleapis.com
   ```

2. **Create Firestore database**

   ```bash
   gcloud firestore databases create --project=your-project-id
   ```

3. **Create Cloud Run Jobs service account**
   ```bash
   gcloud iam service-accounts create code-index-jobs \
     --display-name="Code Index System Cloud Run Jobs Service Account" \
     --description="Service account for Cloud Run Jobs processing"
   ```

## 🚀 Deployment

### Cloud Run Deployment

1. **Build and push Docker image**

   ```bash
   gcloud builds submit --tag gcr.io/your-project-id/code-index-system
   ```

2. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy code-index-system \
     --image gcr.io/your-project-id/code-index-system \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8080 \
     --memory 4Gi \
     --cpu 2 \
     --max-instances 100
   ```

### GitHub Actions CI/CD

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: google-github-actions/setup-gcloud@v1
      - name: Deploy to Cloud Run
        run: |
          gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/code-index-system
          gcloud run deploy code-index-system \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/code-index-system \
            --platform managed \
            --region us-central1
```

## 📊 API Endpoints

### Health & Status

- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with dependencies
- `GET /health/ready` - Readiness check for Kubernetes
- `GET /health/live` - Liveness check for Kubernetes
- `GET /status` - System status

### Repository Management

- `POST /repositories` - Create new repository
- `GET /repositories` - List all repositories
- `GET /repositories/{repo_id}` - Get repository details
- `PUT /repositories/{repo_id}` - Update repository
- `DELETE /repositories/{repo_id}` - Delete repository
- `POST /repositories/{repo_id}/process` - Trigger processing

### File Processing

- `POST /files/process` - Process a file for indexing
- `GET /files/{repo_id}/{file_path}` - Get file index
- `GET /files/{repo_id}` - List repository files
- `DELETE /files/{repo_id}/{file_path}` - Delete file index

## 🔒 Security

- **Authentication**: Service account-based authentication
- **Authorization**: IAM roles for least privilege access
- **Data Privacy**: No source code content stored, only metadata
- **Encryption**: Encrypted storage at rest and in transit

## 📈 Monitoring & Observability

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

## 🧪 Testing

### Run Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test categories
poetry run pytest -m unit
poetry run pytest -m integration
poetry run pytest -m e2e
```

### Test Structure

```
tests/
├── unit/                    # Unit tests
├── integration/             # Integration tests
├── e2e/                    # End-to-end tests
├── performance/             # Performance tests
└── fixtures/                # Test data and fixtures
```

## 🔄 Development Workflow

1. **Create feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and test**

   ```bash
   poetry run pytest
   poetry run black src/
   poetry run isort src/
   poetry run mypy src/
   ```

3. **Commit changes**

   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

4. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub
   ```

## 📚 Documentation

- [API Documentation](http://localhost:8080/docs) - Interactive API docs
- [Technical Specification](specs/spec.md) - Detailed system design
- [Linear Project](https://linear.app/cloud-brain/project/serverless-code-index-system-987c28ba3093) - Issue tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: Create an issue on GitHub
- **Discussions**: Use GitHub Discussions
- **Linear**: Track development progress in Linear

## 🗺️ Roadmap

- [ ] Support for additional programming languages
- [ ] Advanced type inference algorithms
- [ ] Dependency graph visualization
- [ ] Integration with IDEs and editors
- [ ] Real-time collaboration features
- [ ] Machine learning for type inference
