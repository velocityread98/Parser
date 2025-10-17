"""
Background Task Manager for Async PDF Processing

Handles background processing of PDFs with status tracking and result storage.
Uses process pool for true parallelism to avoid blocking the event loop.
"""

import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskInfo:
    """Information about a background task"""
    task_id: str
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: Optional[Dict] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    source_url: Optional[str] = None
    source_filename: Optional[str] = None


class BackgroundTaskManager:
    """Manages background PDF processing tasks
    
    Uses ThreadPoolExecutor to run CPU-bound work in separate threads,
    preventing the event loop from being blocked during PDF processing.
    """
    
    def __init__(self, max_workers: int = 1):
        """Initialize the task manager
        
        Args:
            max_workers: Maximum number of concurrent processing workers
        """
        self.tasks: Dict[str, TaskInfo] = {}
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self._processing_service = None
        self._worker_running = False
        self._tasks_processed = 0
        self.max_workers = max_workers
        self.executor: Optional[ThreadPoolExecutor] = None
        
    def set_processing_service(self, service):
        """Set the processing service instance
        
        Args:
            service: PDFProcessingService instance
        """
        self._processing_service = service
    
    async def start_worker(self):
        """Start the background worker and thread pool"""
        # Initialize thread pool executor
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        logger.info(f"Thread pool initialized with {self.max_workers} workers")
        
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._worker())
            self._worker_running = True
            logger.info("Background worker started")
            # Give the worker a moment to initialize
            await asyncio.sleep(0.1)
    
    async def stop_worker(self):
        """Stop the background worker and shutdown thread pool"""
        self._worker_running = False
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            logger.info("Background worker stopped")
        
        # Shutdown thread pool
        if self.executor:
            logger.info("Shutting down thread pool...")
            self.executor.shutdown(wait=True)
            logger.info("Thread pool shutdown complete")
    
    async def submit_task(
        self,
        task_id: str,
        pdf_path: str,
        source_url: Optional[str] = None,
        source_filename: Optional[str] = None,
        output_container: str = "dolphin-results",
        max_batch_size: int = 16
    ) -> TaskInfo:
        """Submit a new PDF processing task
        
        Args:
            task_id: Unique task identifier
            pdf_path: Path to the PDF file
            source_url: Source URL if from blob storage
            source_filename: Source filename if from upload
            output_container: Container name for output storage
            max_batch_size: Maximum batch size for processing
            
        Returns:
            TaskInfo for the submitted task
        """
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            source_url=source_url,
            source_filename=source_filename
        )
        
        self.tasks[task_id] = task_info
        
        # Add to processing queue
        await self.processing_queue.put({
            "task_id": task_id,
            "pdf_path": pdf_path,
            "source_url": source_url,
            "source_filename": source_filename,
            "output_container": output_container,
            "max_batch_size": max_batch_size
        })
        
        logger.info(f"Task {task_id} submitted to queue")
        return task_info
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get the status of a task
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskInfo if task exists, None otherwise
        """
        return self.tasks.get(task_id)
    
    def list_tasks(self) -> Dict[str, TaskInfo]:
        """List all tasks
        
        Returns:
            Dictionary of all tasks
        """
        return self.tasks.copy()
    
    def get_worker_status(self) -> Dict:
        """Get worker status information
        
        Returns:
            Dictionary with worker status
        """
        return {
            "worker_running": self._worker_running,
            "worker_alive": self.worker_task and not self.worker_task.done() if self.worker_task else False,
            "executor_type": "ThreadPoolExecutor",
            "max_workers": self.max_workers,
            "executor_running": self.executor is not None and not self.executor._shutdown,
            "queue_size": self.processing_queue.qsize(),
            "total_tasks": len(self.tasks),
            "tasks_processed": self._tasks_processed,
            "pending_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
            "processing_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING),
            "completed_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
        }
    
    async def _worker(self):
        """Background worker that processes tasks from the queue"""
        logger.info("Background worker loop started")
        
        while True:
            try:
                # Get next task from queue
                task_data = await self.processing_queue.get()
                task_id = task_data["task_id"]
                
                logger.info(f"Processing task {task_id}")
                
                # Update task status
                task_info = self.tasks[task_id]
                task_info.status = TaskStatus.PROCESSING
                task_info.started_at = datetime.now().isoformat()
                
                try:
                    # Process the PDF in thread pool to avoid blocking event loop
                    # This is crucial: CPU-bound work must run in a separate thread/process
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        self.executor,
                        self._process_pdf_sync,
                        task_data["pdf_path"],
                        task_id,
                        task_data["source_url"],
                        task_data["source_filename"],
                        task_data["max_batch_size"]
                    )
                    
                    # Upload results to blob storage if available
                    output_url = None
                    if self._processing_service.blob_manager:
                        output_blob_name = f"processed_{task_id}.json"
                        output_url = await self._processing_service.blob_manager.upload_json_to_blob(
                            result.dict(), task_data["output_container"], output_blob_name
                        )
                    
                    # Update task with success
                    task_info.status = TaskStatus.COMPLETED
                    task_info.completed_at = datetime.now().isoformat()
                    task_info.result = {
                        "output_url": output_url,
                        "total_pages": result.total_pages,
                        "processing_time": result.processing_time,
                        "timestamp": result.timestamp
                    }
                    
                    self._tasks_processed += 1
                    logger.info(f"Task {task_id} completed successfully ({self._tasks_processed} total)")
                    
                except Exception as e:
                    # Update task with error
                    task_info.status = TaskStatus.FAILED
                    task_info.completed_at = datetime.now().isoformat()
                    task_info.error = str(e)
                    
                    self._tasks_processed += 1
                    logger.error(f"Task {task_id} failed: {str(e)}", exc_info=True)
                
                finally:
                    # Clean up temporary file if it exists
                    if task_data["pdf_path"]:
                        self._processing_service.file_manager.cleanup_temp_file(
                            task_data["pdf_path"]
                        )
                
                # Mark task as done in queue
                self.processing_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("Worker task cancelled")
                self._worker_running = False
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker: {str(e)}", exc_info=True)
                # Continue processing other tasks
                continue
    
    def _process_pdf_sync(
        self,
        pdf_path: str,
        task_id: str,
        source_url: Optional[str],
        source_filename: Optional[str],
        max_batch_size: int
    ):
        """Synchronous PDF processing that runs in thread pool
        
        This method runs in a separate thread to avoid blocking the event loop.
        It performs the actual CPU/GPU-bound work.
        """
        import asyncio
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async processing in this thread's event loop
            result = loop.run_until_complete(
                self._processing_service._process_pdf_file(
                    pdf_path=pdf_path,
                    task_id=task_id,
                    source_url=source_url,
                    source_filename=source_filename,
                    max_batch_size=max_batch_size
                )
            )
            return result
        finally:
            loop.close()

