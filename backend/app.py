from fastapi import FastAPI, UploadFile, File, HTTPException
import os

# Create the FastAPI app
app = FastAPI(title="Document RAG System")

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "Hello! The API is working!"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a document file"""
    
    # Check if file was actually uploaded
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # For now, let's only accept certain file types
    allowed_types = [".txt", ".pdf", ".docx"]
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"File type {file_extension} not supported. Allowed: {allowed_types}"
        )
    
    # Save the file
    file_path = f"uploads/{file.filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Return info about the uploaded file
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content),
        "path": file_path,
        "message": "File uploaded successfully!"
    }

@app.get("/files")
def list_uploaded_files():
    """List all uploaded files"""
    try:
        files = os.listdir("uploads")
        return {
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        return {"files": [], "count": 0, "error": str(e)}
