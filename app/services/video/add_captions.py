"""
Service for adding captions to videos.
"""
import os
import uuid
import logging
import json
import tempfile
import subprocess
import asyncio
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urlparse

from app.utils.media import download_media_file, download_subtitle_file
from app.utils.storage import storage_manager
from app.utils.captions import prepare_subtitle_styling, create_srt_from_text, create_srt_from_word_timestamps
from app.services.media.transcription import transcription_service

# Configure logging
logger = logging.getLogger(__name__)

class AddCaptionsService:
    """Service for adding captions to videos."""
    
    async def add_captions_to_video(
        self,
        video_path: str,
        captions_path: str,
        caption_properties: Optional[Dict] = None
    ) -> str:
        """
        Add captions to a video.
        
        Args:
            video_path: Path to the video file
            captions_path: Path to the captions file (SRT or ASS)
            caption_properties: Dictionary of caption styling properties
            
        Returns:
            Path to the output video with captions
        """
        try:
            # Get file extension to determine if it's SRT or ASS
            captions_ext = os.path.splitext(captions_path)[1].lower()
            # Create output directory if it doesn't exist
            os.makedirs("temp/output", exist_ok=True)
            
            # Create output path
            output_path = os.path.join("temp/output", f"captioned_{uuid.uuid4()}.mp4")
            
            # Prepare subtitle styling options
            style_options = prepare_subtitle_styling(caption_properties)
            
            # For both SRT and ASS files, use the subtitles filter
            if captions_ext == '.ass':
                # For ASS subtitles, use the ass filter which offers better styling
                subtitle_filter = f"ass='{captions_path}'"
            else:
                # For SRT files, use subtitle filter with styling
                subtitle_filter = f"subtitles='{captions_path}'"
                
                if style_options:
                    # Convert dictionary to style string
                    style_parts = []
                    
                    # Handle font specially - check if we need to add font lookup path
                    if 'FontName' in style_options:
                        font_name = style_options['FontName']
                        # First try adding the font name directly
                        style_parts.append(f"fontname={font_name}")
                        
                        # Check if we should also provide a font path hint
                        try:
                            # Try to find the font file path
                            font_path_cmd = ["fc-match", "-v", font_name]
                            font_match_result = subprocess.run(
                                font_path_cmd,
                                capture_output=True,
                                text=True
                            )
                            
                            # Log the font match results for debugging
                            logger.info(f"Font match result for '{font_name}':\n{font_match_result.stdout}")
                            
                            # Alternatively, add the default font directory path hint
                            font_dirs = [
                                "/usr/share/fonts/truetype/custom",
                                "/usr/share/fonts",
                                "/usr/local/share/fonts"
                            ]
                            for font_dir in font_dirs:
                                if os.path.exists(font_dir):
                                    subtitle_filter += f":fontsdir='{font_dir}'"
                                    logger.info(f"Added font directory hint: {font_dir}")
                                    break
                        except Exception as e:
                            logger.warning(f"Error getting font path: {e}")
                    
                    # Add all other style options
                    for key, value in style_options.items():
                        if key != 'FontName':  # Skip font name as we've already handled it
                            style_parts.append(f"{key}={value}")
                    
                    # Add the force_style parameter
                    force_style = ','.join(style_parts)
                    subtitle_filter += f":force_style='{force_style}'"
            
            # Build the command using the filter
            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-vf", subtitle_filter,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "copy",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output_path
            ]
            
            # Log the command
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                logger.error(f"FFmpeg error: {error_msg}")
                raise RuntimeError(f"FFmpeg command failed: {error_msg}")
            
            # Check if output file was created
            if not os.path.exists(output_path):
                raise RuntimeError(f"Output file was not created: {output_path}")
                
            logger.info(f"Successfully added captions to video: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error in add_captions_to_video: {e}")
            raise
    
    async def process_job(self, job_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a job to add captions to a video.
        
        Args:
            job_id: The ID of the job
            params: Job parameters
                - video_url: URL of the video to add captions to
                - captions: Text content for captions, URL to SRT/ASS file, or None to use audio
                - caption_properties: Styling properties for captions (optional)
                
        Returns:
            Dictionary with result information
        """
        # Track created files for cleanup
        temp_files = []
        
        try:
            # Extract parameters
            video_url = params["video_url"]
            captions = params.get("captions")
            caption_properties = params.get("caption_properties")
            
            # Download video
            video_path, _ = await download_media_file(video_url)
            temp_files.append(video_path)
            
            # Variable to hold captions path
            captions_path = None
            srt_url = None
            
            # Process captions - could be raw text, SRT/ASS file URL, or None (use audio)
            if captions:
                # Check if captions is a URL
                try:
                    parsed_url = urlparse(captions)
                    if parsed_url.scheme and parsed_url.netloc:
                        # It's a URL, download the file
                        captions_path = await download_subtitle_file(captions)
                        temp_files.append(captions_path)
                        srt_url = captions
                        
                        # If it's an SRT file and style is highlight, we may want to convert it to ASS
                        # for better styling, but we'll leave as is for now
                        captions_ext = os.path.splitext(captions_path)[1].lower()
                        if captions_ext == '.srt' and caption_properties and caption_properties.get("style") in ["highlight", "word_by_word"]:
                            logger.info(f"Downloaded SRT file for {caption_properties.get('style')} style. Using as is, but ASS would give better results.")
                    else:
                        # It's raw text, create SRT file
                        # Get video duration
                        duration = self._get_media_duration(video_path)
                        
                        # Get style and max_words_per_line
                        max_words_per_line = 10  # Default
                        style = "highlight"  # Default caption style
                        
                        if caption_properties:
                            if "max_words_per_line" in caption_properties:
                                max_words_per_line = caption_properties["max_words_per_line"]
                            if "style" in caption_properties:
                                style = caption_properties["style"]
                        
                        # For highlight style, create artificial word timestamps for better rendering
                        if style == "highlight" or style == "word_by_word":
                            # Split text into words
                            words = captions.split()
                            word_count = len(words)
                            
                            if word_count > 0:
                                # Create artificial word timestamps by distributing evenly
                                seconds_per_word = duration / word_count
                                
                                # Create word timestamps array
                                word_timestamps = []
                                for i, word in enumerate(words):
                                    start_time = i * seconds_per_word
                                    end_time = (i + 1) * seconds_per_word
                                    word_timestamps.append({
                                        "word": word,
                                        "start": start_time,
                                        "end": end_time
                                    })
                                
                                # Use the appropriate function for creating captions
                                captions_path = await create_srt_from_word_timestamps(
                                    word_timestamps,
                                    duration,
                                    max_words_per_line,
                                    style,
                                    caption_properties=caption_properties
                                )
                                logger.info(f"Created {style} style captions from text using artificial word timestamps")
                            else:
                                # No words, just use simple SRT
                                captions_path = await create_srt_from_text(
                                    captions, 
                                    duration, 
                                    max_words_per_line,
                                    style
                                )
                                logger.info(f"Created simple captions with empty text")
                        else:
                            # For other styles, use simpler approach
                            captions_path = await create_srt_from_text(
                                captions, 
                                duration, 
                                max_words_per_line,
                                style
                            )
                            logger.info(f"Created {style} style captions from text")
                        
                        temp_files.append(captions_path)
                except Exception as e:
                    logger.error(f"Error processing captions URL/text: {e}")
                    # Assume it's raw text if URL parsing fails
                    # Get video duration
                    duration = self._get_media_duration(video_path)
                    
                    # Get style and max_words_per_line
                    max_words_per_line = 10  # Default
                    style = "highlight"  # Default caption style
                    
                    if caption_properties:
                        if "max_words_per_line" in caption_properties:
                            max_words_per_line = caption_properties["max_words_per_line"]
                        if "style" in caption_properties:
                            style = caption_properties["style"]
                    
                    # For highlight style, create artificial word timestamps for better rendering
                    if style == "highlight" or style == "word_by_word":
                        # Split text into words
                        words = captions.split()
                        word_count = len(words)
                        
                        if word_count > 0:
                            # Create artificial word timestamps by distributing evenly
                            seconds_per_word = duration / word_count
                            
                            # Create word timestamps array
                            word_timestamps = []
                            for i, word in enumerate(words):
                                start_time = i * seconds_per_word
                                end_time = (i + 1) * seconds_per_word
                                word_timestamps.append({
                                    "word": word,
                                    "start": start_time,
                                    "end": end_time
                                })
                            
                            # Use the appropriate function for creating captions
                            captions_path = await create_srt_from_word_timestamps(
                                word_timestamps,
                                duration,
                                max_words_per_line,
                                style,
                                caption_properties=caption_properties
                            )
                            logger.info(f"Created {style} style captions from text using artificial word timestamps (fallback)")
                        else:
                            # No words, just use simple SRT
                            captions_path = await create_srt_from_text(
                                captions, 
                                duration, 
                                max_words_per_line,
                                style
                            )
                            logger.info(f"Created simple captions with empty text (fallback)")
                    else:
                        # For other styles, use simpler approach
                        captions_path = await create_srt_from_text(
                            captions, 
                            duration, 
                            max_words_per_line,
                            style
                        )
                        logger.info(f"Created {style} style captions from text (fallback)")
                    
                    temp_files.append(captions_path)
            else:
                # No captions provided, transcribe the audio from the video
                logger.info("No captions provided, transcribing audio from video")
                
                # Create a temporary file for the extracted audio
                temp_dir = "temp"
                audio_path = os.path.join(temp_dir, f"extracted_audio_{uuid.uuid4()}.mp3")
                
                # Extract audio from video
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", video_path,
                    "-vn",
                    "-c:a", "libmp3lame",
                    "-q:a", "4",
                    audio_path
                ]
                
                # Run FFmpeg
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Failed to extract audio: {result.stderr}")
                    raise RuntimeError(f"Failed to extract audio from video: {result.stderr}")
                
                temp_files.append(audio_path)
                
                # Get audio duration
                audio_duration = self._get_media_duration(audio_path)
                logger.info(f"Audio duration: {audio_duration} seconds")
                
                # Get max_words_per_line and style
                max_words_per_line = 10  # Default
                style = "highlight"  # Default caption style
                
                if caption_properties:
                    if "max_words_per_line" in caption_properties:
                        max_words_per_line = caption_properties["max_words_per_line"]
                    if "style" in caption_properties:
                        style = caption_properties["style"]
                
                # For highlight and word_by_word styles, we need word-level timestamps
                need_word_timestamps = style in ["highlight", "word_by_word"]
                
                # Transcribe the audio file
                transcription_result = await transcription_service.transcribe(
                    audio_path,
                    include_text=True,
                    include_srt=not need_word_timestamps,  # Only get SRT from service if not using word timestamps
                    word_timestamps=need_word_timestamps,
                    max_words_per_line=max_words_per_line
                )
                
                # Log transcription result keys for debugging
                logger.info(f"Transcription result contains keys: {', '.join(transcription_result.keys())}")
                
                if need_word_timestamps and "words" in transcription_result:
                    # Create styled subtitles using word timestamps for highlight and word_by_word styles
                    captions_path = await create_srt_from_word_timestamps(
                        transcription_result["words"],
                        audio_duration,
                        max_words_per_line,
                        style,
                        caption_properties=caption_properties
                    )
                    temp_files.append(captions_path)
                    logger.info(f"Created {style} style captions using word timestamps from transcription")
                    
                    # Set srt_url if available in transcription result
                    if "srt_url" in transcription_result:
                        srt_url = transcription_result["srt_url"]
                elif "srt_url" in transcription_result:
                    # Download the SRT file for other styles
                    captions_path = await download_subtitle_file(transcription_result["srt_url"])
                    temp_files.append(captions_path)
                    srt_url = transcription_result["srt_url"]
                    logger.info(f"Downloaded SRT file for {style} style captions")
                else:
                    # If we don't have word timestamps but need them for highlight style,
                    # use text from transcription to create artificial timestamps
                    if need_word_timestamps and "text" in transcription_result:
                        text = transcription_result["text"]
                        words = text.split()
                        word_count = len(words)
                        
                        if word_count > 0:
                            # Create artificial word timestamps by distributing evenly
                            seconds_per_word = audio_duration / word_count
                            
                            # Create word timestamps array
                            word_timestamps = []
                            for i, word in enumerate(words):
                                start_time = i * seconds_per_word
                                end_time = (i + 1) * seconds_per_word
                                word_timestamps.append({
                                    "word": word,
                                    "start": start_time,
                                    "end": end_time
                                })
                            
                            # Use the appropriate function for creating captions
                            captions_path = await create_srt_from_word_timestamps(
                                word_timestamps,
                                audio_duration,
                                max_words_per_line,
                                style,
                                caption_properties=caption_properties
                            )
                            temp_files.append(captions_path)
                            logger.info(f"Created {style} style captions using artificial word timestamps from transcription text")
                        else:
                            raise RuntimeError("Transcription text is empty")
                    else:
                        raise RuntimeError("Transcription failed to generate subtitles")
            
            # Add captions to video
            output_path = await self.add_captions_to_video(
                video_path=video_path,
                captions_path=captions_path,
                caption_properties=caption_properties
            )
            temp_files.append(output_path)
            
            # Upload to S3
            object_name = f"videos/captioned_{uuid.uuid4()}.mp4"
            result_url = storage_manager.upload_file(output_path, object_name)
            
            # Get video info
            video_info = self._get_video_info(output_path)

            video_info["url"] = result_url

            # remove the signature from the url
            video_info["url"] = video_info["url"].split("?")[0]
            
            # Prepare response
            result = {
                "url": video_info["url"],
                "path": object_name,
                "duration": video_info.get("duration", 0),
                "width": video_info.get("width", 0),
                "height": video_info.get("height", 0)
            }
            
            # Add SRT URL if available
            if srt_url:
                result["srt_url"] = srt_url
            
            return result
            
        except Exception as e:
            logger.error(f"Error in process_job: {e}")
            raise
        finally:
            # Clean up temporary files
            for file_path in temp_files:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed temporary file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove temporary file {file_path}: {e}")
    
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
    
    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get video information (duration, width, height) using FFprobe.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary with video information
            
        Raises:
            RuntimeError: If the FFprobe operation fails
        """
        try:
            # Use FFprobe to get video information
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height:format=duration",
                "-of", "json",
                video_path
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            info = json.loads(result.stdout)
            
            video_info = {}
            
            # Get duration
            if "format" in info and "duration" in info["format"]:
                video_info["duration"] = float(info["format"]["duration"])
            
            # Get width and height
            if "streams" in info and len(info["streams"]) > 0:
                stream = info["streams"][0]
                if "width" in stream:
                    video_info["width"] = stream["width"]
                if "height" in stream:
                    video_info["height"] = stream["height"]
            
            return video_info
        except subprocess.CalledProcessError as e:
            logger.error(f"FFprobe error: {e.stderr}")
            raise RuntimeError(f"Failed to get video information: {e.stderr}")
        except Exception as e:
            logger.error(f"Error getting video information: {e}")
            raise RuntimeError(f"Failed to get video information: {str(e)}")

# Create a singleton instance
add_captions_service = AddCaptionsService() 