"""
Caption processing utilities for the image-to-video pipeline.
"""
import os
import uuid
import logging
from typing import Dict, Any, List, Optional

from app.utils.media import download_subtitle_file
from app.services.media.transcription import transcription_service
from app.utils.captions import (
    create_srt_from_text, 
    prepare_subtitle_styling,
    create_srt_from_word_timestamps,
)

logger = logging.getLogger(__name__)

async def process_captions_from_audio(audio_path: str, speech_text: Optional[str] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process captions from audio file with optional speech text.
    
    Args:
        audio_path: Path to the audio file
        speech_text: Optional text of the speech (for text-to-speech generated audio)
        params: Dictionary containing:
            - caption_properties: Caption styling properties
            - should_add_captions: Whether to add captions
            
    Returns:
        Dictionary containing:
            - srt_path: Path to the generated subtitle file
            - srt_url: URL of the subtitle file (if applicable)
            - caption_style: Style used for the captions
    """
    result = {
        "srt_path": None,
        "srt_url": None,
        "caption_style": None
    }
    
    if not params.get("should_add_captions", False) or not audio_path:
        return result
        
    try:
        # Get caption styling properties
        caption_properties = params.get("caption_properties", {})
        max_words_per_line = caption_properties.get("max_words_per_line", 10)
        style = caption_properties.get("style", "")
        
        # For highlight style and similar timed styles, we need word-level timestamps
        need_word_timestamps = True 
        
        # Make a copy of the audio file for transcription to prevent it from being deleted
        temp_dir = "temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        transcription_audio_path = os.path.join(temp_dir, f"transcribe_{uuid.uuid4()}.mp3")
        try:
            import shutil
            shutil.copy2(audio_path, transcription_audio_path)
            logger.info(f"Created copy of audio for transcription: {transcription_audio_path}")
        except Exception as copy_err:
            logger.error(f"Failed to copy audio for transcription: {str(copy_err)}")
            # Fall back to using the original file if copy fails
            transcription_audio_path = audio_path
        
        # Transcribe audio to get SRT
        logger.info(f"Transcribing audio for captions with style: {style}")
        transcription_result = await transcription_service.transcribe(
            transcription_audio_path,
            include_text=True,
            include_srt=True,
            word_timestamps=need_word_timestamps,
            max_words_per_line=max_words_per_line
        )
        
        if "srt_url" in transcription_result:
            # For highlight style, use word timestamps if available
            if need_word_timestamps and "words" in transcription_result:
                # Get audio duration (needed for SRT generation)
                from app.utils.image_to_video.audio_processing import get_audio_duration
                audio_duration = await get_audio_duration(audio_path)
                
                # Create custom styled subtitles using word timestamps
                srt_path = await create_srt_from_word_timestamps(
                    transcription_result["words"],
                    audio_duration,
                    max_words_per_line,
                    style,
                    caption_properties=caption_properties
                )
                logger.info(f"Created custom {style} style subtitle file using word timestamps")
            else:
                # For non-highlight styles or when word timestamps aren't available
                srt_path = await download_subtitle_file(transcription_result["srt_url"])
                logger.info("Using standard SRT from transcription")
                
            result["srt_path"] = srt_path
            result["srt_url"] = transcription_result.get("srt_url")
            result["caption_style"] = style
                
        return result
            
    except Exception as e:
        logger.error(f"Error processing captions from audio: {e}")
        return result

async def process_captions_from_text(text: str, duration: float, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process captions from text.
    
    Args:
        text: Text to create captions from
        duration: Duration of the audio in seconds
        params: Dictionary containing:
            - caption_properties: Caption styling properties
            
    Returns:
        Dictionary containing:
            - srt_path: Path to the generated subtitle file
            - caption_style: Style used for the captions
    """
    result = {
        "srt_path": None,
        "caption_style": None
    }
    
    if not text or duration <= 0:
        return result
        
    try:
        # Get caption styling properties
        caption_properties = params.get("caption_properties", {}) if params else {}
        max_words_per_line = caption_properties.get("max_words_per_line", 10)
        style = caption_properties.get("style", "highlight")
        
        # Create SRT file from text
        srt_path = await create_srt_from_text(
            text,
            duration,
            max_words_per_line,
            style
        )
        
        result["srt_path"] = srt_path
        result["caption_style"] = style
        
        return result
            
    except Exception as e:
        logger.error(f"Error processing captions from text: {e}")
        return result 