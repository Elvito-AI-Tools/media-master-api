"""
FastAPI application for media generation.
"""
from fastapi import FastAPI, Depends
import os
import asyncio
import logging
from dotenv import load_dotenv
from fastapi.openapi.models import SecurityScheme
from fastapi.openapi.utils import get_openapi

# Load environment variables from .env file if it exists
load_dotenv()

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Load environment variables again and log them
logger.info("Loaded environment variables")
logger.info(f"AWS_REGION: {os.environ.get('AWS_REGION', 'Not set')}")
logger.info(f"AWS_BUCKET_NAME: {os.environ.get('AWS_BUCKET_NAME', 'Not set')}")
logger.info(f"LOG_LEVEL: {os.environ.get('LOG_LEVEL', 'Not set')}")
logger.info(f"DEBUG: {os.environ.get('DEBUG', 'Not set')}")
logger.info(f"KOKORO_API_URL: {os.environ.get('KOKORO_API_URL', 'http://kokoro-tts:8880/v1/audio/speech')}")

# Import authentication
from app.utils.auth import get_api_key

# Import routers
from app.routes.image.image_to_video import router as image_to_video_router
from app.routes.audio.text_to_speech import router as text_to_speech_router
from app.routes.media.transcription import router as media_transcription_router
from app.routes.video import router as video_router

# Create application
app = FastAPI(
    title="Media Master API",
    description="API for generating media content without coding",
    version="0.1.0"
)

# Add API key security scheme to OpenAPI documentation
app.openapi_schema = None  # Reset schema to rebuild it
app.swagger_ui_init_oauth = None
app.openapi_tags = [
    {"name": "auth", "description": "Authentication endpoints"},
    {"name": "image", "description": "Image processing endpoints"},
    {"name": "audio", "description": "Audio processing endpoints"},
    {"name": "media", "description": "Media processing endpoints"},
    {"name": "video", "description": "Video processing endpoints"},
]

def custom_openapi():
    if app.openapi_schema:  # Use the cached schema if it exists
        return app.openapi_schema

    # Create the base OpenAPI schema
    openapi_schema = get_openapi(
        title="Media Master API",
        version="1.0.0",
        description="API for media processing and transformation",
        routes=app.routes,
    )

    # Customize the schema as needed
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }

    # Cache the schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Replace FastAPI's default openapi() with our custom one
app.openapi = custom_openapi

# Ensure temporary files directory exists
os.makedirs("temp", exist_ok=True)
os.makedirs("temp/output", exist_ok=True)

# Include routers with authentication dependency
app.include_router(image_to_video_router, dependencies=[Depends(get_api_key)])
app.include_router(text_to_speech_router, dependencies=[Depends(get_api_key)])
app.include_router(media_transcription_router, dependencies=[Depends(get_api_key)])
app.include_router(video_router, prefix="/v1/video", dependencies=[Depends(get_api_key)])

# Add API key information to the root endpoint
@app.get("/")
async def read_root():
    """Root endpoint."""
    return {
        "message": "Welcome to Media Master API",
        "authentication": "Please include your API key in the X-API-Key header for all requests",
        "docs": "/docs",
        "operations": {
            "image_to_video": {
                "create_job": "/v1/image/to-video",
                "get_job_status": "/v1/image/to-video/{job_id}"
            },
            "text_to_speech": {
                "create_job": "/v1/audio/text-to-speech",
                "get_job_status": "/v1/audio/text-to-speech/{job_id}"
            },
            "media_transcription": {
                "create_job": "/v1/media/transcription",
                "get_job_status": "/v1/media/transcription/{job_id}"
            },
            "video": {
                "concatenate": {
                    "create_job": "/v1/video/concatenate",
                    "get_job_status": "/v1/video/concatenate/{job_id}"
                },
                "add_audio": {
                    "create_job": "/v1/video/add-audio",
                    "get_job_status": "/v1/video/add-audio/{job_id}"
                }
            }
        }
    }


@app.on_event("startup")
async def startup_event():
    """Run startup events."""
    # Import job queue service to initialize it
    from app.services.job_queue import job_queue
    logging.info("Job queue initialized with max size: %d", job_queue.max_queue_size)


@app.on_event("shutdown")
async def shutdown_event():
    """Run shutdown events."""
    # Import job queue service
    from app.services.job_queue import job_queue
    
    # Clean up resources
    for task in job_queue.processing_tasks.values():
        task.cancel()
    
    logging.info("All job processing tasks cancelled")


if __name__ == "__main__":
    import uvicorn
    
    # Use multiple workers to better handle concurrent requests
    # Workers should be 2-4 times the number of CPU cores
    workers = int(os.environ.get("UVICORN_WORKERS", 4))
    
    # In development, use a single worker with reload=True
    if os.environ.get("DEBUG", "False").lower() == "true":
        uvicorn.run(
            "app.main:app", 
            host="0.0.0.0", 
            port=8000, 
            reload=True
        )
    else:
        # In production, use multiple workers with no reload
        uvicorn.run(
            "app.main:app", 
            host="0.0.0.0", 
            port=8000, 
            workers=workers
        ) 