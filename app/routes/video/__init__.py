"""
Routes for video manipulation operations.
"""
from fastapi import APIRouter

from app.routes.video.concatenate import router as concatenate_router

# Create a main router that includes all video-related routes
router = APIRouter()
router.include_router(concatenate_router) 