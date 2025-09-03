from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter, Query
from pathlib import Path
import os
import io
from dotenv import load_dotenv

# Load environment variables
if os.path.exists('.env'):
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")


from groq_client import groq_chat_completion
from document_service import DocumentProcessor
from pinecone_service import PineconeService
from gcs_client import gcs_client  # NEW IMPORT

# Initialize FastAPI app and router
app = FastAPI(title="Document RAG System")
router = APIRouter()

# Update CORS for production
origins = [
    "http://localhost:3000",
    "https://your-frontend-url.web.app",  # We'll update this after frontend deployment
    "*"  # Temporarily allow all for testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
doc_processor = DocumentProcessor()
pinecone_service = PineconeService()

# Remove local uploads directory creation
# os.makedirs("uploads", exist_ok=True)  # DELETE THIS LINE

@app.get("/")
def read_root():
    return {"message": "Hello! The API is working!"}

# Add a health check endpoint for Cloud Run
@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    allowed_types = [".txt", ".pdf", ".docx"]
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not supported. Allowed: {allowed_types}"
        )

    try:
        # Upload to GCS instead of local storage
        file_metadata = gcs_client.upload_file(file)
        
        # Process and preview text from GCS
        file_content = gcs_client.download_file_content(file_metadata["blob_name"])
        
        # Create a temporary file-like object for your document processor
        temp_file_path = f"/tmp/{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file_content)
        
        document_info = doc_processor.read_file_content(temp_file_path)
        
        # Clean up temp file
        os.remove(temp_file_path)
        
        preview = (document_info["content"][:500] + "..." 
                  if len(document_info["content"]) > 500 
                  else document_info["content"])
        
        return {
            "filename": file_metadata["filename"],
            "blob_name": file_metadata["blob_name"],  # NEW: Return blob_name for frontend
            "content_type": file_metadata["content_type"],
            "size": file_metadata["size"],
            "text_preview": preview,
            "word_count": document_info["word_count"],
            "character_count": document_info["character_count"],
            "file_type": document_info["file_type"],
            "message": "File uploaded and processed successfully!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@app.get("/files")
def list_uploaded_files():
    try:
        files = gcs_client.list_files("uploads/")
        return {"files": files, "count": len(files)}
    except Exception as e:
        return {"files": [], "count": 0, "error": str(e)}

@app.get("/files/{blob_name:path}/content")
def get_file_content(blob_name: str):
    try:
        file_content = gcs_client.download_file_content(blob_name)
        
        # Create temp file for processing
        filename = blob_name.split('/')[-1]  # Extract filename from blob_name
        temp_file_path = f"/tmp/{filename}"
        
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file_content)
        
        document_info = doc_processor.read_file_content(temp_file_path)
        os.remove(temp_file_path)  # Clean up
        
        return {
            "filename": filename,
            "blob_name": blob_name,
            "content": document_info["content"],
            "word_count": document_info["word_count"],
            "character_count": document_info["character_count"],
            "file_type": document_info["file_type"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/files/{blob_name:path}/chunks")
def get_file_chunks(blob_name: str):
    """Return a preview (first five) of the automated text chunks for a given file"""
    try:
        file_content = gcs_client.download_file_content(blob_name)
        filename = blob_name.split('/')[-1]
        
        # Create temp file for processing
        temp_file_path = f"/tmp/{filename}"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file_content)
        
        doc_info = doc_processor.read_file_content(temp_file_path)
        os.remove(temp_file_path)  # Clean up
        
        chunks = doc_processor.chunk_text(doc_info["content"], filename)
        return {
            "total_chunks": len(chunks),
            "chunks": chunks[:5]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error chunking file: {str(e)}")

@router.post("/files/{blob_name:path}/embed")
def embed_document_chunks(blob_name: str, namespace: str | None = None):
    """Reads a file from GCS, chunks it, and upserts chunks to Pinecone"""
    try:
        file_content = gcs_client.download_file_content(blob_name)
        filename = blob_name.split('/')[-1]
        
        # Create temp file for processing
        temp_file_path = f"/tmp/{filename}"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file_content)
        
        doc_info = doc_processor.read_file_content(temp_file_path)
        os.remove(temp_file_path)  # Clean up
        
        full_text = doc_info["content"]
        chunks = doc_processor.chunk_text(full_text, source_filename=filename)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks generated from document.")

        total = pinecone_service.upsert_chunks(chunks, namespace=namespace, source_path=blob_name)
        return {
            "message": f"Upserted {total} chunks to Pinecone",
            "namespace": namespace or "__default__"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pinecone upsert failed: {str(e)}")

# Add delete endpoint
@router.delete("/files/{blob_name:path}")
def delete_file(blob_name: str, namespace: str | None = None):
    """Delete file from GCS and optionally remove from Pinecone"""
    try:
        gcs_client.delete_file(blob_name)
        # TODO: Add logic to remove embeddings from Pinecone if needed
        return {"message": "File deleted successfully", "blob_name": blob_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

# Your existing endpoints remain the same
@router.get("/search")
def search(query: str, top_k: int = 5, namespace: str | None = None):
    ns = namespace or "__default__"
    try:
        response = pinecone_service.search_chunks(query=query, top_k=top_k, namespace=ns)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/ask")
def ask_question(question: str, top_k: int = 5, namespace: str | None = None):
    ns = namespace or "__default__"
    retrieval = pinecone_service.search_chunks(query=question, top_k=top_k, namespace=ns)
    print(f"Found {len(retrieval['matches'])} chunks")
    
    context_text = "\n\n".join(
        f"Source: {c['source']} (Chunk {c['chunk_index']}):\n{c['chunk_text']}" for c in retrieval['matches']
    )
    
    prompt = [
        {
            "role": "system",
            "content": "You are an expert assistant. Use ONLY the provided document excerpts to answer as helpfully as possible. If unsure, say you don't know."
        },
        {
            "role": "user",
            "content": f"Context:\n{context_text}\n\nQuestion: {question}\nAnswer:"
        }
    ]
    
    llm_response = groq_chat_completion(messages=prompt)
    answer = llm_response['choices'][0]['message']['content']
    
    return {
        "question": question,
        "answer": answer,
        "chunks_used": retrieval['matches']
    }
@router.post("/test-groq")
def test_groq_simple():
    """Test Groq API with minimal request"""
    try:
        simple_prompt = [
            {"role": "user", "content": "Say hello"}
        ]
        
        response = groq_chat_completion(
            messages=simple_prompt,
            model="llama3-8b-8192",
            temperature=0.1,
            max_tokens=50
        )
        
        return {"success": True, "response": response}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Include router
app.include_router(router, prefix="/api", tags=["pinecone"])
