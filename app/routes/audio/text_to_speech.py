"""
Routes for text to speech conversion using Kokoro TTS.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from app.models import TextToSpeechRequest, JobResponse, JobStatusResponse
from app.services.job_queue import job_queue
from app.services.audio.text_to_speech import process_text_to_speech

router = APIRouter(prefix="/v1/audio", tags=["audio"])


@router.post("/text-to-speech", response_model=JobResponse)
async def create_text_to_speech_job(request: TextToSpeechRequest):
    """
    Create a job to convert text to speech using the external Kokoro TTS service.
    
    This endpoint accepts text and converts it to speech using the specified Kokoro voice.
    The audio is processed by a dedicated Kokoro TTS service container.
    
    Args:
        request: Text to speech request
            - text: Text to convert to speech
            - voice: Kokoro voice to use (default: "af_alloy")
            
    Returns:
        JobResponse with job_id that can be used to check the status of the job
    """
    try:
        # Create a new job
        job_id = job_queue.create_job(
            operation="text_to_speech",
            params={
                "text": request.text,
                "voice": request.voice
            }
        )
        
        # Start processing the job
        job_queue.start_job_processing(job_id, process_text_to_speech)
        
        return JobResponse(job_id=job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/text-to-speech/{job_id}", response_model=JobStatusResponse)
async def get_text_to_speech_job_status(job_id: str):
    """
    Get the status of a text to speech conversion job.
    
    Args:
        job_id: ID of the job to get status for
        
    Returns:
        JobStatusResponse containing:
        - job_id: The ID of the job
        - status: Current job status (pending, processing, completed, failed)
        - result: If completed, contains the audio_url
        - error: If failed, contains error information
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