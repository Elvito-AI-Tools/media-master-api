"""
Routes for image to video conversion.
"""
from fastapi import APIRouter, HTTPException
from app.models import (
    ImageToVideoRequest, 
    JobResponse, 
    JobStatusResponse,
)
from app.services.job_queue import job_queue
from app.services.image.image_to_video import image_to_video_service

router = APIRouter(prefix="/v1/image", tags=["image"])


@router.post("/to-video", response_model=JobResponse)
async def create_image_to_video_job(request: ImageToVideoRequest):
    """
    Create an optimized job to convert an image to a video with optional audio and captions.
    
    This endpoint is a high-performance version of /to-video that uses a 
    streamlined processing pipeline to significantly reduce S3 uploads/downloads and 
    processing time. It combines multiple steps into fewer FFmpeg operations.
    
    1. Converts an image to video with a Ken Burns zoom effect
    2. Optionally generates audio from text or uses provided audio URL
    3. Mixes the video and audio
    4. Optionally adds captions to the video
    
    Args:
        request: Comprehensive request with the following parameters:
            - image_url: URL of the image to convert to video
            - video_length, frame_rate, zoom_speed: Video parameters
            - speech_text: Text to convert to speech (optional)
            - voice: Voice to use for speech synthesis (optional)
            - audio_url: URL of audio file to add (optional, ignored if speech_text is provided)
            - audio_vol: Volume level for the audio track (0-100)
            - should_add_captions: Whether to automatically add captions by transcribing audio
            - caption_properties: Styling properties for captions (optional) including:
                - max_words_per_line: Control how many words appear per line of captions (1-20, default: 10)
                - font_size, font_family, color, position, etc.
            - match_length: Whether to match the output length to 'audio' or 'video'
            
    Returns:
        JobResponse with job_id that can be used to check the status of the job
    """
    try:
        # Validate match_length parameter
        if request.match_length not in ["audio", "video"]:
            raise ValueError("match_length must be either 'audio' or 'video'")
        
        # Create a new job with all the parameters
        params = {
            "image_url": str(request.image_url),
            "video_length": request.video_length,
            "frame_rate": request.frame_rate,
            "zoom_speed": request.zoom_speed,
            "match_length": request.match_length,
            "audio_vol": request.audio_vol,
            "should_add_captions": request.should_add_captions
        }
        
        # Add optional parameters if provided
        if request.speech_text:
            params["speech_text"] = request.speech_text
            params["voice"] = request.voice
        elif request.audio_url:
            params["audio_url"] = str(request.audio_url)
        
        if request.caption_properties:
            params["caption_properties"] = request.caption_properties.dict(
                exclude_none=True  # Only include non-None values
            )
        
        # Create and start the job
        job_id = job_queue.create_job(
            operation="optimized_image_to_video_with_audio_captions",
            params=params
        )
        
        # Start processing the job using the optimized processor
        job_queue.start_job_processing(job_id, image_to_video_service.image_to_video)
        
        return JobResponse(job_id=job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/to-video/{job_id}", response_model=JobStatusResponse)
async def get_image_to_video_job_status(job_id: str):
    """
    Get the status of an image-to-video with audio and captions job.
    
    This is the status endpoint for jobs created through /to-video.
    
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