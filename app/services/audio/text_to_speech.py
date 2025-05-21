"""
Service for converting text to speech using external Kokoro TTS API.
"""
import os
import uuid
import asyncio
import logging
import json
import aiohttp
from app.utils.storage import storage_manager

# Configure logging
logger = logging.getLogger(__name__)

# Kokoro API settings
KOKORO_API_URL = os.environ.get("KOKORO_API_URL", "http://kokoro-tts:8880/v1/audio/speech")
KOKORO_TIMEOUT = int(os.environ.get("KOKORO_TIMEOUT", "30"))  # seconds

async def generate_speech(
    text: str,
    voice: str = "af_alloy",
) -> bytes:
    """
    Generate speech from text using the external Kokoro TTS API.
    
    Args:
        text: Text to convert to speech
        voice: Name of the Kokoro voice to use
        
    Returns:
        Audio data bytes
    """
    try:
        logger.info(f"Calling Kokoro TTS service with voice: {voice}")
        
        # Prepare request data - MUST use "input" for text
        data = {
            "input": text,  # API expects "input", not "text"
            "voice": voice,
        }
        
        # Log exact request details for debugging
        logger.info(f"Kokoro API URL: {KOKORO_API_URL}")
        logger.info(f"Sending request to Kokoro API with data: {json.dumps(data)}")
        
        # Call the Kokoro API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                KOKORO_API_URL, 
                json=data,  # This sends the data as JSON in the request body
                timeout=KOKORO_TIMEOUT
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Kokoro API error {response.status}: {error_text}")
                    # Also log headers for debugging
                    logger.error(f"Request headers: {response.request_info.headers}")
                    logger.error(f"Response headers: {response.headers}")
                    raise ValueError(f"Kokoro API returned {response.status}: {error_text}")
                
                # Read the audio data
                audio_data = await response.read()
                logger.info(f"Received {len(audio_data)} bytes of audio data from Kokoro API")
                return audio_data
                
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to Kokoro API: {e}")
        raise ValueError(f"Failed to connect to Kokoro API: {e}")
    except Exception as e:
        logger.error(f"Unexpected error calling Kokoro API: {e}")
        raise ValueError(f"Failed to generate speech with Kokoro: {e}")


async def process_text_to_speech(params: dict) -> dict:
    """
    Process text to speech conversion as a job using Kokoro TTS API.
    
    Args:
        params: Job parameters
            - text: Text to convert to speech
            - voice: Name of the Kokoro voice to use
            
    Returns:
        Dictionary with the result
            - audio_url: URL of the generated audio file
            - tts_engine: The TTS engine used (kokoro)
            - voice: The voice used for synthesis
    """
    text = params.get("text")
    voice = params.get("voice", "af_alloy")
    
    if not text:
        raise ValueError("Text parameter is required")
    
    # Track created files for cleanup
    created_files = []
    audio_url = None
    
    try:
        # Generate a unique output filename
        mp3_filename = f"{uuid.uuid4()}.mp3"
        mp3_output_path = f"temp/output/{mp3_filename}"
        
        # Make sure output directory exists
        os.makedirs(os.path.dirname(mp3_output_path), exist_ok=True)
        
        # Log the parameters being sent to the API
        logger.info(f"Sending to Kokoro TTS API - Text: '{text}', Voice: '{voice}'")
        
        # Get the audio data from Kokoro API
        audio_data = await generate_speech(text, voice)
        
        # Save the audio data to file
        with open(mp3_output_path, 'wb') as f:
            f.write(audio_data)
        
        created_files.append(mp3_output_path)
        logger.info(f"Saved audio data to {mp3_output_path}")
        
        # Upload to S3
        s3_key = f"audio/{mp3_filename}"
        audio_url  = storage_manager.upload_file(mp3_output_path, s3_key)
    
        
        logger.info(f"Audio file uploaded to S3 with URL: {audio_url}")

        #remove signed url from s3
        audio_url = audio_url.split("?")[0]
        

        # Return the result
        return {
            "audio_url": audio_url,
            "audio_path": s3_key,
            "tts_engine": "kokoro",
            "voice": voice
        }
        
    except Exception as e:
        logger.error(f"Error processing text to speech: {e}")
        raise
    finally:
        # Only clean up temporary files if we've successfully uploaded to S3
        if audio_url:
            logger.info("Cleaning up temporary files")
            for path in created_files:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.info(f"Removed temporary file: {path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove temporary file {path}: {e}")
        else:
            logger.warning("Keeping temporary files for debugging as upload failed") 