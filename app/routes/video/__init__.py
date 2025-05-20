"""
Routes for video manipulation operations.
"""
from fastapi import APIRouter

from app.routes.video.concatenate import router as concatenate_router
from app.routes.video.add_audio import router as add_audio_router
from app.routes.video.add_captions import router as add_captions_router

# Create a main router that includes all video-related routes
router = APIRouter()
router.include_router(concatenate_router)
router.include_router(add_audio_router)
router.include_router(add_captions_router) 