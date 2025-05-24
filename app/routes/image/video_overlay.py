"""
Routes for video overlay operations.
"""
from fastapi import APIRouter, HTTPException
from app.models import (
    VideoOverlayRequest, 
    JobResponse, 
    JobStatusResponse,
)
from app.services.job_queue import job_queue
from app.services.image.video_overlay import video_overlay_service

router = APIRouter(prefix="/v1/image", tags=["image"])


@router.post("/add-video-overlay", response_model=JobResponse)
async def create_video_overlay_job(request: VideoOverlayRequest):
    """
    Create a job to overlay videos on top of a base image.
    
    This endpoint processes a request to overlay one or more videos onto a base image,
    creating dynamic video compositions with precise control over positioning, timing, 
    size, and audio mixing.
    
    Args:
        request: Video overlay request with the following parameters:
            - base_image_url: URL of the base image
            - overlay_videos: List of overlay videos with position and timing information including:
                - url: URL of the overlay video
                - x, y: Position (0-1) where to place the overlay
                - width, height: Optional size (0-1) relative to base image
                - start_time, end_time: Optional timing information
                - loop: Whether to loop the video
                - opacity: Optional opacity (0-1)
                - volume: Optional volume (0-1)
                - z_index: Optional layer order (higher values appear on top)
            - output_duration: Duration of the output video (optional)
            - frame_rate: Frame rate of the output video (default: 30)
            - output_width, output_height: Optional output dimensions
            - maintain_aspect_ratio: Whether to maintain aspect ratio when resizing (default: True)
            - background_audio_url: Optional background audio URL
            - background_audio_volume: Volume for background audio (default: 0.2)
            
    Returns:
        JobResponse with job_id that can be used to check the status of the job
    """
    try:
        # Convert overlay_videos to a list of dictionaries
        overlay_videos = []
        for overlay in request.overlay_videos:
            # Convert Pydantic model to dictionary
            overlay_dict = overlay.dict(exclude_none=True)
            # Ensure URL is a string
            overlay_dict["url"] = str(overlay_dict["url"])
            overlay_videos.append(overlay_dict)
            
        # Create parameters dictionary
        params = {
            "base_image_url": str(request.base_image_url),
            "overlay_videos": overlay_videos,
            "frame_rate": request.frame_rate,
            "maintain_aspect_ratio": request.maintain_aspect_ratio
        }
        
        # Add optional parameters if provided
        if request.output_duration:
            params["output_duration"] = request.output_duration
        if request.output_width:
            params["output_width"] = request.output_width
        if request.output_height:
            params["output_height"] = request.output_height
        if request.background_audio_url:
            params["background_audio_url"] = str(request.background_audio_url)
            params["background_audio_volume"] = request.background_audio_volume
        
        # Create and start the job
        job_id = job_queue.create_job(
            operation="video_overlay",
            params=params
        )
        
        # Start processing the job
        job_queue.start_job_processing(job_id, video_overlay_service.overlay_videos)
        
        return JobResponse(job_id=job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/add-video-overlay/{job_id}", response_model=JobStatusResponse)
async def get_video_overlay_job_status(job_id: str):
    """
    Get the status of a video overlay job.
    
    Args:
        job_id: ID of the job to get status for
        
    Returns:
        JobStatusResponse containing the job status and results when completed
    """
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        result=job.result,
        error=job.error
    ) 