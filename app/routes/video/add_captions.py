"""
Routes for adding captions to videos.
"""
import logging
import uuid
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.utils.media import download_media_file, SUPPORTED_VIDEO_FORMATS
from app.services.job_queue import job_queue, JobType
from app.services.video.add_captions import add_captions_service
from app.models import JobResponse, JobStatusResponse, VideoAddCaptionsRequest, VideoAddCaptionsResult

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/add-captions", tags=["add-captions"])

@router.post("/", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_add_captions_job(request: VideoAddCaptionsRequest):
    """
    Create a job to add captions to a video.
    
    Args:
        request: The request containing video URL, captions content/URL, and styling options
        
    Returns:
        A JobResponse object with the job ID and initial status
        
    Raises:
        HTTPException: If the job cannot be created
    """
    # Validate input
    if not request.video_url:
        raise HTTPException(status_code=400, detail="No video URL provided")
    
    # Create job data
    job_data = {
        "video_url": request.video_url,
        "captions": request.captions,
        "caption_properties": request.caption_properties.dict() if request.caption_properties else None
    }
    
    # Create a job
    job_id = str(uuid.uuid4())
    
    try:
        # Add job to queue
        await job_queue.add_job(
            job_id=job_id,
            job_type=JobType.VIDEO_ADD_CAPTIONS,
            process_func=add_captions_service.process_job,
            data=job_data
        )
        
        logger.info(f"Created video add captions job: {job_id}")
        
        # Return the response with the job_id and status
        return JobResponse(
            job_id=job_id,
            status="processing"  # Jobs are immediately processed after creation
        )
    except Exception as e:
        logger.error(f"Failed to create add captions job: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create add captions job: {str(e)}"
        )

@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of an add captions job.
    
    Args:
        job_id: The ID of the job to check
        
    Returns:
        A JobStatusResponse object with the job status and result if available
        
    Raises:
        HTTPException: If the job is not found
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