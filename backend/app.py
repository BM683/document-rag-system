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
        return {"message": f"Upserted {total} chunks to Pinecone", "namespace": namespace or "__default__"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pinecone upsert failed: {str(e)}")


# Include router with a prefix for organization
app.include_router(router, prefix="/api", tags=["pinecone"])
