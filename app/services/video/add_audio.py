"""
Service for adding audio to videos.

This service provides functionality to add background music or other audio to videos,
with control over volume levels and length matching. It supports both direct audio files
and YouTube audio sources, which are automatically downloaded and processed.

Features:
- Mix video and audio tracks with adjustable volume levels
- Match output length to either video or audio duration
- Loop video or audio to match the other's duration
- Support for YouTube links as audio sources
"""
import os
import time
import tempfile
import logging
import subprocess
from typing import Dict, Any, Tuple, Optional

from app.utils.media import download_media_file
from app.utils.youtube import is_youtube_url, download_youtube_audio
from app.utils.storage import storage_manager

# Configure logging
logger = logging.getLogger(__name__)

class AddAudioService:
    """
    Service for adding audio to videos.
    
    This service handles the process of adding audio tracks to video files,
    with options for controlling volume levels and duration matching. It supports
    direct audio files and YouTube audio sources.
    
    Features:
    - Adjustable volume levels for both video and audio tracks
    - Option to match final output length to either video or audio duration
    - Automatic looping of shorter tracks to match longer ones
    - YouTube audio extraction and processing
    """
    
    async def process_job(self, job_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a job to add audio to a video.
        
        This method handles the entire workflow of adding audio to a video:
        1. Download the video and audio files
        2. Mix them with specified volume levels
        3. Upload the result to S3
        
        Args:
            job_id: The ID of the job
            job_data: The job data, including:
                - video_url: URL of the video file
                - audio_url: URL of the audio file (can be direct file or YouTube)
                - video_volume: Volume level for the video track (0-100)
                - audio_volume: Volume level for the audio track (0-100)
                - match_length: Whether to match the output length to 'audio' or 'video'
            
        Returns:
            A dictionary with the results of the operation:
                - url: The URL of the resulting video
                - path: The S3 path of the resulting video
                - duration: The duration of the resulting video in seconds
            
        Raises:
            RuntimeError: If the operation fails at any step
        """
        logger.info(f"Processing add audio job {job_id}")
        
        # Extract job parameters
        video_url = job_data["video_url"]
        audio_url = job_data["audio_url"]
        video_volume = job_data.get("video_volume", 100)
        audio_volume = job_data.get("audio_volume", 50)
        match_length = job_data.get("match_length", "video")
        
        try:
            # Download video file
            logger.info(f"Downloading video from {video_url}")
            video_path, video_ext = await download_media_file(video_url)
            
            # Check if audio URL is from YouTube
            if is_youtube_url(audio_url):
                logger.info(f"YouTube audio URL detected: {audio_url}")
                audio_path, success = await download_youtube_audio(audio_url)
                if not success:
                    raise RuntimeError(f"Failed to download YouTube audio from {audio_url}")
            else:
                # Download audio file normally
                logger.info(f"Downloading audio from {audio_url}")
                audio_path, audio_ext = await download_media_file(audio_url)
            
            # Mix video and audio
            logger.info(f"Mixing video and audio with video volume {video_volume}% and audio volume {audio_volume}%")
            output_path, duration = await self._mix_video_audio(
                video_path=video_path,
                audio_path=audio_path,
                video_volume=video_volume,
                audio_volume=audio_volume,
                match_length=match_length
            )
            
            # Upload to S3
            logger.info(f"Uploading mixed video to S3")
            output_filename = f"mixed_video_{job_id}{video_ext}"
            s3_path = f"output/videos/{output_filename}"
            url = storage_manager.upload_file(output_path, s3_path)
            
            # Clean up temporary files
            for path in [video_path, audio_path, output_path]:
                if os.path.exists(path):
                    os.unlink(path)

           #remove signed url from s3
            url = url.split("?")[0]
            # Return result
            return {
                "url": url,
                "path": s3_path,
                "duration": duration
            }
        except Exception as e:
            logger.error(f"Error processing add audio job {job_id}: {e}")
            raise RuntimeError(f"Failed to add audio to video: {str(e)}")
    
    async def _mix_video_audio(self, video_path: str, audio_path: str, video_volume: int, 
                               audio_volume: int, match_length: str) -> Tuple[str, float]:
        """
        Mix video and audio files using FFmpeg.
        
        This method handles the actual mixing of video and audio tracks, with options
        for controlling volume levels and matching lengths between the two media files.
        
        Args:
            video_path: Path to the video file
            audio_path: Path to the audio file
            video_volume: Volume level for the video track (0-100)
            audio_volume: Volume level for the audio track (0-100)
            match_length: Whether to match the output length to the 'audio' or 'video'
            
        Returns:
            Tuple of (output path, duration in seconds)
            
        Raises:
            RuntimeError: If the FFmpeg operation fails
        """
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            # Get video and audio durations
            video_duration = self._get_media_duration(video_path)
            audio_duration = self._get_media_duration(audio_path)
            
            logger.info(f"Video duration: {video_duration} seconds")
            logger.info(f"Audio duration: {audio_duration} seconds")
            
            # Check if video has audio stream
            has_audio_stream = self._check_video_has_audio(video_path)
            logger.info(f"Video has audio stream: {has_audio_stream}")
            
            # Set the options based on the match_length parameter
            if match_length == "audio":
                # Audio will determine the output duration - always loop video to match audio
                cmd = self._build_ffmpeg_loop_video_command(
                    video_path, audio_path, output_path, 
                    video_volume, audio_volume, audio_duration,
                    has_audio_stream
                )
                final_duration = audio_duration
            else:  # match_length == "video"
                # Video will determine the output duration
                if video_duration > audio_duration:
                    # Loop audio to match video duration
                    cmd = self._build_ffmpeg_loop_audio_command(
                        video_path, audio_path, output_path, 
                        video_volume, audio_volume,
                        has_audio_stream
                    )
                else:
                    # Video is shorter or equal, trim audio
                    cmd = self._build_ffmpeg_standard_command(
                        video_path, audio_path, output_path, 
                        video_volume, audio_volume,
                        has_audio_stream
                    )
                final_duration = video_duration
            
            # Run the FFmpeg command
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                stderr = result.stderr if hasattr(result, 'stderr') else ""
                raise RuntimeError(f"Failed to create output video. FFmpeg error: {stderr}")
            
            # Return the output path and duration
            logger.info(f"Successfully mixed video and audio to {output_path}")
            return output_path, final_duration
        
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            if os.path.exists(output_path):
                os.unlink(output_path)
            raise RuntimeError(f"Failed to mix video and audio: {e.stderr}")
        except Exception as e:
            logger.error(f"Error mixing video and audio: {e}")
            if os.path.exists(output_path):
                os.unlink(output_path)
            raise
    
    def _get_media_duration(self, media_path: str) -> float:
        """
        Get the duration of a media file in seconds using FFprobe.
        
        Args:
            media_path: Path to the media file
            
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
                media_path
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
    
    def _check_video_has_audio(self, video_path: str) -> bool:
        """
        Check if a video file has an audio stream.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            True if the video has an audio stream, False otherwise
        """
        try:
            cmd = [
                "ffprobe", 
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            return result.stdout.strip() == "audio"
        except Exception as e:
            logger.error(f"Error checking for audio stream: {e}")
            return False
    
    def _build_ffmpeg_standard_command(self, video_path: str, audio_path: str, 
                                      output_path: str, video_volume: int, 
                                      audio_volume: int, has_audio_stream: bool = True) -> list:
        """
        Build a standard FFmpeg command for mixing video and audio.
        
        This command mixes the video and audio tracks with the specified volume levels,
        trimming to the shorter of the two durations.
        
        Args:
            video_path: Path to the video file
            audio_path: Path to the audio file
            output_path: Path to the output file
            video_volume: Volume level for the video track (0-100)
            audio_volume: Volume level for the audio track (0-100)
            has_audio_stream: Whether the video has an audio stream
            
        Returns:
            FFmpeg command as a list of strings
        """
        # Convert volume percentages to decimal
        video_vol = video_volume / 100
        audio_vol = audio_volume / 100
        
        if has_audio_stream:
            # Video has audio, mix both audio streams
            filter_complex = f"[0:a]volume={video_vol}[a1];[1:a]volume={audio_vol}[a2];[a1][a2]amix=inputs=2:duration=shortest[aout]"
        else:
            # Video doesn't have audio, just use the audio file with adjusted volume
            filter_complex = f"[1:a]volume={audio_vol}[aout]"
        
        return [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
    
    def _build_ffmpeg_loop_audio_command(self, video_path: str, audio_path: str, 
                                        output_path: str, video_volume: int, 
                                        audio_volume: int, has_audio_stream: bool = True) -> list:
        """
        Build an FFmpeg command for mixing video with looped audio.
        
        This command loops the audio track to match the video duration.
        
        Args:
            video_path: Path to the video file
            audio_path: Path to the audio file
            output_path: Path to the output file
            video_volume: Volume level for the video track (0-100)
            audio_volume: Volume level for the audio track (0-100)
            has_audio_stream: Whether the video has an audio stream
            
        Returns:
            FFmpeg command as a list of strings
        """
        # Convert volume percentages to decimal
        video_vol = video_volume / 100
        audio_vol = audio_volume / 100
        
        if has_audio_stream:
            # Video has audio, mix both audio streams
            filter_complex = f"[0:a]volume={video_vol}[a1];[1:a]volume={audio_vol}[a2];[a1][a2]amix=inputs=2:duration=first[aout]"
        else:
            # Video doesn't have audio, just use the audio file with adjusted volume
            filter_complex = f"[1:a]volume={audio_vol}[aout]"
        
        return [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-stream_loop", "-1",  # Loop audio infinitely
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
    
    def _build_ffmpeg_loop_video_command(self, video_path: str, audio_path: str, 
                                        output_path: str, video_volume: int, 
                                        audio_volume: int, duration: float,
                                        has_audio_stream: bool = True) -> list:
        """
        Build an FFmpeg command for mixing looped video with audio.
        
        This command loops the video track to match the audio duration.
        
        Args:
            video_path: Path to the video file
            audio_path: Path to the audio file
            output_path: Path to the output file
            video_volume: Volume level for the video track (0-100)
            audio_volume: Volume level for the audio track (0-100)
            duration: The target duration in seconds
            has_audio_stream: Whether the video has an audio stream
            
        Returns:
            FFmpeg command as a list of strings
        """
        # Convert volume percentages to decimal
        video_vol = video_volume / 100
        audio_vol = audio_volume / 100
        
        if has_audio_stream:
            # Video has audio, mix both audio streams
            filter_complex = f"[0:a]volume={video_vol}[a1];[1:a]volume={audio_vol}[a2];[a1][a2]amix=inputs=2:duration=first[aout]"
        else:
            # Video doesn't have audio, just use the audio file with adjusted volume
            filter_complex = f"[1:a]volume={audio_vol}[aout]"
        
        return [
            "ffmpeg",
            "-y",
            "-stream_loop", "-1",  # Loop video infinitely
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-t", str(duration),  # Limit to audio duration
            output_path
        ]


# Create service instance
add_audio_service = AddAudioService() 