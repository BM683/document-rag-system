# gcs_client.py
import os
from google.cloud import storage
from fastapi import UploadFile
from datetime import datetime
import uuid

class GCSClient:
    def __init__(self):
        # Authentication handled automatically via GOOGLE_APPLICATION_CREDENTIALS
        self.client = storage.Client()
        self.bucket_name = os.getenv('GCS_BUCKET_NAME')
        self.bucket = self.client.bucket(self.bucket_name)
    
    def upload_file(self, file: UploadFile, user_id: str = None) -> dict:
        """Upload file to GCS and return metadata"""
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_id = str(uuid.uuid4())[:8]
        
        if user_id:
            blob_name = f"{user_id}/{timestamp}_{file_id}_{file.filename}"
        else:
            blob_name = f"uploads/{timestamp}_{file_id}_{file.filename}"
        
        # Create blob and upload
        blob = self.bucket.blob(blob_name)
        blob.upload_from_file(file.file, content_type=file.content_type)
        
        return {
            "filename": file.filename,
            "blob_name": blob_name,
            "size": blob.size,
            "content_type": file.content_type,
            "public_url": f"https://storage.googleapis.com/{self.bucket_name}/{blob_name}"
        }
    
    def download_file_content(self, blob_name: str) -> bytes:
        """Download file content from GCS"""
        blob = self.bucket.blob(blob_name)
        return blob.download_as_bytes()
    
    def delete_file(self, blob_name: str):
        """Delete file from GCS"""
        blob = self.bucket.blob(blob_name)
        blob.delete()

# Initialize global client
gcs_client = GCSClient()
