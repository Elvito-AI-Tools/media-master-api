"""
Audio processing utilities for the image-to-video pipeline.
"""
import os
import uuid
import json
import logging
import subprocess
from typing import Dict, Any, Tuple, Optional, List

from app.services.audio.text_to_speech import generate_speech
from app.utils.media import download_media_file
from app.utils.youtube import is_youtube_url, download_youtube_audio

logger = logging.getLogger(__name__)

async def verify_audio_file(audio_path: str) -> bool:
    """
    Verify that an audio file exists and contains valid audio data.
    
    Args:
        audio_path: Path to the audio file to verify
        
    Returns:
        True if the file exists and contains valid audio data, False otherwise
    """
    if not os.path.exists(audio_path):
        logger.error(f"Audio file does not exist: {audio_path}")
        return False
        
    # Check file size
    file_size = os.path.getsize(audio_path)
    if file_size == 0:
        logger.error(f"Audio file is empty (0 bytes): {audio_path}")
        return False
        
    # Use ffprobe to verify it's a valid audio file
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=format_name,duration",
            "-of", "json",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFprobe failed to verify audio file: {result.stderr}")
            return False
            
        info = json.loads(result.stdout)
        if "format" not in info:
            logger.error(f"No format information found in audio file: {audio_path}")
            return False
            
        # Log successful verification
        duration = info["format"].get("duration", "unknown")
        format_name = info["format"].get("format_name", "unknown")
        logger.info(f"Verified audio file {audio_path}: format={format_name}, duration={duration}, size={file_size} bytes")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying audio file {audio_path}: {str(e)}")
        return False

async def get_audio_duration(audio_path: str) -> float:
    """
    Get the duration of an audio file in seconds using FFprobe.
    
    Args:
        audio_path: Path to the audio file
            
    Returns:
        Duration in seconds
            
    Raises:
        RuntimeError: If the FFprobe operation fails
    """
    try:
        # Use FFprobe to get the duration
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        
        return duration
    except subprocess.CalledProcessError as e:
        logger.error(f"FFprobe error: {e.stderr}")
        raise RuntimeError(f"Failed to get media duration: {e.stderr}")
    except Exception as e:
        logger.error(f"Error getting media duration: {e}")
        raise RuntimeError(f"Failed to get media duration: {str(e)}")

