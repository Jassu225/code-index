"""
Google Cloud Run Jobs service for batch processing large repositories.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from google.cloud import run_v2
from google.cloud.run_v2 import Job, Execution, TaskTemplate, Container

from .config import get_settings

logger = logging.getLogger(__name__)


class CloudRunJobsService:
    """Google Cloud Run Jobs service for batch repository processing."""
    
    def __init__(self):
        """Initialize Cloud Run Jobs client."""
        self.settings = get_settings()
        self.client: Optional[run_v2.JobsClient] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Cloud Run Jobs client."""
        try:
            self.client = run_v2.JobsClient()
            logger.info("Cloud Run Jobs client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Cloud Run Jobs client: {e}")
            raise
    
    def _get_job_name(self, repo_id: str) -> str:
        """Get the full job name for Cloud Run Jobs."""
        settings = get_settings()
        return f"projects/{settings.gcp_project_id}/locations/{settings.cloud_run_jobs_location}/jobs/code-index-{repo_id}"
    
    def _get_execution_name(self, repo_id: str, execution_id: str) -> str:
        """Get the full execution name."""
        return f"{self._get_job_name(repo_id)}/executions/{execution_id}"
    
    async def create_repository_processing_job(
        self, 
        repo_id: str, 
        repo_url: str,
        force_reprocess: bool = False
    ) -> Optional[str]:
        """Create a Cloud Run Job for processing a large repository."""
        try:
            if not self.client:
                raise RuntimeError("Cloud Run Jobs client not initialized")
            
            # Check if job already exists
            job_name = self._get_job_name(repo_id)
            
                        # Create a simple job configuration
            job = Job()
            job.name = job_name
            
            # Create or update the job
            try:
                operation = self.client.update_job(job=job)
                result = operation.result()
                logger.info(f"Updated job: {result.name}")
            except Exception:
                # Job doesn't exist, create it
                operation = self.client.create_job(
                    parent=f"projects/{self.settings.gcp_project_id}/locations/{self.settings.cloud_run_jobs_location}",
                    job=job,
                    job_id=f"code-index-{repo_id}"
                )
                result = operation.result()
                logger.info(f"Created job: {result.name}")
            
            # Execute the job
            execution = Execution()
            execution.name = f"{result.name}/executions/latest"
            
            operation = self.client.create_execution(
                parent=result.name,
                execution=execution
            )
            result_execution = operation.result()
            
            logger.info(f"Created execution for repository {repo_id}: {result_execution.name}")
            return result_execution.name
            
        except Exception as e:
            logger.error(f"Failed to create processing job for repository {repo_id}: {e}")
            return None
    
    async def get_job_status(self, repo_id: str, execution_id: str) -> Dict[str, Any]:
        """Get the status of a Cloud Run Job execution."""
        try:
            if not self.client:
                raise RuntimeError("Cloud Run Jobs client not initialized")
            
            execution_name = self._get_execution_name(repo_id, execution_id)
            execution = self.client.get_execution(name=execution_name)
            
            return {
                "name": execution.name,
                "state": execution.state.name,
                "create_time": execution.create_time.ToDatetime().isoformat() + "Z" if execution.create_time else None,
                "completion_time": execution.completion_time.ToDatetime().isoformat() + "Z" if execution.completion_time else None,
                "task_count": execution.task_count,
                "parallelism": execution.parallelism,
                "succeeded_count": execution.succeeded_count,
                "failed_count": execution.failed_count,
                "cancelled_count": execution.cancelled_count,
                "retried_count": execution.retried_count,
                "log_uri": execution.log_uri,
                "satisfies_pzs": execution.satisfies_pzs
            }
            
        except Exception as e:
            logger.error(f"Failed to get job status for {repo_id}: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    async def list_job_executions(self, repo_id: str) -> list[Dict[str, Any]]:
        """List all executions for a specific job."""
        try:
            if not self.client:
                raise RuntimeError("Cloud Run Jobs client not initialized")
            
            job_name = self._get_job_name(repo_id)
            executions = self.client.list_executions(parent=job_name)
            
            execution_list = []
            for execution in executions:
                execution_info = {
                    "name": execution.name,
                    "state": execution.state.name,
                    "create_time": execution.create_time.ToDatetime().isoformat() + "Z" if execution.create_time else None,
                    "completion_time": execution.completion_time.ToDatetime().isoformat() + "Z" if execution.completion_time else None,
                    "succeeded_count": execution.succeeded_count,
                    "failed_count": execution.failed_count
                }
                execution_list.append(execution_info)
            
            return execution_list
            
        except Exception as e:
            logger.error(f"Failed to list job executions for {repo_id}: {e}")
            return []
    
    async def cancel_job_execution(self, repo_id: str, execution_id: str) -> bool:
        """Cancel a running job execution."""
        try:
            if not self.client:
                raise RuntimeError("Cloud Run Jobs client not initialized")
            
            execution_name = self._get_execution_name(repo_id, execution_id)
            operation = self.client.cancel_execution(name=execution_name)
            operation.result()
            
            logger.info(f"Cancelled execution for repository {repo_id}: {execution_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel execution for {repo_id}: {e}")
            return False
    
    async def delete_job(self, repo_id: str) -> bool:
        """Delete a Cloud Run Job and all its executions."""
        try:
            if not self.client:
                raise RuntimeError("Cloud Run Jobs client not initialized")
            
            job_name = self._get_job_name(repo_id)
            operation = self.client.delete_job(name=job_name)
            operation.result()
            
            logger.info(f"Deleted job for repository {repo_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete job for {repo_id}: {e}")
            return False
    
    async def get_job_info(self, repo_id: str) -> Dict[str, Any]:
        """Get information about a specific job."""
        try:
            if not self.client:
                raise RuntimeError("Cloud Run Jobs client not initialized")
            
            job_name = self._get_job_name(repo_id)
            job = self.client.get_job(name=job_name)
            
            return {
                "name": job.name,
                "uid": job.uid,
                "generation": job.generation,
                "labels": dict(job.labels) if job.labels else {},
                "annotations": dict(job.annotations) if job.annotations else {},
                "create_time": job.create_time.ToDatetime().isoformat() + "Z" if job.create_time else None,
                "update_time": job.update_time.ToDatetime().isoformat() + "Z" if job.update_time else None,
                "delete_time": job.delete_time.ToDatetime().isoformat() + "Z" if job.delete_time else None,
                "expire_time": job.expire_time.ToDatetime().isoformat() + "Z" if job.expire_time else None,
                "creator": job.creator,
                "last_modifier": job.last_modifier,
                "client": job.client,
                "client_version": job.client_version,
                "launch_stage": job.launch_stage.name if job.launch_stage else None,
                "binary_authorization": job.binary_authorization.name if job.binary_authorization else None,
                "template": {
                    "parallelism": job.template.parallelism,
                    "task_count": job.template.task_count,
                    "timeout": job.template.timeout,
                    "template": {
                        "cpu": job.template.template.resources.cpu if job.template.template.resources else None,
                        "memory": job.template.template.resources.memory if job.template.template.resources else None,
                        "image": job.template.template.image
                    }
                } if job.template else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get job info for {repo_id}: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }


# Global Cloud Run Jobs service instance
_jobs_service: Optional[CloudRunJobsService] = None


def get_jobs_service() -> CloudRunJobsService:
    """Get Cloud Run Jobs service instance."""
    global _jobs_service
    if _jobs_service is None:
        _jobs_service = CloudRunJobsService()
    return _jobs_service
