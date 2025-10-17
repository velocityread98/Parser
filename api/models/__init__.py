"""
Data models module for the Dolphin PDF Processing API
"""

from .request_models import ProcessingRequest, UploadProcessingRequest
from .response_models import (
    ElementData,
    ErrorResponse,
    HealthResponse,
    PageData,
    ProcessingResponse,
    ProcessingResult,
    TaskStatusResponse,
)

__all__ = [
    # Request models
    "ProcessingRequest",
    "UploadProcessingRequest",
    # Response models
    "ElementData",
    "ErrorResponse",
    "HealthResponse",
    "PageData",
    "ProcessingResponse",
    "ProcessingResult",
    "TaskStatusResponse",
]

