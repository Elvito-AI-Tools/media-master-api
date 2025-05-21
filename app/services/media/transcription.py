"""
Service for transcribing media files using Whisper.
"""
import os
import json
import logging
import tempfile
import subprocess
from urllib.parse import urlparse
import whisper
from typing import Dict, Any, Tuple, List, Optional
import asyncio
import concurrent.futures

from app.utils.media import download_media_file, SUPPORTED_FORMATS
from app.utils.storage import storage_manager

# Configure logging
logger = logging.getLogger(__name__)

# Define supported file extensions - imported from utils.media now
SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg']
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.webm', '.mov', '.avi', '.mkv']
SUPPORTED_FORMATS = SUPPORTED_AUDIO_FORMATS + SUPPORTED_VIDEO_FORMATS

# Whisper model cache location
WHISPER_MODEL_DIR = os.environ.get("WHISPER_MODEL_DIR", os.path.expanduser("~/.cache/whisper"))
os.makedirs(WHISPER_MODEL_DIR, exist_ok=True)

class TranscriptionService:
    """Service for transcribing media files using Whisper."""
    
    def __init__(self):
        """Initialize the transcription service."""
        # Initialize models dict to load models on demand
        self.models = {}
        # Thread pool for running transcription tasks
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        logger.info("Transcription service initialized")
    
    def _get_model(self, model_name: str = "base"):
        """Get or load a Whisper model."""
        if model_name not in self.models:
            logger.info(f"Loading Whisper model: {model_name}")
            try:
                self.models[model_name] = whisper.load_model(model_name, download_root=WHISPER_MODEL_DIR)
                logger.info(f"Successfully loaded Whisper model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load Whisper model {model_name}: {e}")
                raise RuntimeError(f"Failed to load Whisper model: {e}")
        
        return self.models[model_name]
    
    async def download_media(self, media_url: str) -> Tuple[str, str]:
        """
        Download media file from URL.
        
        Args:
            media_url: URL of the media file
            
        Returns:
            Tuple of (local file path, file extension)
        """
        # Use the common media download utility function
        return await download_media_file(media_url, temp_dir="temp")
    
    def _run_transcription(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run transcription in a separate thread.
        
        Args:
            file_path: Path to media file
            options: Transcription options
            
        Returns:
            Transcription result
        """
        # Get appropriate model (use 'base' by default)
        model = self._get_model("base")
        logger.info(f"Starting transcription of {file_path}")
        
        # Perform transcription
        result = model.transcribe(file_path, **options)
        logger.info(f"Transcription completed successfully")
        return result
    
    async def transcribe(
        self, 
        file_path: str, 
        include_text: bool = True,
        include_srt: bool = True,
        word_timestamps: bool = False,
        language: Optional[str] = None,
        max_words_per_line: int = 10
    ) -> Dict[str, Any]:
        """
        Transcribe media file using Whisper.
        
        Args:
            file_path: Path to media file
            include_text: Whether to include plain text transcription in the result
            include_srt: Whether to include SRT format
            word_timestamps: Whether to include word-level timestamps
            language: Source language code (optional)
            max_words_per_line: Maximum number of words per line in SRT (default: 10)
            
        Returns:
            Dict containing the transcription results
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Set transcription options
            options = {
                "verbose": False,
                "word_timestamps": word_timestamps
            }
            
            # Add language option if specified
            if language:
                options["language"] = language
            
            # Run transcription in a separate thread to avoid blocking the event loop
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self._run_transcription(file_path, options)
            )
            
            # Prepare response
            response = {}
            
            # Include text if requested
            if include_text:
                response["text"] = result["text"]
            
            # Include word timestamps if requested
            if word_timestamps and "segments" in result:
                words = []
                for segment in result["segments"]:
                    if "words" in segment:
                        words.extend(segment["words"])
                response["words"] = words
            
            # Generate and save SRT if requested
            if include_srt:
                srt_path = file_path + ".srt"
                self._generate_srt(result, srt_path, max_words_per_line)
                
                # Upload SRT to S3
                srt_object_name = os.path.basename(srt_path)
                srt_url = storage_manager.upload_file(srt_path, f"transcriptions/{srt_object_name}")

                # Remove signature parameters from URL
                if '?' in srt_url:
                    srt_url = srt_url.split('?')[0]
                
                response["srt_url"] = srt_url
                
                # Delete local SRT file
                os.unlink(srt_path)
            
            return response
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {e}")
        finally:
            # Clean up the downloaded file
            if os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    logger.info(f"Deleted temporary file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {file_path}: {e}")
    
    def _generate_srt(self, transcription: Dict[str, Any], output_path: str, max_words_per_line: int = 10):
        """
        Generate SRT file from transcription result with controlled line length.
        
        Args:
            transcription: Whisper transcription result
            output_path: Path to save the SRT file
            max_words_per_line: Maximum number of words per line (default: 10)
        """
        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(transcription["segments"], start=1):
                start_time = self._format_timestamp(segment["start"])
                end_time = self._format_timestamp(segment["end"])
                text = segment["text"].strip()
                
                # Apply max words per line formatting
                formatted_text = self._format_text_with_max_words(text, max_words_per_line)
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{formatted_text}\n\n")
        
        logger.info(f"Generated SRT file with max {max_words_per_line} words per line: {output_path}")
    
    def _format_text_with_max_words(self, text: str, max_words_per_line: int) -> str:
        """
        Format text with a maximum number of words per line.
        
        Args:
            text: The text to format
            max_words_per_line: Maximum number of words per line
            
        Returns:
            Formatted text with line breaks
        """
        words = text.split()
        if len(words) <= max_words_per_line:
            return text
        
        formatted_lines = []
        for i in range(0, len(words), max_words_per_line):
            line = ' '.join(words[i:i+max_words_per_line])
            formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format seconds as SRT timestamp: HH:MM:SS,mmm
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"


# Create a singleton instance
transcription_service = TranscriptionService() 