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
    2. Optionally generates narrator audio from text or uses provided narrator audio URL
    3. Optionally adds background music (can be from YouTube)
    4. Mixes the video, narrator audio, and background music
    5. Optionally adds captions to the video
    
    Args:
        request: Comprehensive request with the following parameters:
            - image_url: URL of the image to convert to video
            - video_length, frame_rate, zoom_speed: Video parameters
            - narrator_speech_text: Text to convert to speech (optional)
            - voice: Voice to use for speech synthesis (optional)
            - narrator_audio_url: URL of audio file to add as narration (optional, ignored if narrator_speech_text is provided)
            - narrator_vol: Volume level for the narrator audio track (0-100)
            - background_music_url: URL of background music to add (optional, can be YouTube URL)
            - background_music_vol: Volume level for the background music track (0-100, default: 20)
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
            "narrator_vol": request.narrator_vol,
            "should_add_captions": request.should_add_captions,
            "effect_type": request.effect_type,
            "pan_direction": request.pan_direction,
            "ken_burns_keypoints": request.ken_burns_keypoints
        }
        
        # Add optional narrator audio parameters if provided
        if request.narrator_speech_text:
            params["narrator_speech_text"] = request.narrator_speech_text
            params["voice"] = request.voice
        elif request.narrator_audio_url:
            params["narrator_audio_url"] = str(request.narrator_audio_url)
        
        # Add optional background music parameters if provided
        if request.background_music_url:
            params["background_music_url"] = str(request.background_music_url)
            params["background_music_vol"] = request.background_music_vol
        
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