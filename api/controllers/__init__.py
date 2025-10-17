"""
Controllers module for the Dolphin PDF Processing API
"""

from .health_controller import router as health_router
from .processing_controller import router as processing_router
from .task_controller import router as task_router

__all__ = [
    "health_router",
    "processing_router",
    "task_router",
]

