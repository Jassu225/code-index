"""
Configuration management for the Serverless Code Index System.
"""

import os
import json
from typing import Optional, List, Union
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env.test for development
try:
    from dotenv import load_dotenv
    print(f"Config: Starting environment loading process...")
    print(f"Config: Current GCP_PROJECT_ID before loading: {os.environ.get('GCP_PROJECT_ID', 'NOT_SET')}")
    
    # Check if ENV_FILE is specified, otherwise use default priority
    env_file = os.environ.get("ENV_FILE", None)
    if env_file and Path(env_file).exists():
        load_dotenv(env_file)
        print(f"Config: Loaded environment from {env_file} (from ENV_FILE)")
        print(f"Config: GCP_PROJECT_ID after loading {env_file}: {os.environ.get('GCP_PROJECT_ID', 'NOT_SET')}")
    elif Path("gcp.env").exists():
        load_dotenv("gcp.env")
        print("Config: Loaded environment from gcp.env")
        print(f"Config: GCP_PROJECT_ID after loading gcp.env: {os.environ.get('GCP_PROJECT_ID', 'NOT_SET')}")
    elif Path(".env").exists():
        load_dotenv(".env")
        print("Config: Loaded environment from .env")
        print(f"Config: GCP_PROJECT_ID after loading .env: {os.environ.get('GCP_PROJECT_ID', 'NOT_SET')}")
    elif Path(".env.test").exists():
        load_dotenv(".env.test")
        print("Config: Loaded environment from .env.test")
        print(f"Config: GCP_PROJECT_ID after loading .env.test: {os.environ.get('GCP_PROJECT_ID', 'NOT_SET')}")
    else:
        print("Config: No gcp.env, .env, or .env.test file found")
except ImportError:
    print("Config: python-dotenv not installed, using system environment variables")


class Settings(BaseSettings):
    """Application settings with GCP and Firestore configuration."""
    
    # Application settings
    app_name: str = "Serverless Code Index System"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # GCP Project settings
    gcp_project_id: str = Field(default="icode-94891", env="GCP_PROJECT_ID")
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
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from various input formats."""
        if isinstance(v, str):
            # Try to parse as JSON first
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If not valid JSON, treat as comma-separated string
                return [origin.strip() for origin in v.split(',') if origin.strip()]
        elif isinstance(v, list):
            return v
        else:
            return ["*"]
    
    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        """Initialize settings and force reload from environment."""
        super().__init__(**kwargs)
        # Force reload values from environment variables
        self._reload_from_env()
    
    def _reload_from_env(self):
        """Force reload values from environment variables."""
        print(f"Config: Reloading from environment variables...")
        for field_name, field_info in Settings.model_fields.items():
            # Get the environment variable name (alias or uppercase field name)
            env_var = field_name.upper()
            if env_var in os.environ:
                env_value = os.environ[env_var]
                print(f"Config: Found {env_var}={env_value} for field {field_name}")
                if env_value:
                    # Convert the value to the proper type if possible
                    try:
                        # Use Pydantic's validation to convert the value
                        # In Pydantic v2, we need to use the field's annotation for type conversion
                        field_type = field_info.annotation
                        if field_type:
                            if field_type == bool:
                                # Handle boolean conversion
                                validated_value = env_value.lower() in ('true', '1', 'yes', 'on')
                            elif field_type == int:
                                validated_value = int(env_value)
                            elif field_type == float:
                                validated_value = float(env_value)
                            elif field_type == list:
                                # Handle list conversion (for CORS_ORIGINS)
                                try:
                                    validated_value = json.loads(env_value)
                                except json.JSONDecodeError:
                                    validated_value = [env_value.strip() for env_value in env_value.split(',') if env_value.strip()]
                            else:
                                validated_value = env_value
                        else:
                            validated_value = env_value
                        
                        setattr(self, field_name, validated_value)
                        print(f"Config: Set {field_name} = {validated_value}")
                    except Exception as e:
                        # Fallback to setting the raw value
                        print(f"Config: Warning - could not validate {field_name}={env_value}: {e}")
                        setattr(self, field_name, env_value)
            else:
                print(f"Config: No environment variable found for {field_name} (looking for {env_var})")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
