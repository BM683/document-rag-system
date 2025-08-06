from fastapi import FastAPI, UploadFile, File, HTTPException
import os
from document_service import DocumentProcessor

# Create the FastAPI app
app = FastAPI(title="Document RAG System")

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

# Initialize document processor
doc_processor = DocumentProcessor()

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
    
    # NEW: Process the document and extract text
    try:
        document_info = doc_processor.read_file_content(file_path)
        
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "path": file_path,
            "text_preview": document_info["content"][:500] + "..." if len(document_info["content"]) > 500 else document_info["content"],
            "word_count": document_info["word_count"],
            "character_count": document_info["character_count"],
            "file_type": document_info["file_type"],
            "message": "File uploaded and processed successfully!"
        }
    except Exception as e:
        # If processing fails, still return upload success but note the processing error
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "path": file_path,
            "processing_error": str(e),
            "message": "File uploaded but processing failed"
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

@app.get("/files/{filename}/content")
def get_file_content(filename: str):
    """Get the processed content of a specific file"""
    file_path = f"uploads/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        document_info = doc_processor.read_file_content(file_path)
        return {
            "filename": filename,
            "content": document_info["content"],
            "word_count": document_info["word_count"],
            "character_count": document_info["character_count"],
            "file_type": document_info["file_type"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.get("/files/{filename}/chunks")
def get_file_chunks(filename: str):
    """
    Return a preview (first five) of the automated text chunks for a given file
    """
    file_path = f"uploads/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        doc_info = doc_processor.read_file_content(file_path)
        chunks = doc_processor.chunk_text(doc_info["content"], filename)
        return {
            "total_chunks": len(chunks),
            "chunks": chunks[:5]  # Preview first five
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error chunking file: {str(e)}")
