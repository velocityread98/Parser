"""
Task Controller

Handles task status and monitoring endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from ..models import TaskStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Global task manager reference (will be set by main.py)
_task_manager = None


def set_task_manager(task_manager):
    """Set the task manager instance"""
    global _task_manager
    _task_manager = task_manager


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get the status of a processing task
    
    Args:
        task_id: Unique task identifier
    
    Returns:
        TaskStatusResponse with current task status
    """
    if not _task_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task manager not initialized"
        )
    
    task_info = _task_manager.get_task_status(task_id)
    
    if not task_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    return TaskStatusResponse(
        task_id=task_info.task_id,
        status=task_info.status.value,
        created_at=task_info.created_at,
        started_at=task_info.started_at,
        completed_at=task_info.completed_at,
        progress=task_info.progress,
        result=task_info.result,
        error=task_info.error,
        source_url=task_info.source_url,
        source_filename=task_info.source_filename
    )


@router.get("", response_model=dict)
async def list_tasks():
    """List all processing tasks
    
    Returns:
        Dictionary of all tasks with their status
    """
    if not _task_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task manager not initialized"
        )
    
    tasks = _task_manager.list_tasks()
    
    return {
        "total_tasks": len(tasks),
        "tasks": [
            {
                "task_id": task.task_id,
                "status": task.status.value,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "source_url": task.source_url,
                "source_filename": task.source_filename
            }
            for task in tasks.values()
        ]
    }


@router.get("/worker/status", response_model=dict)
async def get_worker_status():
    """Get background worker status and statistics
    
    Returns:
        Dictionary with worker status information
    """
    if not _task_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task manager not initialized"
        )
    
    return _task_manager.get_worker_status()

