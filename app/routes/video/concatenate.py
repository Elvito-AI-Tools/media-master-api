"""
Routes for video concatenation operations.
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.utils.media import SUPPORTED_VIDEO_FORMATS
from app.services.job_queue import job_queue, JobStatus, JobType
from app.services.video.concatenate import concatenation_service
from app.models import JobResponse, JobStatusResponse, VideoConcatenateRequest, VideoConcatenateResult

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/concatenate", tags=["concatenate"])

@router.post("/", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_concatenate_job(request: VideoConcatenateRequest):
    """
    Create a job to concatenate multiple videos into a single video.
    
    Args:
        request: The request containing a list of video URLs to concatenate.
        
    Returns:
        A JobResponse object with the job ID and initial status.
        
    Raises:
        HTTPException: If the job cannot be created.
    """
    # Validate input
    if not request.video_urls:
        raise HTTPException(status_code=400, detail="No video URLs provided")
    
    # Validate output format
    output_format = request.output_format.lower()
    if not output_format.startswith('.'):
        output_format = f".{output_format}"
    
    if output_format not in SUPPORTED_VIDEO_FORMATS:
        valid_formats = [f[1:] for f in SUPPORTED_VIDEO_FORMATS]  # Remove the leading dot
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported output format. Supported formats: {', '.join(valid_formats)}"
        )
    
    # Create job data
    job_data = {
        "video_urls": request.video_urls,
        "output_format": output_format
    }
    
    # Create a job
    job_id = str(uuid.uuid4())
    
    try:
        # Add job to queue
        await job_queue.add_job(
            job_id=job_id,
            job_type=JobType.VIDEO_CONCATENATION,
            process_func=concatenation_service.process_job,
            data=job_data
        )
        
        logger.info(f"Created video concatenation job: {job_id}")
        
        # Return the response with the job_id and status
        # Since jobs immediately go to "processing" state after add_job
        return JobResponse(
            job_id=job_id,
            status="processing"  # Jobs are immediately processed after creation
        )
    except Exception as e:
        logger.error(f"Failed to create concatenation job: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create concatenation job: {str(e)}"
        )

@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a concatenation job.
    
    Args:
        job_id: The ID of the job to check.
        
    Returns:
        A JobStatusResponse object with the job status and result if available.
        
    Raises:
        HTTPException: If the job is not found.
    """
    # Get job status
    job_info = await job_queue.get_job_info(job_id)
    
    if not job_info:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )
    
    # Create response
    response = JobStatusResponse(
        job_id=job_id,
        status=job_info.status.value,
        result=job_info.result,
        error=job_info.error
    )
    
    return response 