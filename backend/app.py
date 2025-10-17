from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter, Query
from pathlib import Path
import os
import io
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port)

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

# Debug: Print GCS configuration
print(f"🔧 GCS Configuration:")
print(f"   Bucket Name: {os.getenv('GCS_BUCKET_NAME', 'NOT SET')}")
print(f"   Credentials: {'SET' if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') else 'NOT SET'}")
print(f"   Credentials Path: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'N/A')}")

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
async def upload_file(file: UploadFile = File(...), namespace: str = Query(None)):
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
        # Upload to GCS with namespace
        file_metadata = gcs_client.upload_file(file, namespace=namespace)
        
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

# Test endpoint for Pinecone API
@router.get("/test-pinecone")
def test_pinecone_api(namespace: str = Query(...)):
    """Test Pinecone API methods to see what works"""
    try:
        pinecone_service.test_pinecone_api(namespace)
        return {"message": "Pinecone API test completed - check logs"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pinecone API test failed: {str(e)}")

# Document management endpoints
@router.get("/documents")
def list_documents(namespace: str = Query(...)):
    """List all documents for a given namespace"""
    try:
        print(f"📋 API Request: List documents for namespace '{namespace}'")
        
        # Get files from GCS
        gcs_files = gcs_client.list_files_by_namespace(namespace)
        print(f"📁 GCS returned {len(gcs_files)} files")
        
        # Get indexed documents from Pinecone
        pinecone_docs = pinecone_service.list_documents_in_namespace(namespace)
        print(f"🔍 Pinecone returned {len(pinecone_docs)} indexed documents")
        
        # Create a mapping of document names to document IDs for quick lookup
        indexed_docs = {doc["document_name"]: doc["document_id"] for doc in pinecone_docs}
        print(f"🎯 Indexed documents: {list(indexed_docs.keys())}")
        
        # Also create a mapping by source path for legacy documents
        indexed_sources = {doc["source"]: doc["document_id"] for doc in pinecone_docs if doc.get("source")}
        print(f"🎯 Indexed sources: {list(indexed_sources.keys())}")
        
        # Combine GCS files with indexing status
        documents = []
        for file_info in gcs_files:
            # Try to find document_id by filename first (new format)
            document_id = indexed_docs.get(file_info["filename"])
            is_indexed = document_id is not None
            
            # If not found, try by source path (legacy format)
            if not document_id:
                document_id = indexed_sources.get(file_info["blob_name"])
                is_indexed = document_id is not None
            
            print(f"📄 File: {file_info['filename']} -> Indexed: {is_indexed} (doc_id: {document_id})")
            documents.append({
                "filename": file_info["filename"],
                "blob_name": file_info["blob_name"],
                "size": file_info["size"],
                "content_type": file_info["content_type"],
                "upload_date": file_info["upload_date"],
                "created": file_info["created"],
                "is_indexed": is_indexed,
                "document_id": document_id
            })
        
        # ALSO include Pinecone-only documents (documents that exist in Pinecone but not in GCS)
        # This handles the case where GCS file was deleted but Pinecone vectors remain
        for pinecone_doc in pinecone_docs:
            doc_name = pinecone_doc["document_name"]
            doc_id = pinecone_doc["document_id"]
            
            # Check if this document is already in our list (exists in both GCS and Pinecone)
            already_listed = any(doc["document_id"] == doc_id for doc in documents)
            
            if not already_listed:
                print(f"📄 Pinecone-only document: {doc_name} (id: {doc_id})")
                documents.append({
                    "filename": doc_name,
                    "blob_name": pinecone_doc.get("source", ""),
                    "size": 0,  # Unknown size for Pinecone-only docs
                    "content_type": "unknown",
                    "upload_date": None,
                    "created": None,
                    "is_indexed": True,
                    "document_id": doc_id
                })
        
        print(f"✅ API Response: Returning {len(documents)} documents")
        return {
            "documents": documents,
            "count": len(documents),
            "namespace": namespace
        }
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.get("/documents/{blob_name:path}/download")
def download_document(blob_name: str):
    """Download original file"""
    try:
        file_content = gcs_client.download_file_content(blob_name)
        
        # Extract filename from blob_name
        filename = blob_name.split('/')[-1]
        
        # Determine content type
        file_extension = os.path.splitext(filename)[1].lower()
        content_type_map = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        content_type = content_type_map.get(file_extension, 'application/octet-stream')
        
        from fastapi.responses import Response
        return Response(
            content=file_content,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

@router.delete("/documents/{blob_name:path}")
def delete_document(blob_name: str, namespace: str = Query(...), document_id: str = Query(None)):
    """Delete document completely from both GCS and Pinecone"""
    try:
        print(f"🗑️ API Delete: Deleting document '{blob_name}' with document_id '{document_id}'")
        
        # Delete from Pinecone first (if document_id provided)
        deleted_embeddings = 0
        if document_id and document_id != 'None' and document_id != 'null':
            print(f"🔄 Calling Pinecone delete with document_id: {document_id}")
            deleted_embeddings = pinecone_service.delete_document_embeddings(document_id, namespace)
            print(f"✅ Pinecone Delete: Removed {deleted_embeddings} embeddings")
        else:
            print(f"⚠️ No valid document_id provided ('{document_id}'), skipping Pinecone deletion")
        
        # Delete from GCS (only if blob_name is not empty)
        if blob_name and blob_name != "":
            try:
                gcs_client.delete_file(blob_name)
                print(f"✅ GCS Delete: Removed file '{blob_name}'")
            except Exception as gcs_error:
                print(f"⚠️ GCS Delete failed (file may not exist): {gcs_error}")
        else:
            print(f"⚠️ No blob_name provided, skipping GCS deletion")
        
        return {
            "message": "Document deleted successfully",
            "blob_name": blob_name,
            "document_id": document_id,
            "deleted_embeddings": deleted_embeddings
        }
    except Exception as e:
        print(f"❌ API Delete Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

# Legacy delete endpoint (keeping for backward compatibility)
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
