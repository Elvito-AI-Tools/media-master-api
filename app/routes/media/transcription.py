"""
Routes for media transcription using Whisper.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import AnyUrl

from app.models import JobResponse, JobStatusResponse, MediaTranscriptionRequest, MediaTranscriptionResult
from app.services.job_queue import job_queue
from app.services.media.transcription import transcription_service

router = APIRouter(prefix="/v1/media", tags=["media"])


async def process_transcription(params):
    """
    Process a transcription job.
    
    Args:
        params: Transcription parameters
            - media_url: URL of the media to transcribe
            - include_text: Whether to include plain text transcription
            - include_srt: Whether to include SRT format subtitles
            - word_timestamps: Whether to include word-level timestamps
            - language: Source language code (optional)
            - max_words_per_line: Maximum words per line in SRT (default: 10)
    
    Returns:
        Dict with transcription results
    """
    # Download the media
    local_file_path, file_extension = await transcription_service.download_media(params["media_url"])
    
    # Transcribe the media - this function should now properly use async
    result = await transcription_service.transcribe(
        local_file_path,
        include_text=params.get("include_text", True),
        include_srt=params.get("include_srt", True),
        word_timestamps=params.get("word_timestamps", False),
        language=params.get("language"),
        max_words_per_line=params.get("max_words_per_line", 10)
    )
    
    return result


@router.post("/transcription", response_model=JobResponse)
async def create_transcription_job(request: MediaTranscriptionRequest):
    """
    Create a job to transcribe media using Whisper.
    
    This endpoint accepts a media URL and transcribes it using Whisper.
    The transcription is processed asynchronously, and the results can be retrieved
    using the returned job_id.
    
    Args:
        request: Media transcription request
            - media_url: URL of the media file to be transcribed
            - include_text: Include plain text transcription in the response
            - include_srt: Include SRT format subtitles in the response
            - word_timestamps: Include timestamps for individual words
            - language: Source language code for transcription (optional)
            - max_words_per_line: Maximum words per line in SRT (default: 10)
        
    Returns:
        JobResponse with job_id that can be used to check the status of the job
    """
    try:
        # Create a new job
        job_id = job_queue.create_job(
            operation="transcription",
            params={
                "media_url": str(request.media_url),
                "include_text": request.include_text,
                "include_srt": request.include_srt,
                "word_timestamps": request.word_timestamps,
                "language": request.language,
                "max_words_per_line": request.max_words_per_line
            }
        )
        
        # Start processing the job
        job_queue.start_job_processing(job_id, process_transcription)
        
        return JobResponse(job_id=job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/transcription/{job_id}", response_model=JobStatusResponse)
async def get_transcription_job_status(job_id: str):
    """
    Get the status of a transcription job.
    
    This endpoint retrieves the current status of a transcription job. When the job
    is completed, the `result` field will contain a MediaTranscriptionResult object
    with the following possible fields:
    - `text`: The full text transcription of the media (if include_text was true)
    - `srt_url`: URL to the SRT subtitle file in S3 (if include_srt was true)
    - `words`: Word-level timestamps with time information (if word_timestamps was true)
    
    Args:
        job_id: ID of the job to get status for
        
    Returns:
        JobStatusResponse containing:
        - job_id: The ID of the job
        - status: Current job status (pending, processing, completed, failed)
        - result: If completed, contains the transcription results (MediaTranscriptionResult)
        - error: If failed, contains error information
    """
    # Simply retrieve the job status without any waiting or processing
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    
    # Immediately return the current status
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        result=job.result,
        error=job.error
    ) 