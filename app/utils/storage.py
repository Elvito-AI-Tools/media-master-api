"""
Storage utilities for managing video files on AWS S3.
"""
import os
import json
import uuid
import logging
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)

class S3StorageManager:
    """
    Class to manage uploads to AWS S3.
    """
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one S3 instance is created."""
        if cls._instance is None:
            cls._instance = super(S3StorageManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize AWS S3 client."""
        if self._initialized:
            return
            
        try:
            # Initialize S3 client using environment variables
            # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION are automatically used by boto3
            self.s3_client = boto3.client('s3')
            
            self.bucket_name = os.getenv("AWS_BUCKET_NAME")
            
            # Check if the bucket exists
            if self.bucket_name:
                try:
                    self.s3_client.head_bucket(Bucket=self.bucket_name)
                    self._initialized = True
                    logger.info(f"AWS S3 initialized successfully with bucket: {self.bucket_name}")
                except ClientError as e:
                    logger.error(f"Failed to access AWS S3 bucket '{self.bucket_name}': {e}")
                    self._initialized = False
            else:
                logger.error("AWS_BUCKET_NAME environment variable is not set")
                self._initialized = False
                
        except Exception as e:
            logger.error(f"Failed to initialize AWS S3: {e}")
            self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if S3 is properly initialized."""
        return self._initialized
    
    def reinitialize(self) -> bool:
        """
        Attempt to reinitialize the S3 connection.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        self._initialized = False
        try:
            # Initialize S3 client using environment variables
            self.s3_client = boto3.client('s3')
            
            self.bucket_name = os.getenv("AWS_BUCKET_NAME")
            
            # Check if the bucket exists
            if self.bucket_name:
                try:
                    self.s3_client.head_bucket(Bucket=self.bucket_name)
                    self._initialized = True
                    logger.info(f"AWS S3 reinitialized successfully with bucket: {self.bucket_name}")
                    return True
                except ClientError as e:
                    logger.error(f"Failed to access AWS S3 bucket '{self.bucket_name}' during reinitialization: {e}")
            else:
                logger.error("S3 bucket name not set in environment variables")
        except Exception as e:
            logger.error(f"Failed to reinitialize AWS S3: {e}")
            
        return False
    
    def upload_video(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
        """
        Upload a video file to AWS S3.
        
        Args:
            file_path: Path to the video file
            metadata: Optional metadata for the file
            
        Returns:
            Dict containing URLs and metadata, or None if upload failed
        """
        if not self.is_initialized:
            logger.error("AWS S3 not initialized, cannot upload")
            return None
            
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        try:
            # Generate unique ID for the file
            file_id = str(uuid.uuid4())
            file_name = os.path.basename(file_path)
            
            # Extract file extension
            _, file_extension = os.path.splitext(file_name)
            
            # Create a storage path - videos/{YYYY-MM-DD}/{uuid}.{ext}
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            destination_path = f"videos/{today}/{file_id}{file_extension}"
            
            # Set content type
            content_type = "video/mp4"
            if file_extension.lower() == ".webm":
                content_type = "video/webm"
            elif file_extension.lower() == ".mov":
                content_type = "video/quicktime"
            
            # Convert metadata to fit S3 format if provided
            s3_metadata = {}
            if metadata:
                # S3 metadata keys must be strings and values must be strings
                for key, value in metadata.items():
                    s3_metadata[key] = str(value)
            
            # Upload to S3
            with open(file_path, 'rb') as file_data:
                self.s3_client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    destination_path,
                    ExtraArgs={
                        'ContentType': content_type,
                        'Metadata': s3_metadata
                    }
                )
            
            # Generate the public URL
            region = os.getenv("AWS_REGION", "us-east-1")
            
            # Get URL generation method - either direct (if bucket is public) or presigned
            url_type = os.getenv("S3_URL_TYPE", "direct").lower()
            
            if url_type == "presigned":
                # Generate a presigned URL that expires in 7 days (604800 seconds)
                try:
                    public_url = self.s3_client.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': self.bucket_name,
                            'Key': destination_path
                        },
                        ExpiresIn=604800  # 7 days in seconds
                    )
                except Exception as e:
                    logger.error(f"Failed to generate presigned URL: {e}")
                    # Fall back to direct URL
                    if region == "us-east-1":
                        public_url = f"https://{self.bucket_name}.s3.amazonaws.com/{destination_path}"
                    else:
                        public_url = f"https://{self.bucket_name}.s3.{region}.amazonaws.com/{destination_path}"
            else:
                # Direct URL (works if bucket has public access)
                if region == "us-east-1":
                    # Standard endpoint for us-east-1
                    public_url = f"https://{self.bucket_name}.s3.amazonaws.com/{destination_path}"
                else:
                    # Region-specific endpoint
                    public_url = f"https://{self.bucket_name}.s3.{region}.amazonaws.com/{destination_path}"
            
            logger.info(f"Video uploaded successfully to {destination_path}")
            logger.info(f"Generated URL: {public_url}")
            
            # Return URLs and metadata
            return {
                "url": public_url,
                "path": destination_path,
                "name": file_name,
                "id": file_id,
                "uploaded_at": datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to upload video to AWS S3: {e}")
            return None
    
    def delete_video(self, storage_path: str) -> bool:
        """
        Delete a video from AWS S3.
        
        Args:
            storage_path: The path to the object in S3
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.is_initialized:
            logger.error("AWS S3 not initialized, cannot delete")
            return False
            
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=storage_path
            )
            logger.info(f"Video deleted successfully from {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete video from AWS S3: {e}")
            return False

# Global storage manager instance
storage_manager = S3StorageManager() 