async def process_narrator_audio(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process narrator audio from either URL or text-to-speech.
    
    Args:
        params: Dictionary containing:
            - narrator_audio_url: Optional URL of narrator audio file
            - narrator_speech_text: Optional text to convert to speech
            - voice: Optional voice to use for text-to-speech
            
    Returns:
        Dictionary containing:
            - narrator_audio_path: Path to the narrator audio file
            - audio_duration: Duration of the audio in seconds
            - speech_text: Original text used for speech (if applicable)
    """
    result = {
        "narrator_audio_path": None,
        "audio_duration": None,
        "speech_text": None
    }
    
    try:
        # Priority given to narrator_audio_url over narrator_speech_text
        if params.get("narrator_audio_url"):
            # Download existing narrator audio
            narrator_audio_url = params["narrator_audio_url"]
            narrator_audio_path, _ = await download_media_file(narrator_audio_url)
            
            # Verify the downloaded audio file is valid
            if not await verify_audio_file(narrator_audio_path):
                raise ValueError(f"Downloaded narrator audio file is not valid: {narrator_audio_path}")
            
            # Get audio duration
            audio_duration = await get_audio_duration(narrator_audio_path)
            
            result["narrator_audio_path"] = narrator_audio_path
            result["audio_duration"] = audio_duration
            
        # Only use narrator_speech_text if narrator_audio_url is not provided
        elif params.get("narrator_speech_text"):
            # Generate speech from text
            speech_text = params["narrator_speech_text"]
            voice = params.get("voice", "af_alloy")
            
            # Generate audio data
            logger.info(f"Generating speech with voice: {voice}")
            audio_data = await generate_speech(speech_text, voice)
            
            # Make sure the audio data is valid
            if not audio_data:
                logger.error("Failed to generate audio data - received empty response")
                raise ValueError("Text-to-speech service returned empty audio data")
            
            logger.info(f"Successfully generated audio data of size: {len(audio_data)} bytes")
            
            # Ensure temp directory exists
            temp_dir = "temp"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
                logger.info(f"Created temp directory: {temp_dir}")
                
            # Save to temp file
            narrator_audio_path = os.path.join(temp_dir, f"speech_{uuid.uuid4()}.mp3")
            
            try:
                with open(narrator_audio_path, "wb") as f:
                    f.write(audio_data)
                    # Explicitly sync to ensure file is fully written to disk
                    f.flush()
                    os.fsync(f.fileno())
                
                # Verify the audio file was created successfully
                if not os.path.exists(narrator_audio_path):
                    logger.error(f"Failed to create narrator audio file at {narrator_audio_path} despite no exception")
                    raise FileNotFoundError(f"Generated narrator audio file not found: {narrator_audio_path}")
                
                file_size = os.path.getsize(narrator_audio_path)
                logger.info(f"Successfully saved narrator audio file at {narrator_audio_path} with size: {file_size} bytes")
            except Exception as audio_write_err:
                logger.error(f"Error writing narrator audio file: {str(audio_write_err)}")
                raise RuntimeError(f"Failed to write narrator audio file: {str(audio_write_err)}")
            
            # Verify the audio file is valid
            if not await verify_audio_file(narrator_audio_path):
                raise ValueError(f"Generated narrator audio file is not valid: {narrator_audio_path}")
            
            # Get audio duration
            audio_duration = await get_audio_duration(narrator_audio_path)
            
            result["narrator_audio_path"] = narrator_audio_path
            result["audio_duration"] = audio_duration
            result["speech_text"] = speech_text
            
        return result
            
    except Exception as e:
        logger.error(f"Error processing narrator audio: {e}")
        raise

async def process_background_music(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process background music from URL or YouTube.
    
    Args:
        params: Dictionary containing:
            - background_music_url: URL of background music (can be YouTube)
            - background_music_vol: Volume level for background music (0-100)
            
    Returns:
        Dictionary containing:
            - background_music_path: Path to the background music file
            - background_music_duration: Duration of the background music in seconds
    """
    result = {
        "background_music_path": None,
        "background_music_duration": None
    }
    
    if not params.get("background_music_url"):
        return result
        
    try:
        background_music_url = params["background_music_url"]
        
        # Check if it's a YouTube URL
        if is_youtube_url(background_music_url):
            logger.info(f"Detected YouTube URL for background music: {background_music_url}")
            background_music_path, success = await download_youtube_audio(background_music_url)
            if not success:
                logger.error(f"Failed to download YouTube audio from {background_music_url}")
                return result
        else:
            # Regular audio file download
            background_music_path, _ = await download_media_file(background_music_url)
        
        # Verify the downloaded audio file is valid
        if not await verify_audio_file(background_music_path):
            logger.error(f"Downloaded background music file is not valid: {background_music_path}")
            return result
            
        # Get audio duration
        background_music_duration = await get_audio_duration(background_music_path)
        
        result["background_music_path"] = background_music_path
        result["background_music_duration"] = background_music_duration
        
        return result
            
    except Exception as e:
        logger.error(f"Error processing background music: {e}")
        return result

async def mix_audio_tracks(narrator_path: str, background_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mix narrator audio and background music.
    
    Args:
        narrator_path: Path to narrator audio file
        background_path: Path to background music file
        params: Dictionary containing:
            - narrator_vol: Volume level for narrator (0-100)
            - background_music_vol: Volume level for background music (0-100)
            
    Returns:
        Dictionary containing:
            - mixed_audio_path: Path to the mixed audio file
            - audio_duration: Duration of the mixed audio in seconds
    """
    result = {
        "mixed_audio_path": None,
        "audio_duration": None
    }
    
    if not narrator_path or not background_path:
        return result
        
    try:
        # Create a temporary file for the mixed audio
        temp_dir = "temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        mixed_audio_path = os.path.join(temp_dir, f"mixed_audio_{uuid.uuid4()}.m4a")
        
        # Get durations
        narrator_duration = await get_audio_duration(narrator_path)
        background_duration = await get_audio_duration(background_path)
        
        logger.info(f"Narrator audio duration: {narrator_duration} seconds")
        logger.info(f"Background music duration: {background_duration} seconds")
        
        # Get volume settings
        narrator_vol = params.get("narrator_vol", 100) / 100
        background_vol = params.get("background_music_vol", 20) / 100
        
        # Mix the audio using FFmpeg
        cmd = [
            "ffmpeg",
            "-y",
            "-i", narrator_path,
            "-stream_loop", "-1",  # Loop background music if needed
            "-i", background_path,
            "-filter_complex",
            f"[0:a]volume={narrator_vol}[a1];"
            f"[1:a]volume={background_vol}[a2];"
            f"[a1][a2]amix=inputs=2:duration=first[aout]",
            "-map", "[aout]",
            "-c:a", "aac",
            "-b:a", "192k",
            mixed_audio_path
        ]
        
        logger.info(f"Running FFmpeg command to mix audio: {' '.join(cmd)}")
        
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            logger.error(f"FFmpeg mixing error: {process.stderr}")
            return result
            
        if not os.path.exists(mixed_audio_path) or os.path.getsize(mixed_audio_path) == 0:
            logger.error(f"Mixed audio file was not created or is empty: {mixed_audio_path}")
            return result
            
        # Get mixed audio duration
        mixed_audio_duration = await get_audio_duration(mixed_audio_path)
        
        result["mixed_audio_path"] = mixed_audio_path
        result["audio_duration"] = mixed_audio_duration
        
        return result
            
    except Exception as e:
        logger.error(f"Error mixing audio tracks: {e}")
        return result 