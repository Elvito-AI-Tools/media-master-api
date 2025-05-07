"""
Utility functions for working with YouTube content.

This module provides functions for extracting audio from YouTube videos
and other YouTube-related operations.
"""
import os
import re
import tempfile
import logging
import subprocess
from typing import Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

def is_youtube_url(url: str) -> bool:
    """
    Check if a URL is from YouTube.
    
    Args:
        url: The URL to check
        
    Returns:
        True if the URL is from YouTube, False otherwise
    """
    youtube_pattern = r'(youtube\.com|youtu\.be)'
    return bool(re.search(youtube_pattern, url))

async def download_youtube_audio(url: str, temp_dir: str = "temp") -> Tuple[str, bool]:
    """
    Download audio from a YouTube video.
    
    Args:
        url: YouTube URL
        temp_dir: Directory to save the temporary file
        
    Returns:
        Tuple of (path to downloaded audio file, success status)
        
    Raises:
        RuntimeError: If the download fails
    """
    # Ensure temp directory exists
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"Created temp directory: {temp_dir}")
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=temp_dir)
    audio_path = temp_file.name
    temp_file.close()
    
    logger.info(f"YouTube audio URL detected: {url}")
    logger.info(f"Downloading audio using yt-dlp directly to {audio_path}")
    
    # Verify audio_path is valid before proceeding
    if not audio_path:
        raise RuntimeError("Failed to create temporary audio file path")
    
    logger.info(f"Temporary audio file path: {audio_path}")
    
    # Run yt-dlp to extract audio in MP3 format
    cmd = [
        "yt-dlp",
        "-x",  # Extract audio
        "--audio-format", "mp3",
        "--extract-audio",  # Make sure we're extracting audio
        "--audio-quality", "0",  # Best quality
        "--no-playlist",  # Don't download playlists
        "--no-continue",  # Don't resume partial downloads
        "--force-overwrites",  # Overwrite existing files
        "-o", audio_path,  # Use explicit path variable
        url
    ]
    
    logger.info(f"Executing yt-dlp command: {' '.join(cmd)}")
    
    try:
        # Execute the command
        process_result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=300)
        
        # Log yt-dlp output regardless of success/failure
        if process_result.stdout:
            logger.info(f"yt-dlp stdout:\n{process_result.stdout.strip()}")
        if process_result.stderr:
            logger.info(f"yt-dlp stderr:\n{process_result.stderr.strip()}")
        
        # Check if the file exists and has content, regardless of exit code
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            logger.info(f"Audio file successfully created at {audio_path} "
                      f"(Size: {os.path.getsize(audio_path)} bytes)")
            return audio_path, True
        else:
            raise RuntimeError(f"yt-dlp failed to create audio file. "
                             f"Exit code: {process_result.returncode}, "
                             f"stderr: {process_result.stderr.strip()}")
    
    except subprocess.TimeoutExpired as e:
        logger.error(f"yt-dlp command timed out after {e.timeout} seconds.")
        stdout_decoded = e.stdout.decode(errors='replace').strip() if e.stdout else "N/A"
        stderr_decoded = e.stderr.decode(errors='replace').strip() if e.stderr else "N/A"
        logger.error(f"yt-dlp stdout (if any):\n{stdout_decoded}")
        logger.error(f"yt-dlp stderr (if any):\n{stderr_decoded}")
        if os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except OSError as e_unlink:
                logger.warning(f"Could not remove temporary audio file {audio_path} after timeout: {e_unlink}")
        raise RuntimeError(f"yt-dlp command timed out.") from e
    except Exception as e:
        logger.error(f"Error downloading YouTube audio: {str(e)}")
        if os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except OSError as e_unlink:
                logger.warning(f"Could not remove temporary audio file {audio_path}: {e_unlink}")
        raise RuntimeError(f"Failed to download YouTube audio: {str(e)}") 