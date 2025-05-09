import os
from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException, status
from urllib.parse import urlparse
from datetime import timedelta

class Storage:
    def __init__(self):
        self.client = Minio(
            endpoint=os.getenv("S3_ENDPOINT_URL").replace("http://", "").replace("https://", ""),
            access_key=os.getenv("S3_ACCESS_KEY"),
            secret_key=os.getenv("S3_SECRET_KEY"),
            secure=False  # Set to True if using https
        )
        self.bucket_name = os.getenv("S3_BUCKET_NAME")
        self.ensure_bucket_exists()

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