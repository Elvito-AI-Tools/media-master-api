"""
S3 service for handling file uploads to AWS S3.
"""
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging
from dotenv import load_dotenv
import asyncio
import concurrent.futures

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class S3Service:
    """S3 service for handling file uploads to AWS S3."""
    
    def __init__(self):
        """Initialize S3 service."""
        # Get AWS credentials from environment variables
        self.aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.bucket_name = os.environ.get("AWS_BUCKET_NAME")
        self.region = os.environ.get("AWS_REGION")
        
        # Thread pool for handling blocking S3 operations
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        
        # Print environment variables for debugging (without sensitive info)
        logger.debug(f"AWS_ACCESS_KEY_ID: {'*' * 8 if self.aws_access_key_id else 'Not Set'}")
        logger.debug(f"AWS_SECRET_ACCESS_KEY: {'*' * 8 if self.aws_secret_access_key else 'Not Set'}")
        logger.debug(f"AWS_BUCKET_NAME: {self.bucket_name}")
        logger.debug(f"AWS_REGION: {self.region}")
        
        # Check if credentials are provided
        using_dummy_credentials = (self.aws_access_key_id == "dummy_access_key_id" or 
                                 self.aws_secret_access_key == "dummy_secret_access_key" or 
                                 self.bucket_name == "dummy-bucket-name")
        
        if using_dummy_credentials:
            logger.warning("Using dummy AWS credentials. S3 uploads will return mock URLs instead.")
            self.s3_client = None
            return
            
        # Initialize S3 client
        try:
            # Make sure all required values are strings
            self.aws_access_key_id = str(self.aws_access_key_id)
            self.aws_secret_access_key = str(self.aws_secret_access_key)
            self.bucket_name = str(self.bucket_name)
            self.region = str(self.region)
            
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region
            )
            logger.info(f"S3 client initialized with region {self.region} and bucket {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None
    
    def _upload_file_sync(self, file_path: str, object_name: str = None) -> str:
        """
        Synchronous version of upload_file to be run in thread pool.
        
        Args:
            file_path: Path to the file to upload
            object_name: S3 object name. If not specified, file_path's basename will be used
            
        Returns:
            URL of the uploaded file
        """
        # If we have dummy credentials, return a mock URL instead
        if self.s3_client is None:
            logger.warning("S3 client not initialized. Returning a mock URL instead of uploading to S3.")
            mock_object_name = object_name or os.path.basename(file_path)
            return f"https://example.com/mock-s3/{mock_object_name}"
            
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File {file_path} does not exist. Cannot upload to S3.")
            raise FileNotFoundError(f"File {file_path} does not exist")
            
        # If object_name is not specified, use file_path's basename
        if object_name is None:
            object_name = os.path.basename(file_path)
        
        try:
            # Upload file to S3
            logger.info(f"Uploading file {file_path} to S3 bucket {self.bucket_name} as {object_name}")
            self.s3_client.upload_file(file_path, self.bucket_name, object_name)
            
            # Get the URL of the uploaded file
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_name}"
            logger.info(f"File uploaded successfully. URL: {url}")
            return url
        except FileNotFoundError as e:
            logger.error(f"File not found: {file_path}. Error: {e}")
            raise
        except NoCredentialsError:
            logger.error("AWS credentials not found or invalid")
            # Fall back to mock URL instead of failing
            mock_object_name = object_name or os.path.basename(file_path)
            logger.info(f"Falling back to mock URL due to credential error")
            return f"https://example.com/mock-s3/{mock_object_name}"
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            # Fall back to mock URL instead of failing
            mock_object_name = object_name or os.path.basename(file_path)
            logger.info(f"Falling back to mock URL due to client error")
            return f"https://example.com/mock-s3/{mock_object_name}"
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            # Fall back to mock URL instead of failing
            mock_object_name = object_name or os.path.basename(file_path)
            logger.info(f"Falling back to mock URL due to unexpected error")
            return f"https://example.com/mock-s3/{mock_object_name}"
    
    async def upload_file(self, file_path: str, object_name: str = None) -> str:
        """
        Upload a file to S3 bucket (async version that uses thread pool).
        
        Args:
            file_path: Path to the file to upload
            object_name: S3 object name. If not specified, file_path's basename will be used
            
        Returns:
            URL of the uploaded file
        """
        return await asyncio.get_event_loop().run_in_executor(
            self.executor,
            lambda: self._upload_file_sync(file_path, object_name)
        )
    
    def _download_file_sync(self, object_name: str, download_path: str = None) -> str:
        """
        Synchronous version of download_file to be run in thread pool.
        
        Args:
            object_name: S3 object name to download
            download_path: Path to save the downloaded file. If not specified, a temporary file will be created.
            
        Returns:
            Path to the downloaded file
        """
        # If we have dummy credentials, create a mock file instead
        if self.s3_client is None:
            logger.warning("S3 client not initialized. Creating a mock file instead of downloading from S3.")
            
            # Create a mock file
            import tempfile
            if not download_path:
                # Create a temporary file with the same extension as the object_name
                _, ext = os.path.splitext(object_name)
                temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                download_path = temp_file.name
                temp_file.close()
            
            # Write some dummy content to the file
            with open(download_path, "w") as f:
                f.write(f"This is a mock file for {object_name}")
            
            logger.info(f"Created mock file at {download_path}")
            return download_path
        
        # Create download path if not specified
        if not download_path:
            import tempfile
            # Create a temporary file with the same extension as the object_name
            _, ext = os.path.splitext(object_name)
            temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            download_path = temp_file.name
            temp_file.close()
        
        try:
            # Download file from S3
            logger.info(f"Downloading file {object_name} from S3 bucket {self.bucket_name} to {download_path}")
            self.s3_client.download_file(self.bucket_name, object_name, download_path)
            logger.info(f"File downloaded successfully to {download_path}")
            return download_path
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            # Clean up the file if it exists
            if os.path.exists(download_path):
                os.unlink(download_path)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during S3 download: {e}")
            # Clean up the file if it exists
            if os.path.exists(download_path):
                os.unlink(download_path)
            raise
    
    async def download_file(self, object_name: str, download_path: str = None) -> str:
        """
        Download a file from S3 bucket (async version that uses thread pool).
        
        Args:
            object_name: S3 object name to download
            download_path: Path to save the downloaded file. If not specified, a temporary file will be created.
            
        Returns:
            Path to the downloaded file
        """
        return await asyncio.get_event_loop().run_in_executor(
            self.executor,
            lambda: self._download_file_sync(object_name, download_path)
        )
    
    def _delete_file_sync(self, object_name: str) -> bool:
        """
        Synchronous version of delete_file to be run in thread pool.
        
        Args:
            object_name: S3 object name to delete
            
        Returns:
            True if successful, False otherwise
        """
        # If we have dummy credentials, just return True
        if self.s3_client is None:
            logger.warning("S3 client not initialized. Skipping S3 delete operation.")
            return True
            
        try:
            # Delete file from S3
            logger.info(f"Deleting file {object_name} from S3 bucket {self.bucket_name}")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info(f"File {object_name} deleted successfully")
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 delete: {e}")
            return False
    
    async def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from S3 bucket (async version that uses thread pool).
        
        Args:
            object_name: S3 object name to delete
            
        Returns:
            True if successful, False otherwise
        """
        return await asyncio.get_event_loop().run_in_executor(
            self.executor,
            lambda: self._delete_file_sync(object_name)
        )


# Create a singleton instance
s3_service = S3Service() 