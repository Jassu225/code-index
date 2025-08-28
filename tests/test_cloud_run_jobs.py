"""
Tests for Cloud Run Jobs integration.
"""

import pytest
from unittest.mock import Mock, patch
import hashlib

from src.core.cloud_run_jobs import CloudRunJobsService


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
            mock_config = Mock()
            mock_config.gcp_project_id = "icode-94891"
            mock_config.cloud_run_jobs_location = "europe-west4"
            mock_config.cloud_run_jobs_timeout = 3600
            mock_config.cloud_run_jobs_cpu = 2
            mock_config.cloud_run_jobs_memory = "4Gi"
            mock_settings.return_value = mock_config
            return CloudRunJobsService()
    
    def test_jobs_service_initialization(self, jobs_service):
        """Test jobs service initialization."""
        assert jobs_service.client is not None
        assert jobs_service.settings is not None
    
    def test_get_job_name(self, jobs_service):
        """Test job name generation."""
        repo_url = "https://github.com/test/repo"
        job_name = jobs_service._get_job_name(repo_url)
        
        # Calculate expected hash
        repo_hash = hashlib.md5(repo_url.encode()).hexdigest()[:8]
        expected = f"projects/icode-94891/locations/europe-west4/jobs/code-index-{repo_hash}"
        
        assert job_name == expected
    
    def test_get_execution_name(self, jobs_service):
        """Test execution name generation."""
        repo_url = "https://github.com/test/repo"
        execution_name = jobs_service._get_execution_name(repo_url, "exec-123")
        
        # Calculate expected hash
        repo_hash = hashlib.md5(repo_url.encode()).hexdigest()[:8]
        expected = f"projects/icode-94891/locations/europe-west4/jobs/code-index-{repo_hash}/executions/exec-123"
        
        assert execution_name == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
