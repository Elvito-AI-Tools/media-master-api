"""
Routes for image overlay operations.
"""
from fastapi import APIRouter, HTTPException
from app.models import (
    ImageOverlayRequest, 
    JobResponse, 
    JobStatusResponse,
)
from app.services.job_queue import job_queue
from app.services.image.image_overlay import image_overlay_service

router = APIRouter(prefix="/v1/image", tags=["image"])


@router.post("/add-overlay-image", response_model=JobResponse)
async def create_image_overlay_job(request: ImageOverlayRequest):
    """
    Create a job to overlay images on top of a base image.
    
    This endpoint processes a request to overlay one or more images onto a base image,
    with precise control over positioning, size, rotation, and opacity of each overlay.
    
    Args:
        request: Image overlay request with the following parameters:
            - base_image_url: URL of the base image
            - overlay_images: List of overlay images with position information including:
                - url: URL of the overlay image
                - x, y: Position (0-1) where to place the overlay
                - width, height: Optional size (0-1) relative to base image
                - rotation: Optional rotation angle in degrees
                - opacity: Optional opacity (0-1)
                - z_index: Optional layer order (higher values appear on top)
            - output_format: Output image format (default: 'png')
            - output_quality: Quality for lossy formats (1-100, default: 90)
            - output_width, output_height: Optional output dimensions
            - maintain_aspect_ratio: Whether to maintain aspect ratio when resizing (default: True)
            
    Returns:
        JobResponse with job_id that can be used to check the status of the job
    """
    try:
        # Convert overlay_images to a list of dictionaries
        overlay_images = []
        for overlay in request.overlay_images:
            # Convert Pydantic model to dictionary
            overlay_dict = overlay.dict(exclude_none=True)
            # Ensure URL is a string
            overlay_dict["url"] = str(overlay_dict["url"])
            overlay_images.append(overlay_dict)
            
        # Create parameters dictionary
        params = {
            "base_image_url": str(request.base_image_url),
            "overlay_images": overlay_images,
            "output_format": request.output_format,
            "output_quality": request.output_quality,
            "maintain_aspect_ratio": request.maintain_aspect_ratio
        }
        
        # Add optional output dimensions if provided
        if request.output_width:
            params["output_width"] = request.output_width
        if request.output_height:
            params["output_height"] = request.output_height
        
        # Create and start the job
        job_id = job_queue.create_job(
            operation="image_overlay",
            params=params
        )
        
        # Start processing the job
        job_queue.start_job_processing(job_id, image_overlay_service.overlay_images)
        
        return JobResponse(job_id=job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/add-overlay-image/{job_id}", response_model=JobStatusResponse)
async def get_image_overlay_job_status(job_id: str):
    """
    Get the status of an image overlay job.
    
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