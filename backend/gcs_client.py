# gcs_client.py
import os
from typing import List
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
            blob_name = f"users/{user_id}/{timestamp}_{file_id}_{file.filename}"
        else:
            blob_name = f"uploads/{timestamp}_{file_id}_{file.filename}"
        
        print(f"🚀 GCS Upload: Uploading {file.filename} to {blob_name}")
        print(f"📁 Bucket: {self.bucket_name}")
        print(f"👤 User ID: {user_id}")
        
        # Create blob and upload
        blob = self.bucket.blob(blob_name)
        blob.upload_from_file(file.file, content_type=file.content_type)
        
        print(f"✅ GCS Upload Success: {blob_name} ({blob.size} bytes)")
        
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
    
    def list_files_by_user(self, user_id: str) -> List[dict]:
        """List all files for a specific user"""
        try:
            namespace = f"users/{user_id}"
            print(f"🔍 GCS List: Looking for files for user '{user_id}'")
            print(f"📁 Bucket: {self.bucket_name}")
            print(f"🔎 Prefix: {namespace}/")
            
            blobs = self.bucket.list_blobs(prefix=f"{namespace}/")
            files = []
            
            blob_count = 0
            for blob in blobs:
                blob_count += 1
                print(f"📄 Found blob: {blob.name} ({blob.size} bytes)")
                
                # Extract filename from blob name
                filename = blob.name.split('/')[-1]
                # Extract timestamp from filename (format: timestamp_id_filename)
                parts = filename.split('_', 2)
                upload_date = None
                if len(parts) >= 2:
                    try:
                        # Parse timestamp from filename
                        timestamp_str = parts[0] + '_' + parts[1]
                        upload_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S').isoformat()
                    except:
                        pass
                
                files.append({
                    "filename": filename,
                    "blob_name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_type,
                    "upload_date": upload_date,
                    "created": blob.time_created.isoformat() if blob.time_created else None
                })
            
            print(f"✅ GCS List Success: Found {blob_count} files for user '{user_id}'")
            return files
        except Exception as e:
            print(f"❌ Error listing files for user {user_id}: {str(e)}")
            return []

# Initialize global client
gcs_client = GCSClient()
