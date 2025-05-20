import os
from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException, status
from urllib.parse import urlparse
from datetime import timedelta
from typing import Dict
import uuid

class Storage:
    def __init__(self):
        endpoint = os.getenv("S3_ENDPOINT_URL", "").replace("http://", "").replace("https://", "")
        region = os.getenv("S3_REGION")
        
        # Determine if we're using AWS S3 or MinIO
        is_aws = not endpoint.startswith("minio")
        
        # For AWS S3, use the standard endpoint format if none provided
        if is_aws and not endpoint:
            endpoint = f"s3.{region}.amazonaws.com" if region else "s3.amazonaws.com"
        
        self.client = Minio(
            endpoint=endpoint,
            access_key=os.getenv("S3_ACCESS_KEY"),
            secret_key=os.getenv("S3_SECRET_KEY"),
            region=region,
            secure=is_aws  # True for AWS S3, False for local MinIO
        )
        self.bucket_name = os.getenv("S3_BUCKET_NAME")
        self.ensure_bucket_exists()

    def reinitialize(self) -> bool:
        """
        Attempt to reinitialize the connection to S3.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            endpoint = os.getenv("S3_ENDPOINT_URL", "").replace("http://", "").replace("https://", "")
            region = os.getenv("S3_REGION")
            
            # Determine if we're using AWS S3 or MinIO
            is_aws = not endpoint.startswith("minio")
            
            # For AWS S3, use the standard endpoint format if none provided
            if is_aws and not endpoint:
                endpoint = f"s3.{region}.amazonaws.com" if region else "s3.amazonaws.com"
            
            self.client = Minio(
                endpoint=endpoint,
                access_key=os.getenv("S3_ACCESS_KEY"),
                secret_key=os.getenv("S3_SECRET_KEY"),
                region=region,
                secure=is_aws  # True for AWS S3, False for local MinIO
            )
            self.bucket_name = os.getenv("S3_BUCKET_NAME")
            self.ensure_bucket_exists()
            return True
        except Exception as e:
            print(f"Failed to reinitialize storage: {e}")
            return False

    def ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Storage error: {err.message}"
            )

    def upload_file(self, file_path: str, object_name: str):
        try:
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=file_path,
            )
            return self.get_file_url(object_name)
        except S3Error as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload error: {err.message}"
            )

    def upload_video(self, file_path: str, metadata: Dict[str, str] = None) -> Dict[str, str]:
        """
        Upload a video file to S3 with metadata.
        
        Args:
            file_path: Path to the video file
            metadata: Optional metadata to attach to the object
            
        Returns:
            Dictionary with URL and path information
        """
        try:
            # Generate a unique object name for the video
            filename = os.path.basename(file_path)
            object_name = f"videos/{uuid.uuid4()}-{filename}"
            
            # Upload to S3 with metadata if provided
            if metadata:
                self.client.fput_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    file_path=file_path,
                    metadata=metadata
                )
            else:
                self.client.fput_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    file_path=file_path
                )
                
            # Get a URL for the uploaded file
            url = self.get_file_url(object_name)
            
            # Remove signature parameters from URL if present
            if '?' in url:
                clean_url = url.split('?')[0]
            else:
                clean_url = url
                
            return {
                "url": clean_url,
                "path": object_name
            }
        except S3Error as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video upload error: {err.message}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during video upload: {str(e)}"
            )

    def get_file_url(self, object_name: str):
        try:
            # Generate presigned URL that's valid for 7 days
            return self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(days=7)
            )
        except S3Error as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"URL generation error: {err.message}"
            )

    def delete_file(self, object_name: str):
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
        except S3Error as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Delete error: {err.message}"
            )

# Create the storage manager instance
storage_manager = Storage()