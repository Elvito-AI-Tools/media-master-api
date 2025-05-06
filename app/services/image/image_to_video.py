"""
Media processor service to generate videos from images with audio and captions 
using a streamlined FFmpeg pipeline.

This service reduces S3 uploads/downloads by combining multiple operations into fewer FFmpeg commands.
"""
import os
import uuid
import logging
import json
import asyncio
import subprocess
import tempfile
from PIL import Image
from typing import Dict, Any, Tuple, Optional, List

from app.services.s3 import s3_service
from app.services.audio.text_to_speech import generate_speech
from app.utils.media import download_media_file
from app.utils.download import download_image
from app.services.media.transcription import transcription_service
from app.utils.captions import (
    create_srt_from_text, 
    prepare_subtitle_styling,
    create_srt_from_word_timestamps,
)

# Configure logging
logger = logging.getLogger(__name__)

class ImageToVideoService:
    """
    Service for generating videos from images with audio and captions in an optimized way.
    
    This service combines multiple operations (image to video, audio generation, 
    captioning) into fewer FFmpeg commands, reducing the need for S3 roundtrips.
    """
    
    def __init__(self):
        """Initialize the optimized media processor service."""
        self.executor = asyncio.get_event_loop().run_in_executor
        logger.info("Optimized media processor service initialized")
    

    
    async def create_video_with_audio_captions(self, 
                                             image_path: str,
                                             video_length: float,
                                             frame_rate: int,
                                             zoom_speed: float,
                                             audio_path: Optional[str] = None,
                                             srt_path: Optional[str] = None,
                                             caption_properties: Optional[Dict] = None,
                                             match_length: str = "audio") -> str:
        """
        Create video from image with optional audio and captions in a single optimized pipeline.
        
        Args:
            image_path: Path to the input image
            video_length: Length of output video in seconds
            frame_rate: Frame rate of output video
            zoom_speed: Speed of zoom effect (0-100)
            audio_path: Path to the audio file (optional)
            srt_path: Path to the SRT or ASS subtitle file (optional)
            caption_properties: Caption styling properties (optional)
            match_length: Whether to match the output length to 'audio' or 'video'
            
        Returns:
            Path to the final output video
        """
        try:
            # Verify input files exist
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Input image file not found: {image_path}")
                
            if audio_path and not os.path.exists(audio_path):
                raise FileNotFoundError(f"Input audio file not found: {audio_path}")
                
            if srt_path and not os.path.exists(srt_path):
                raise FileNotFoundError(f"Input subtitle file not found: {srt_path}")
            
            # Get image dimensions for optimal output settings
            with Image.open(image_path) as img:
                width, height = img.size
            logger.info(f"Original image dimensions: {width}x{height}")
            
            # Calculate total frames
            total_frames = int(frame_rate * video_length)
            
            # Normalize zoom_speed to a reasonable range (0.1 to 0.5 per second)
            zoom_speed_normalized = (zoom_speed / 100.0) * 0.4 + 0.1
            
            # Calculate final zoom factor
            zoom_factor = 1 + (zoom_speed_normalized * video_length)
            
            # Determine orientation and set dimensions
            if width > height:  # Landscape orientation
                scale_dims = "7680x4320"  # 8K landscape dimensions (note: using 'x' instead of ':')
                output_dims = "1920x1080"  # Full HD
            else:  # Portrait orientation
                scale_dims = "4320x7680"  # 8K portrait dimensions
                output_dims = "1080x1920"  # Full HD vertical video
            
            # Create output path
            output_path = os.path.join("temp", f"optimized_{uuid.uuid4()}.mp4")
            
            # Basic filter for zoom effect
            filter_complex = [
                f"scale={scale_dims},"
                f"zoompan=z='min(1+({zoom_speed_normalized}*{video_length})*on/{total_frames}, {zoom_factor})':"
                f"d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"s={output_dims},fps={frame_rate}"
            ]
            
            # Start building FFmpeg command - check if we'll need to loop the video first
            loop_video = False
            audio_duration = None
            if audio_path:
                # Get audio duration
                audio_info_cmd = [
                    "ffprobe", 
                    "-v", "error", 
                    "-show_entries", "format=duration", 
                    "-of", "json", 
                    audio_path
                ]
                audio_info_result = subprocess.run(
                    audio_info_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if audio_info_result.returncode == 0:
                    audio_info = json.loads(audio_info_result.stdout)
                    audio_duration = float(audio_info["format"]["duration"])
                    logger.info(f"Audio duration: {audio_duration}s")
                    
                    # Check if we need to loop the video
                    if match_length == "audio" and audio_duration > video_length:
                        loop_video = True
            
            # Build the actual command
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output if exists
            ]
            
            # Add stream loop BEFORE the image input if needed
            if loop_video:
                cmd.extend(["-stream_loop", "-1"])  # Loop video infinitely
                
            # Add image input
            cmd.extend([
                "-framerate", str(frame_rate),  # Set input framerate
                "-loop", "1",  # Loop the input
                "-i", image_path,  # Input image
            ])
            
            # Add audio input if provided
            if audio_path:
                cmd.extend(["-i", audio_path])
                
                # Determine final video duration based on match_length
                final_duration = audio_duration if match_length == "audio" else video_length
            else:
                # No audio, just use video length
                final_duration = video_length
            
            # Add subtitles if provided
            if srt_path:
                # Check if it's an ASS file or standard SRT
                is_ass = srt_path.lower().endswith('.ass')
                
                if is_ass:
                    # For ASS subtitles, we can directly use the file
                    # Using ASS subtitles requires a separate input and filter
                    cmd.extend(["-i", srt_path])
                    
                    # Add the ASS subtitle to the filter chain using overlay
                    filter_complex.append(f"ass='{srt_path}'")
                else:
                    # Prepare subtitle styling
                    style_options = prepare_subtitle_styling(caption_properties)
                    subtitle_filter = f"subtitles='{srt_path}'"
                    
                    if style_options:
                        # Convert dictionary to style string
                        style_parts = [f"{key}={value}" for key, value in style_options.items()]
                        force_style = ','.join(style_parts)
                        subtitle_filter += f":force_style='{force_style}'"
                    
                    # Add subtitle filter
                    filter_complex.append(subtitle_filter)
            
            # Combine all filters
            if len(filter_complex) > 1:
                cmd.extend(["-filter_complex", ",".join(filter_complex)])
            else:
                cmd.extend(["-vf", filter_complex[0]])
            
            # Add audio mapping if needed
            if audio_path:
                cmd.extend(["-map", "0:v"])  # Map video from first input
                cmd.extend(["-map", "1:a"])  # Map audio from second input
                cmd.extend(["-c:a", "aac"])  # Audio codec
            
            # Add output settings
            cmd.extend([
                "-c:v", "libx264",  # Video codec
                "-r", str(frame_rate),  # Output framerate
                "-pix_fmt", "yuv420p",  # Pixel format
                "-preset", "medium",  # Quality preset
                "-crf", "23",  # Quality level
                "-t", str(final_duration),  # Duration
                "-movflags", "+faststart",  # Optimize for web
                output_path  # Output file
            ])
            
            # Log the command
            logger.info(f"Running optimized FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg command
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
            
            # Check if output was created
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Output video was not created at {output_path}")
            
            logger.info(f"Successfully created optimized video at {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error in create_video_with_audio_captions: {e}")
            raise
    
    async def verify_audio_file(self, audio_path: str) -> bool:
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

    async def image_to_video(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an optimized image-to-video conversion with audio and captions in one pipeline.
        
        Args:
            params: Job parameters
                - image_url: URL of the image to convert
                - video_length: Length of the output video in seconds
                - frame_rate: Frame rate of the output video
                - zoom_speed: Speed of the zoom effect (0-100)
                - audio_url: URL of audio file to add (prioritized over speech_text)
                - speech_text: Text to convert to speech (used only if audio_url is not provided)
                - voice: Voice to use for speech synthesis (when using speech_text)
                - audio_vol: Volume level for the audio track (0-100)
                - should_add_captions: Whether to add captions
                - caption_properties: Styling properties for captions (optional)
                - match_length: Whether to match output length to 'audio' or 'video'
                
        Returns:
            Dictionary with result information
        """
        # Track created files for cleanup
        temp_files = []
        result = {
            "has_audio": False,
            "has_captions": False
        }
        
        try:
            # Extract parameters
            image_url = params["image_url"]
            video_length = params.get("video_length", 10.0)
            frame_rate = params.get("frame_rate", 30)
            zoom_speed = params.get("zoom_speed", 10.0)
            match_length = params.get("match_length", "audio")
            
            # Download image
            image_path = await download_image(image_url, temp_dir="temp")
            temp_files.append(image_path)
            
            # Process audio
            audio_path = None
            speech_text = None
            srt_path = None
            audio_duration = None
            
            # Priority given to audio_url over speech_text
            if params.get("audio_url"):
                # Download existing audio
                audio_url = params["audio_url"]
                audio_path, _ = await download_media_file(audio_url)
                temp_files.append(audio_path)
                
                # Verify the downloaded audio file is valid
                if not await self.verify_audio_file(audio_path):
                    raise ValueError(f"Downloaded audio file is not valid: {audio_path}")
                
                result["has_audio"] = True
                
                # Handle captions for external audio
                if params.get("should_add_captions", False):
                    try:
                        # Get max_words_per_line and style
                        max_words_per_line = 10  # Default
                        style = "highlight"  # Default caption style
                        if params.get("caption_properties"):
                            if "max_words_per_line" in params["caption_properties"]:
                                max_words_per_line = params["caption_properties"]["max_words_per_line"]
                            if "style" in params["caption_properties"]:
                                style = params["caption_properties"]["style"]
                        
                        # For highlight style and similar timed styles, we need word-level timestamps
                        need_word_timestamps = style in ["highlight", "word_by_word"]
                        
                        # Verify the audio file exists before attempting transcription
                        if not os.path.exists(audio_path):
                            logger.error(f"External audio file not found for transcription: {audio_path}")
                            raise FileNotFoundError(f"External audio file not found for transcription: {audio_path}")
                        
                        # Make a copy of the audio file for transcription to prevent it from being deleted
                        temp_dir = "temp"
                        if not os.path.exists(temp_dir):
                            os.makedirs(temp_dir, exist_ok=True)
                            
                        transcription_audio_path = os.path.join(temp_dir, f"transcribe_{uuid.uuid4()}.mp3")
                        try:
                            import shutil
                            shutil.copy2(audio_path, transcription_audio_path)
                            logger.info(f"Created copy of external audio for transcription: {transcription_audio_path}")
                            temp_files.append(transcription_audio_path)  # Add to cleanup list
                        except Exception as copy_err:
                            logger.error(f"Failed to copy external audio for transcription: {str(copy_err)}")
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
                            # For highlight style, we might need to create our own ASS file
                            # from the transcription results if the SRT doesn't support it
                            if style in ["highlight", "word_by_word"] and "text" in transcription_result:
                                # Generate a custom ASS file with appropriate style
                                try:
                                    # Get audio duration if not already available
                                    if audio_duration is None:
                                        audio_info_cmd = [
                                            "ffprobe", 
                                            "-v", "error", 
                                            "-show_entries", "format=duration", 
                                            "-of", "json", 
                                            audio_path
                                        ]
                                        audio_info_result = subprocess.run(
                                            audio_info_cmd,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            text=True
                                        )
                                        if audio_info_result.returncode == 0:
                                            audio_info = json.loads(audio_info_result.stdout)
                                            audio_duration = float(audio_info["format"]["duration"])
                                        else:
                                            audio_duration = video_length
                                    
                                    # Create appropriate styled subtitle based on available data
                                    if need_word_timestamps and "words" in transcription_result:
                                        # We have word timestamps, use them for precise styling
                                        srt_path = await create_srt_from_word_timestamps(
                                            transcription_result["words"],
                                            audio_duration,
                                            max_words_per_line,
                                            style,
                                            caption_properties=params.get("caption_properties")
                                        )
                                        logger.info(f"Created custom {style} style subtitle file using precise word timestamps")
                                    else:
                                        # No word timestamps, use text-based approach
                                        words = transcription_result["text"].split()
                                        srt_path = await create_srt_from_text(
                                            transcription_result["text"],
                                            audio_duration,
                                            max_words_per_line,
                                            style
                                        )
                                        logger.info(f"Created custom {style} style subtitle file for external audio")
                                except Exception as sub_e:
                                    logger.error(f"Error creating custom subtitle: {str(sub_e)}")
                                    # Fall back to the standard SRT from transcription
                                    srt_path = await caption_service.download_subtitle_file(transcription_result["srt_url"])
                                    logger.info("Falling back to standard SRT from transcription")
                            else:
                                # For non-highlight styles, use highlight style as default
                                srt_path = await caption_service.download_subtitle_file(transcription_result["srt_url"])
                                logger.info("Using highlight style as the default for subtitles")
                            
                            temp_files.append(srt_path)
                            result["has_captions"] = True
                            result["srt_url"] = transcription_result["srt_url"]
                    except Exception as e:
                        logger.error(f"Error transcribing audio for captions: {e}")
                        # Continue without captions
                        logger.info("Continuing without captions")
            
            # Only use speech_text if audio_url is not provided
            elif params.get("speech_text"):
                # Generate speech from text
                speech_text = params["speech_text"]
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
                audio_path = os.path.join(temp_dir, f"speech_{uuid.uuid4()}.mp3")
                
                try:
                    with open(audio_path, "wb") as f:
                        f.write(audio_data)
                        # Explicitly sync to ensure file is fully written to disk
                        f.flush()
                        os.fsync(f.fileno())
                    
                    # Verify the audio file was created successfully
                    if not os.path.exists(audio_path):
                        logger.error(f"Failed to create audio file at {audio_path} despite no exception")
                        raise FileNotFoundError(f"Generated audio file not found: {audio_path}")
                    
                    file_size = os.path.getsize(audio_path)
                    logger.info(f"Successfully saved audio file at {audio_path} with size: {file_size} bytes")
                except Exception as audio_write_err:
                    logger.error(f"Error writing audio file: {str(audio_write_err)}")
                    raise RuntimeError(f"Failed to write audio file: {str(audio_write_err)}")
                
                # Verify the audio file is valid
                if not await self.verify_audio_file(audio_path):
                    raise ValueError(f"Generated audio file is not valid: {audio_path}")
                
                # Add to temp_files after successful creation and verification
                temp_files.append(audio_path)
                result["has_audio"] = True
                
                # Create SRT file from speech text if captions requested
                if params.get("should_add_captions", False):
                    # Get duration from audio file
                    audio_info_cmd = [
                        "ffprobe", 
                        "-v", "error", 
                        "-show_entries", "format=duration", 
                        "-of", "json", 
                        audio_path
                    ]
                    audio_info_result = subprocess.run(
                        audio_info_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    if audio_info_result.returncode == 0:
                        audio_info = json.loads(audio_info_result.stdout)
                        audio_duration = float(audio_info["format"]["duration"])
                    else:
                        # If we can't get duration, use video length
                        audio_duration = video_length
                    
                    # Get max_words_per_line and style
                    max_words_per_line = 10  # Default
                    style = "highlight"  # Default caption style
                    if params.get("caption_properties"):
                        if "max_words_per_line" in params["caption_properties"]:
                            max_words_per_line = params["caption_properties"]["max_words_per_line"]
                        if "style" in params["caption_properties"]:
                            style = params["caption_properties"]["style"]
                    
                    # For advanced caption styles, we might need word-level timestamps
                    need_word_timestamps = True
                    
                        # Transcribe the generated audio to get word-level timestamps
                    try:
                            # Verify the audio file exists before attempting transcription
                            if not os.path.exists(audio_path):
                                logger.error(f"Audio file not found for transcription: {audio_path}")
                                raise FileNotFoundError(f"Audio file not found for transcription: {audio_path}")
                                
                            # Make a copy of the audio file for transcription to prevent it from being deleted
                            transcription_audio_path = os.path.join(temp_dir, f"transcribe_{uuid.uuid4()}.mp3")
                            try:
                                import shutil
                                shutil.copy2(audio_path, transcription_audio_path)
                                logger.info(f"Created copy of audio file for transcription: {transcription_audio_path}")
                                temp_files.append(transcription_audio_path)  # Add to cleanup list
                            except Exception as copy_err:
                                logger.error(f"Failed to copy audio file for transcription: {str(copy_err)}")
                                # Fall back to using the original file if copy fails
                                transcription_audio_path = audio_path
                                
                            logger.info(f"Transcribing generated speech for precise word timestamps with style: {style}")
                            transcription_result = await transcription_service.transcribe(
                                transcription_audio_path,
                                include_text=True,
                                include_srt=False,  # We'll create our own styled SRT
                                word_timestamps=True,
                                max_words_per_line=max_words_per_line
                            )
                            
                            if "words" in transcription_result:
                                # Create styled subtitles using word timestamps
                                srt_path = await create_srt_from_word_timestamps(
                                    transcription_result["words"],
                                    audio_duration,
                                    max_words_per_line,
                                    style,
                                    caption_properties=params.get("caption_properties")
                                )
                                logger.info(f"Created custom {style} style subtitle file for generated speech using word timestamps")
                            else:
                                # For unsupported styles, use highlight style
                                srt_path = await create_srt_from_word_timestamps(
                                    transcription_result["words"],
                                    audio_duration,
                                    max_words_per_line,
                                    "highlight",
                                    caption_properties=params.get("caption_properties")
                                )
                            
                            temp_files.append(srt_path)
                            result["has_captions"] = True
                    except Exception as sub_e:
                            logger.error(f"Error creating word-timed captions: {str(sub_e)}")
                            # Fall back to highlight style without word timestamps
                            srt_path = await create_srt_from_text(
                                speech_text, 
                                audio_duration, 
                                max_words_per_line,
                                "highlight"
                            )
                            logger.info(f"Falling back to highlight style captions without word timestamps")

                    
                    temp_files.append(srt_path)
                    result["has_captions"] = True
            
            # Create the final video in one optimized operation
            caption_properties = params.get("caption_properties") if params.get("should_add_captions") else None
            
            # Verify all required files exist before proceeding
            if image_path and not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                raise FileNotFoundError(f"Image file not found: {image_path}")
                
            if audio_path and not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
                
            if srt_path and not os.path.exists(srt_path):
                logger.error(f"Subtitle file not found: {srt_path}")
                raise FileNotFoundError(f"Subtitle file not found: {srt_path}")
            
            logger.info(f"All input files verified. Running FFmpeg with image: {image_path}, audio: {audio_path}, subtitles: {srt_path}")
            
            output_path = await self.create_video_with_audio_captions(
                image_path=image_path,
                video_length=video_length,
                frame_rate=frame_rate,
                zoom_speed=zoom_speed,
                audio_path=audio_path,
                srt_path=srt_path,
                caption_properties=caption_properties,
                match_length=match_length
            )
            temp_files.append(output_path)
            
            # Upload to S3
            object_name = f"videos/{uuid.uuid4()}.mp4"
            result_url = await s3_service.upload_file(output_path, object_name)
            
            # Add final result info
            result["final_video_url"] = result_url
            
            # Get video duration from output
            video_info_cmd = [
                "ffprobe", 
                "-v", "error", 
                "-show_entries", "format=duration", 
                "-of", "json", 
                output_path
            ]
            video_info_result = subprocess.run(
                video_info_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if video_info_result.returncode == 0:
                video_info = json.loads(video_info_result.stdout)
                result["video_duration"] = float(video_info["format"]["duration"])
            else:
                # Fallback to expected duration
                if audio_path and match_length == "audio":
                    result["video_duration"] = audio_duration or video_length
                else:
                    result["video_duration"] = video_length
            
            return result
        
        except Exception as e:
            logger.error(f"Error in process_optimized_image_to_video: {e}")
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
                elif file_path:
                    logger.warning(f"Temporary file not found during cleanup: {file_path}")

# Create a singleton instance
image_to_video_service = ImageToVideoService() 