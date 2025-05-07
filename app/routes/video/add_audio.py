"""
Routes for adding audio to videos.
"""
import logging
import uuid
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.utils.media import download_media_file, SUPPORTED_AUDIO_FORMATS, SUPPORTED_VIDEO_FORMATS
from app.services.job_queue import job_queue, JobType
from app.services.video.add_audio import add_audio_service
from app.models import JobResponse, JobStatusResponse, VideoAddAudioRequest, VideoAddAudioResult

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/add-audio", tags=["add-audio"])

@router.post("/", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_add_audio_job(request: VideoAddAudioRequest):
    """
    Create a job to add audio to a video.
    
    Args:
        request: The request containing video URL, audio URL, and mixing options
        
    Returns:
        A JobResponse object with the job ID and initial status
        
    Raises:
        HTTPException: If the job cannot be created
    """
    # Validate input
    if not request.video_url:
        raise HTTPException(status_code=400, detail="No video URL provided")
    
    if not request.audio_url:
        raise HTTPException(status_code=400, detail="No audio URL provided")
    
    # Validate match_length option
    if request.match_length not in ["audio", "video"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid match_length option. Must be either 'audio' or 'video'"
        )
    
    # Create job data
    job_data = {
        "video_url": request.video_url,
        "audio_url": request.audio_url,
        "video_volume": request.video_volume,
        "audio_volume": request.audio_volume,
        "match_length": request.match_length
    }
    
    # Create a job
    job_id = str(uuid.uuid4())
    
    try:
        # Add job to queue
        await job_queue.add_job(
            job_id=job_id,
            job_type=JobType.VIDEO_ADD_AUDIO,
            process_func=add_audio_service.process_job,
            data=job_data
        )
        
        logger.info(f"Created video add audio job: {job_id}")
        
        # Return the response with the job_id and status
        return JobResponse(
            job_id=job_id,
            status="processing"  # Jobs are immediately processed after creation
        )
    except Exception as e:
        logger.error(f"Failed to create add audio job: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create add audio job: {str(e)}"
        )

@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of an add audio job.
    
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