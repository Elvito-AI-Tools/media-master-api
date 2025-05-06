"""
Job queue service for handling asynchronous jobs.
"""
from datetime import datetime
import uuid
import logging
import traceback
from typing import Dict, Optional, List, Any, Callable, Awaitable
import asyncio
from app.models import Job, JobStatus, JobType

# Configure logging
logger = logging.getLogger(__name__)

class JobInfo:
    """Job info class for simplified job information."""
    def __init__(self, job: Job):
        self.id = job.id
        self.status = job.status
        self.result = job.result
        self.error = job.error
        self.created_at = job.created_at
        self.updated_at = job.updated_at

class JobQueue:
    """Job queue service."""
    
    def __init__(self, max_queue_size: int = 10):
        """Initialize job queue."""
        self.jobs: Dict[str, Job] = {}
        self.max_queue_size = max_queue_size
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        logger.info(f"Initialized job queue with max size {max_queue_size}")
        
    def get_pending_jobs_count(self) -> int:
        """Get number of pending jobs."""
        return sum(1 for job in self.jobs.values() if job.status == JobStatus.PENDING)
    
    def get_processing_jobs_count(self) -> int:
        """Get number of processing jobs."""
        return sum(1 for job in self.jobs.values() if job.status == JobStatus.PROCESSING)
    
    def is_queue_full(self) -> bool:
        """Check if queue is full."""
        return (self.get_pending_jobs_count() + self.get_processing_jobs_count()) >= self.max_queue_size
    
    def create_job(self, operation: str, params: Dict[str, Any]) -> str:
        """Create a new job and add it to the queue."""
        if self.is_queue_full():
            logger.warning("Job queue is full. Rejecting new job.")
            raise ValueError("Job queue is full. Please try again later.")
            
        job_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        job = Job(
            id=job_id,
            operation=operation,
            params=params,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        self.jobs[job_id] = job
        logger.info(f"Created new job {job_id} for operation {operation}")
        return job_id
        
    async def add_job(self, job_id: str, job_type: JobType, process_func: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]], data: Dict[str, Any]) -> str:
        """
        Add a new job to the queue and start processing it asynchronously.
        
        Args:
            job_id: The ID of the job.
            job_type: The type of the job.
            process_func: Function to process the job.
            data: Data for the job.
            
        Returns:
            Job ID
            
        Raises:
            ValueError: If the queue is full.
        """
        if self.is_queue_full():
            logger.warning("Job queue is full. Rejecting new job.")
            raise ValueError("Job queue is full. Please try again later.")
            
        timestamp = datetime.utcnow().isoformat()
        
        job = Job(
            id=job_id,
            operation=job_type.value,
            params=data,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        self.jobs[job_id] = job
        logger.info(f"Created new job {job_id} for operation {job_type.value}")
        
        # Start processing the job
        task = asyncio.create_task(self._process_job_wrapper(job_id, process_func, data))
        self.processing_tasks[job_id] = task
        
        return job_id
    
    async def _process_job_wrapper(self, job_id: str, process_func: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]], data: Dict[str, Any]):
        """
        Process a job using the provided function.
        
        Args:
            job_id: The ID of the job.
            process_func: Function to process the job.
            data: Data for the job.
        """
        job = self.jobs.get(job_id)
        if not job:
            logger.warning(f"Attempted to process non-existent job {job_id}")
            return
        
        # Update job status to processing
        job.status = JobStatus.PROCESSING
        job.updated_at = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} status updated to PROCESSING")
        
        try:
            # Process job
            result = await process_func(job_id, data)
            
            # Update job status to completed
            job.status = JobStatus.COMPLETED
            job.result = result
            job.updated_at = datetime.utcnow().isoformat()
            logger.info(f"Job {job_id} processed successfully")
        except Exception as e:
            # Get the full traceback
            tb = traceback.format_exc()
            
            # Update job status to failed
            job.status = JobStatus.FAILED
            job.error = f"{str(e)}\n\nTraceback:\n{tb}"
            job.updated_at = datetime.utcnow().isoformat()
            logger.error(f"Error processing job {job_id}: {e}\n{tb}")
        finally:
            # Remove task from processing tasks
            if job_id in self.processing_tasks:
                del self.processing_tasks[job_id]
    
    async def get_job_info(self, job_id: str) -> Optional[JobInfo]:
        """
        Get job information by ID.
        
        Args:
            job_id: The ID of the job.
            
        Returns:
            JobInfo object or None if job not found.
        """
        job = self.jobs.get(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found")
            return None
            
        return JobInfo(job)
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        job = self.jobs.get(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found")
        return job
    
    async def process_job(self, job_id: str, handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        """Process a job with the given handler."""
        job = self.jobs.get(job_id)
        if not job:
            logger.warning(f"Attempted to process non-existent job {job_id}")
            return
        
        # Job status is already set to PROCESSING in start_job_processing
        logger.info(f"Processing job {job_id} ({job.operation})")
        
        try:
            # Process job
            result = await handler(job.params)
            
            # Update job status to completed
            job.status = JobStatus.COMPLETED
            job.result = result
            job.updated_at = datetime.utcnow().isoformat()
            logger.info(f"Job {job_id} processed successfully")
        except Exception as e:
            # Get the full traceback
            tb = traceback.format_exc()
            
            # Update job status to failed
            job.status = JobStatus.FAILED
            job.error = f"{str(e)}\n\nTraceback:\n{tb}"
            job.updated_at = datetime.utcnow().isoformat()
            logger.error(f"Error processing job {job_id}: {e}\n{tb}")
        finally:
            # Remove task from processing tasks
            if job_id in self.processing_tasks:
                del self.processing_tasks[job_id]
    
    def start_job_processing(self, job_id: str, handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        """Start processing a job."""
        job = self.jobs.get(job_id)
        if not job:
            logger.warning(f"Attempted to start processing of non-existent job {job_id}")
            return
            
        if job.status != JobStatus.PENDING:
            logger.warning(f"Attempted to start processing of job {job_id} with status {job.status}")
            return
        
        # Update job status to processing immediately
        job.status = JobStatus.PROCESSING
        job.updated_at = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} status updated to PROCESSING")
        
        # Create and start the processing task
        logger.info(f"Starting job {job_id} processing task")
        task = asyncio.create_task(self.process_job(job_id, handler))
        self.processing_tasks[job_id] = task
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old completed or failed jobs."""
        now = datetime.utcnow()
        to_remove = []
        
        for job_id, job in self.jobs.items():
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                created_at = datetime.fromisoformat(job.created_at)
                age = (now - created_at).total_seconds() / 3600
                
                if age > max_age_hours:
                    to_remove.append(job_id)
        
        for job_id in to_remove:
            del self.jobs[job_id]
            logger.info(f"Removed old job {job_id}")


# Create a singleton instance
job_queue = JobQueue(max_queue_size=10) 