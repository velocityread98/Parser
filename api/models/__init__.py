"""
Data models module for the Dolphin PDF Processing API

Now uses shared velocityread-models package.
"""

from velocityread_models.parser import (
    ProcessingRequest,
    UploadProcessingRequest,
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

