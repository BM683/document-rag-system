import os
import uuid
from typing import List, Dict, Any
from pinecone import Pinecone


# Reads env vars (ensure you’ve loaded .env earlier in app startup)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX", "rag-index")
CLOUD = os.getenv("PINECONE_CLOUD", "aws")
REGION = os.getenv("PINECONE_REGION", "us-east-1")
EMBED_MODEL = os.getenv("PINECONE_EMBED_MODEL", "llama-text-embed-v2")
NAMESPACE_DEFAULT = "__default__"

if not PINECONE_API_KEY:
    raise RuntimeError("PINECONE_API_KEY is not set.")

class PineconeService:
    def __init__(self):
        # Initialize client
        self.pc = Pinecone(api_key=PINECONE_API_KEY)

        # Create an integrated-embedding index if it doesn’t exist
        if not self.pc.has_index(INDEX_NAME):
            # field_map maps “text” → the field name you’ll upsert (e.g., "chunk_text")
            self.pc.create_index_for_model(
                name=INDEX_NAME,
                cloud=CLOUD,
                region=REGION,
                embed={
                    "model": EMBED_MODEL,
                    "field_map": {"text": "chunk_text"}
                }
            )

        # Target the index
        self.index = self.pc.Index(INDEX_NAME)

    def upsert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        namespace: str | None = None,
        source_path: str | None = None
    ) -> int:
        """
        Upsert chunk records into Pinecone with integrated embedding.
        Each chunk must include:
          - "text" (string): the chunk text
          - "chunk_index" (int): index within the document
          - optional metadata fields you want to store (e.g., file name)
        """
        ns = namespace or NAMESPACE_DEFAULT
        doc_id = uuid.uuid4().hex[:8]

        records = []
        for c in chunks:
            # Expect "text" and "chunk_index" in your chunk structure
            chunk_text = c["text"]
            chunk_idx = c["chunk_index"]
            record = {
                "_id": f"{doc_id}-{chunk_idx}",
                "chunk_text": chunk_text,  # This is the field used for embedding
                # Any extra fields become metadata automatically:
                "source": c.get("source"),
                "chunk_index": chunk_idx,
                "length": c.get("length"),
                "token_estimate": c.get("token_estimate"),
            }
            if source_path and not record.get("source"):
                record["source"] = source_path
            records.append(record)

        # Batch upsert to keep request sizes manageable
        BATCH_SIZE = int(os.getenv("BATCH_SIZE", "64"))
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            self.index.upsert_records(ns, batch)

        return len(records)
