from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter, Query
from pathlib import Path
import os
from dotenv import load_dotenv

# Load env variables from backend/.env
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from groq_client import groq_chat_completion

from document_service import DocumentProcessor
from pinecone_service import PineconeService

# Initialize FastAPI app and router
app = FastAPI(title="Document RAG System")
router = APIRouter()

# Initialize services
doc_processor = DocumentProcessor()
pinecone_service = PineconeService()

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)


@app.get("/")
def read_root():
    return {"message": "Hello! The API is working!"}


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

    file_path = f"uploads/{file.filename}"
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Process and preview text
    try:
        document_info = doc_processor.read_file_content(file_path)
        preview = document_info["content"][:500] + "..." if len(document_info["content"]) > 500 else document_info["content"]
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "path": file_path,
            "text_preview": preview,
            "word_count": document_info["word_count"],
            "character_count": document_info["character_count"],
            "file_type": document_info["file_type"],
            "message": "File uploaded and processed successfully!"
        }
    except Exception as e:
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
    try:
        files = os.listdir("uploads")
        return {"files": files, "count": len(files)}
    except Exception as e:
        return {"files": [], "count": 0, "error": str(e)}


@app.get("/files/{filename}/content")
def get_file_content(filename: str):
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
            "chunks": chunks[:5]  # preview
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error chunking file: {str(e)}")


@router.post("/files/{filename}/embed")
def embed_document_chunks(filename: str, namespace: str | None = None):
    """
    Reads an uploaded file, chunks it, and upserts chunks to Pinecone with integrated embedding.
    """
    file_path = os.path.join("uploads", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        doc_info = doc_processor.read_file_content(file_path)
        full_text = doc_info["content"]

        chunks = doc_processor.chunk_text(full_text, source_filename=filename)
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks generated from document.")

        total = pinecone_service.upsert_chunks(chunks, namespace=namespace, source_path=file_path)
        return {
            "message": f"Upserted {total} chunks to Pinecone",
            "namespace": namespace or "__default__"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pinecone upsert failed: {str(e)}")

@router.get("/search")
def search(query: str, top_k: int = 5, namespace: str | None = None):
    ns = namespace or "__default__"
    try:
        response = pinecone_service.search_chunks(query=query, top_k=top_k, namespace=ns)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
from groq_client import groq_chat_completion

@router.post("/ask")
def ask_question(
    question: str,
    top_k: int = 5,
    namespace: str | None = None
    ):
    # Step 1: Retrieve chunks with Pinecone
    ns = namespace or "__default__"
    retrieval = pinecone_service.search_chunks(
        query=question,
        top_k=top_k,
        namespace=ns
    )
    # Step 2: Prepare context for the LLM
    context_text = "\n\n".join(
        f"Source: {c['source']} (Chunk {c['chunk_index']}):\n{c['chunk_text']}" for c in retrieval['matches']
    )
    prompt = [
        {
            "role": "system",
            "content": "You are an expert assistant. Use the provided document excerpts to answer as helpfully as possible. If unsure, say you don't know."
        },
        {
            "role": "user",
            "content": f"Context:\n{context_text}\n\nQuestion: {question}\nAnswer:"
        }
    ]
    # Step 3: Call Groq LLM
    llm_response = groq_chat_completion(messages=prompt)
    answer = llm_response['choices'][0]['message']['content']
    return {
        "question": question,
        "answer": answer,
        "chunks_used": retrieval['matches']
    }



# Include router for API grouping
app.include_router(router, prefix="/api", tags=["pinecone"])
