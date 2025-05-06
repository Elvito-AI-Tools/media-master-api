"""
Authentication utilities for API key verification.
"""
import os
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
import logging

logger = logging.getLogger(__name__)

# Define API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Get API key from environment variable
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    logger.warning("API_KEY environment variable is not set. Authentication is disabled.")


async def get_api_key(api_key_header: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """
    Validate the API key from the X-API-Key header.
    
    Args:
        api_key_header: API key from request header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    # If API_KEY is not set in environment, skip authentication
    if not API_KEY:
        logger.warning("API authentication bypassed: No API_KEY set in environment")
        return "authentication_disabled"
    
    # Check if API key is provided in header
    if not api_key_header:
        raise HTTPException(
            status_code=401,
            detail="Missing API Key. Please provide a valid API key in the X-API-Key header."
        )
    
    # Validate API key
    if api_key_header != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key. Please provide a valid API key in the X-API-Key header."
        )
    
    return api_key_header 