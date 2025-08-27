"""
Configuration management for the Serverless Code Index System.
"""

import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with GCP and Firestore configuration."""
    
    # Application settings
    app_name: str = "Serverless Code Index System"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # GCP Project settings
    gcp_project_id: str = Field(default="code-index-dev", env="GCP_PROJECT_ID")
    gcp_region: str = Field(default="us-central1", env="GCP_REGION")
    
    # Firestore settings
    firestore_collection_prefix: str = Field(default="", env="FIRESTORE_COLLECTION_PREFIX")
    firestore_database_id: Optional[str] = Field(default="(default)", env="FIRESTORE_DATABASE_ID")
    
    # Cloud Run Jobs settings (for batch processing)
    cloud_run_jobs_location: str = Field(default="europe-west4", env="CLOUD_RUN_JOBS_LOCATION")
    cloud_run_jobs_timeout: int = Field(default=86400, env="CLOUD_RUN_JOBS_TIMEOUT")  # 24 hours in seconds
    cloud_run_jobs_cpu: int = Field(default=2, env="CLOUD_RUN_JOBS_CPU")
    cloud_run_jobs_memory: str = Field(default="4Gi", env="CLOUD_RUN_JOBS_MEMORY")
    
    # Authentication settings
    use_application_default_credentials: bool = Field(default=True, env="USE_APPLICATION_DEFAULT_CREDENTIALS")
    service_account_key_path: Optional[str] = Field(default=None, env="GOOGLE_APPLICATION_CREDENTIALS")
    
    # Processing settings
    max_concurrent_files: int = Field(default=10, env="MAX_CONCURRENT_FILES")
    file_processing_timeout: int = Field(default=300, env="FILE_PROCESSING_TIMEOUT")  # seconds
    batch_size: int = Field(default=500, env="FIRESTORE_BATCH_SIZE")
    
    # API settings
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    api_rate_limit: int = Field(default=1000, env="API_RATE_LIMIT")  # requests per minute
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
