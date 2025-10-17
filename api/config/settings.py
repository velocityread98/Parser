"""
Application Settings and Configuration

Centralized configuration management using environment variables.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)


class Settings:
    """Application settings loaded from environment variables"""
    
    # Azure Storage Configuration
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    # Model Configuration
    MODEL_PATH: str = os.getenv("MODEL_PATH", "./Dolphin/hf_model")
    MAX_BATCH_SIZE: int = int(os.getenv("MAX_BATCH_SIZE", "16"))
    
    # Container Configuration
    CONTAINER_NAME: str = os.getenv("CONTAINER_NAME", "dolphin-processing")
    DEFAULT_OUTPUT_CONTAINER: str = os.getenv("DEFAULT_OUTPUT_CONTAINER", "dolphin-results")
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_VERSION: str = "1.0.0"
    API_TITLE: str = "Dolphin PDF Processing API"
    API_DESCRIPTION: str = "API for processing PDFs using Dolphin document parsing model"
    
    # Background Processing Configuration
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "1"))
    # Number of concurrent PDF processing workers
    # Set to 1 to avoid GPU memory issues. Increase only if you have multiple GPUs.
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def is_blob_storage_configured(self) -> bool:
        """Check if blob storage is configured"""
        return self.AZURE_STORAGE_CONNECTION_STRING is not None
    
    def __repr__(self) -> str:
        """String representation (hiding sensitive data)"""
        return (
            f"Settings("
            f"MODEL_PATH={self.MODEL_PATH}, "
            f"BLOB_STORAGE={'configured' if self.is_blob_storage_configured else 'not configured'}, "
            f"API_PORT={self.API_PORT}"
            f")"
        )


# Global settings instance
settings = Settings()

