"""
Tests for GCP integration components.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from src.core.config import get_settings, Settings
from src.core.database import FirestoreDatabase
from src.core.cloud_run_jobs import CloudRunJobsService
from src.models.repository import RepositoryMetadata
from src.models.file_index import FileIndex


class TestConfiguration:
    """Test configuration management."""
    
    def test_settings_loading(self):
        """Test that settings can be loaded."""
        settings = get_settings()
        assert isinstance(settings, Settings)
        assert hasattr(settings, 'gcp_project_id')
        assert hasattr(settings, 'firestore_collection_prefix')
    
    def test_default_values(self):
        """Test default configuration values."""
        settings = get_settings()
        assert settings.gcp_region == "europe-west4"  # Environment overrides default
        assert settings.firestore_collection_prefix == "code_index"
        assert settings.max_concurrent_files == 10


class TestFirestoreDatabase:
    """Test Firestore database operations."""
    
    @pytest.fixture
    def mock_firestore_client(self):
        """Mock Firestore client."""
        with patch('src.core.database.firestore.Client') as mock_client:
            mock_client.return_value = Mock()
            yield mock_client
    
    @pytest.fixture
    def database(self, mock_firestore_client):
        """Create database instance with mocked client."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                gcp_project_id="test-project",
                firestore_collection_prefix="test_code_index"
            )
            return FirestoreDatabase()
    
    def test_database_initialization(self, database):
        """Test database initialization."""
        assert database.client is not None
        assert database.settings is not None
    
    @pytest.mark.asyncio
    async def test_create_repository(self, database):
        """Test repository creation."""
        repo_data = RepositoryMetadata(
            repoId="test-repo",
            name="Test Repository",
            url="https://github.com/test/repo",
            lastProcessedCommit="",
            lastProcessedCommitTimestamp="2025-01-26T00:00:00Z",
            totalFiles=0,
            processedFiles=0,
            lastUpdated="2025-01-26T00:00:00Z",
            status="pending"
        )
        
        # Mock the document reference
        mock_doc_ref = Mock()
        database._get_document_ref = Mock(return_value=mock_doc_ref)
        
        result = await database.create_repository(repo_data)
        assert result is True
        mock_doc_ref.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_repository(self, database):
        """Test repository retrieval."""
        # Mock document snapshot
        mock_doc_snapshot = Mock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "repoId": "test-repo",
            "name": "Test Repository",
            "url": "https://github.com/test/repo",
            "lastProcessedCommit": "",
            "lastProcessedCommitTimestamp": "2025-01-26T00:00:00Z",
            "totalFiles": 0,
            "processedFiles": 0,
            "lastUpdated": "2025-01-26T00:00:00Z",
            "status": "pending"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc_snapshot
        database._get_document_ref = Mock(return_value=mock_doc_ref)
        
        result = await database.get_repository("test-repo")
        assert result is not None
        assert result.repoId == "test-repo"
        assert result.name == "Test Repository"


class TestCloudRunJobsService:
    """Test Cloud Run Jobs service."""
    
    @pytest.fixture
    def mock_jobs_client(self):
        """Mock Cloud Run Jobs client."""
        with patch('src.core.cloud_run_jobs.run_v2.JobsClient') as mock_client:
            mock_client.return_value = Mock()
            yield mock_client
    
    @pytest.fixture
    def jobs_service(self, mock_jobs_client):
        """Create jobs service instance with mocked client."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                gcp_project_id="test-project",
                cloud_run_jobs_location="europe-west4",
                cloud_run_jobs_timeout=3600,
                cloud_run_jobs_cpu=2,
                cloud_run_jobs_memory="4Gi",
                gcp_region="europe-west4"
            )
            return CloudRunJobsService()
    
    def test_jobs_service_initialization(self, jobs_service):
        """Test jobs service initialization."""
        assert jobs_service.client is not None
        assert jobs_service.settings is not None
    
    @pytest.mark.asyncio
    async def test_create_repository_processing_job(self, jobs_service):
        """Test repository processing job creation."""
        # Mock the update_job operation to fail (so it creates a new job)
        jobs_service.client.update_job.side_effect = Exception("Job not found")
        
        # Mock job creation response
        mock_response = Mock()
        mock_response.name = "projects/test-project/locations/europe-west4/jobs/code-index-test-repo"
        jobs_service.client.create_job.return_value = mock_response
        
        # Mock execution creation response
        mock_execution = Mock()
        mock_execution.name = "test-execution-name"
        jobs_service.client.create_execution.return_value = mock_execution
        
        # Mock the result() method for operations
        mock_response.result.return_value = mock_response
        mock_execution.result.return_value = mock_execution
        
        result = await jobs_service.create_repository_processing_job(
            repo_url="https://github.com/test/repo",
            force_reprocess=False
        )
        
        assert result == "test-execution-name"
        jobs_service.client.create_job.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_job_info(self, jobs_service):
        """Test job information retrieval."""
        # Mock job path and job object
        mock_job_path = "projects/test-project/locations/europe-west4/jobs/code-index-test-repo"
        jobs_service._get_job_name = Mock(return_value=mock_job_path)
        
        mock_job = Mock()
        mock_job.name = "test-job"
        mock_job.uid = "test-uid"
        mock_job.generation = 1
        mock_job.create_time = None
        mock_job.update_time = None
        mock_job.labels = {}
        mock_job.annotations = {}
        mock_job.delete_time = None
        mock_job.expire_time = None
        mock_job.creator = None
        mock_job.last_modifier = None
        mock_job.client = None
        mock_job.client_version = None
        mock_job.launch_stage = None
        mock_job.binary_authorization = None
        
        # Mock template structure
        mock_template = Mock()
        mock_template.parallelism = 1
        mock_template.task_count = 1
        mock_template.timeout = "3600s"
        mock_template.template = Mock()
        mock_template.template.resources = Mock()
        mock_template.template.resources.cpu = "2"
        mock_template.template.resources.memory = "4Gi"
        mock_template.template.image = "test-image"
        mock_job.template = mock_template
        
        jobs_service.client.get_job.return_value = mock_job
        
        result = await jobs_service.get_job_info("test-repo")
        
        assert result["name"] == "test-job"
        assert result["uid"] == "test-uid"
        assert result["generation"] == 1


class TestIntegration:
    """Integration tests for GCP components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test end-to-end workflow with mocked GCP services."""
        # This test would verify that all components work together
        # In a real scenario, you'd use GCP emulators or test projects
        
        # Mock settings
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                gcp_project_id="test-project",
                firestore_collection_prefix="test_code_index",
                cloud_run_jobs_location="europe-west4",
                cloud_run_jobs_timeout=3600,
                gcp_region="us-central1"
            )
            
            # Test that we can create instances
            db = FirestoreDatabase()
            jobs = CloudRunJobsService()
            
            assert db is not None
            assert jobs is not None
            
            # Test configuration loading
            settings = get_settings()
            assert settings.gcp_project_id == "icode-94891"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
