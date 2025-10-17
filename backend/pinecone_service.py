import os
import uuid
from typing import List, Dict, Any
from pinecone import Pinecone


# Reads env vars (ensure you've loaded .env earlier in app startup)
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

        # Create an integrated-embedding index if it doesn't exist
        if not self.pc.has_index(INDEX_NAME):
            # field_map maps "text" → the field name you'll upsert (e.g., "chunk_text")
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
            
            # Extract document name from source path for easier querying
            document_name = source_path.split('/')[-1] if source_path else c.get("source", "").split('/')[-1]
            
            record = {
                "_id": f"{doc_id}-{chunk_idx}",
                "chunk_text": chunk_text,  # This is the field used for embedding
                # Any extra fields become metadata automatically:
                "source": c.get("source"),
                "document_id": doc_id,  # Unique document identifier
                "document_name": document_name,  # Human-readable document name
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
    
    def search_chunks(self, query: str, top_k: int = 5, namespace: str = "__default__"):
        response = self.index.search(
            namespace=namespace,
            query={
                "top_k": top_k,
                "inputs": {"text": query}
            },
            fields=["chunk_text", "source", "chunk_index"]
        )
        print("Raw Pinecone search response:", response)

        matches = []
        # Correctly iterate hits in Pinecone's new API
        for hit in response.get("result", {}).get("hits", []):
            matches.append({
                "id": hit.get("_id"),
                "score": hit.get("_score"),
                "chunk_text": hit.get("fields", {}).get("chunk_text"),
                "source": hit.get("fields", {}).get("source"),
                "chunk_index": hit.get("fields", {}).get("chunk_index"),
            })

        return {
            "query": query,
            "namespace": namespace,
            "top_k": top_k,
            "matches": matches
        }

    def test_pinecone_api(self, namespace: str = "__default__"):
        """Test what Pinecone API methods are available"""
        try:
            print(f"🧪 Testing Pinecone API methods...")
            
            # Test 1: describe_index_stats
            try:
                stats = self.index.describe_index_stats()
                print(f"✅ describe_index_stats works")
            except Exception as e:
                print(f"❌ describe_index_stats failed: {e}")
            
            # Test 2: query with different formats
            test_formats = [
                {"query": {"inputs": {"text": "test"}}},
                {"query": "test"},
                {"query": {"text": "test"}},
                {"query": {"vector": [0.1] * 768}},  # Dummy vector
            ]
            
            for i, format in enumerate(test_formats):
                try:
                    print(f"🧪 Testing query format {i+1}: {format}")
                    response = self.index.query(
                        namespace=namespace,
                        top_k=10,
                        **format
                    )
                    print(f"✅ Query format {i+1} works")
                    break
                except Exception as e:
                    print(f"❌ Query format {i+1} failed: {e}")
            
            # Test 3: search method
            try:
                response = self.index.search(
                    namespace=namespace,
                    query={
                        "top_k": 10,
                        "inputs": {"text": "test"}
                    }
                )
                print(f"✅ search method works")
            except Exception as e:
                print(f"❌ search method failed: {e}")
            
            # Test 4: fetch method (requires vector IDs)
            try:
                # Try to fetch a non-existent ID to test the method
                response = self.index.fetch(ids=["test-id"], namespace=namespace)
                print(f"✅ fetch method works")
            except Exception as e:
                print(f"❌ fetch method failed: {e}")
                
        except Exception as e:
            print(f"❌ API test failed: {e}")

    def list_documents_in_namespace(self, namespace: str = "__default__") -> List[Dict[str, Any]]:
        """
        List all unique documents in a namespace.
        
        NOTE: Pinecone's query() API requires text input. We use a minimal query
        to retrieve vectors, then extract unique document_id values from metadata.
        This is the only way to list documents without having vector IDs upfront.
        """
        try:
            print(f"🔍 Pinecone List: Querying namespace '{namespace}' for documents")
            
            # Check if namespace has any vectors (but don't rely on this completely)
            try:
                stats = self.index.describe_index_stats()
                namespace_stats = stats.get('namespaces', {}).get(namespace, {})
                vector_count = namespace_stats.get('vector_count', 0)
                print(f"📊 Namespace '{namespace}' reports {vector_count} vectors")
                
                # Don't return early based on vector_count - it might be incorrect
                # Always try to query to be sure
            except Exception as stats_error:
                print(f"⚠️ Could not get index stats: {stats_error}")
            
            # Use search method with retry mechanism for timing issues
            print(f"🔄 Using search method to get all vectors...")
            response = None
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    response = self.index.search(
                        namespace=namespace,
                        query={
                            "top_k": 10000,
                            "inputs": {"text": "a"}
                        },
                        fields=["document_id", "document_name", "source"]
                    )
                    
                    hits = response.get("result", {}).get("hits", [])
                    print(f"📊 Retrieved {len(hits)} vectors (attempt {attempt + 1})")
                    
                    # If we got vectors, break out of retry loop
                    if len(hits) > 0:
                        break
                    
                    # If no vectors and we have more attempts, wait and retry
                    if attempt < max_retries - 1:
                        print(f"⏳ No vectors found, waiting {retry_delay}s before retry...")
                        import time
                        time.sleep(retry_delay)
                    
                except Exception as search_error:
                    print(f"❌ Search failed (attempt {attempt + 1}): {search_error}")
                    if attempt < max_retries - 1:
                        print(f"⏳ Waiting {retry_delay}s before retry...")
                        import time
                        time.sleep(retry_delay)
                    else:
                        print(f"🔄 Returning empty list due to search failure")
                        return []
            
            if not response:
                print(f"❌ No response from Pinecone after {max_retries} attempts")
                return []
            
            hits = response.get("result", {}).get("hits", [])
            
            # Extract unique documents by document_id
            documents_by_id = {}
            documents_by_source = {}  # For legacy documents without document_id
            
            for hit in hits:
                doc_id = hit.get("fields", {}).get("document_id")
                doc_name = hit.get("fields", {}).get("document_name")
                source = hit.get("fields", {}).get("source")
                
                if doc_id:
                    # New format with document_id
                    if doc_id not in documents_by_id:
                        documents_by_id[doc_id] = {
                            "document_id": doc_id,
                            "document_name": doc_name,
                            "source": source,
                            "filename": doc_name
                        }
                        print(f"📄 Found document: {doc_name} (id: {doc_id})")
                elif source:
                    # Legacy format - use source as document_id
                    if source not in documents_by_source:
                        documents_by_source[source] = {
                            "document_id": source,
                            "document_name": source.split('/')[-1] if '/' in source else source,
                            "source": source,
                            "filename": source.split('/')[-1] if '/' in source else source
                        }
                        print(f"📄 Found legacy document: {source}")
            
            # Combine both new and legacy documents
            documents = list(documents_by_id.values()) + list(documents_by_source.values())
            print(f"✅ Found {len(documents)} unique documents")
            return documents
            
        except Exception as e:
            print(f"❌ Error listing documents: {str(e)}")
            return []

    def delete_document_embeddings(self, document_id: str, namespace: str = "__default__") -> int:
        """
        Delete all embeddings for a specific document using document_id.
        Uses individual delete method since Pinecone doesn't have delete_all.
        """
        try:
            print(f"🗑️ Deleting vectors for document_id '{document_id}' in namespace '{namespace}'")
            
            # Method 1: Try delete by metadata filter (most efficient - one API call)
            try:
                print(f"🔄 Attempting delete by metadata filter...")
                self.index.delete(
                    filter={"document_id": {"$eq": document_id}},
                    namespace=namespace
                )
                print(f"✅ Deleted all vectors with document_id '{document_id}' in one call")
                return 1  # Return 1 to indicate success, actual count unknown
            except Exception as filter_error:
                print(f"⚠️ Filter delete failed: {filter_error}")
            
            # Method 2: Try delete by source filter (for legacy documents)
            try:
                print(f"🔄 Attempting delete by source filter...")
                self.index.delete(
                    filter={"source": {"$eq": document_id}},
                    namespace=namespace
                )
                print(f"✅ Deleted all vectors with source '{document_id}' in one call")
                return 1  # Return 1 to indicate success, actual count unknown
            except Exception as source_error:
                print(f"⚠️ Source filter delete failed: {source_error}")
            
            # Method 3: Fallback to batch delete by IDs
            print(f"🔄 Falling back to batch delete by IDs...")
            
            # Search for vectors with this document_id
            response = self.index.search(
                namespace=namespace,
                query={
                    "top_k": 10000,
                    "inputs": {"text": "a"}
                },
                fields=["document_id", "source"]
            )
            
            if not response:
                print(f"❌ No response from Pinecone")
                return 0
            
            # Find vectors matching this document_id or source
            vector_ids = []
            hits = response.get("result", {}).get("hits", [])
            print(f"📊 Found {len(hits)} vectors to check for deletion")
            
            for hit in hits:
                hit_doc_id = hit.get("fields", {}).get("document_id")
                hit_source = hit.get("fields", {}).get("source")
                
                if hit_doc_id == document_id or hit_source == document_id:
                    vector_ids.append(hit.get("_id"))
                    print(f"🎯 Found vector to delete: {hit.get('_id')} (doc_id: {hit_doc_id}, source: {hit_source})")
            
            # Delete vectors in batches (up to 1000 IDs per call)
            if vector_ids:
                print(f"🗑️ Deleting {len(vector_ids)} vectors in batches...")
                deleted_count = 0
                batch_size = 1000  # Pinecone limit
                
                for i in range(0, len(vector_ids), batch_size):
                    batch = vector_ids[i:i + batch_size]
                    try:
                        print(f"🗑️ Deleting batch {i//batch_size + 1}: {len(batch)} vectors")
                        self.index.delete(ids=batch, namespace=namespace)
                        deleted_count += len(batch)
                        print(f"✅ Successfully deleted batch: {len(batch)} vectors")
                    except Exception as e:
                        print(f"❌ Failed to delete batch: {e}")
                        # Fallback to individual deletes for this batch
                        for vector_id in batch:
                            try:
                                self.index.delete(id=vector_id, namespace=namespace)
                                deleted_count += 1
                                print(f"✅ Fallback: Deleted vector {vector_id}")
                            except Exception as individual_error:
                                print(f"❌ Failed to delete vector {vector_id}: {individual_error}")
                
                print(f"✅ Deleted {deleted_count}/{len(vector_ids)} vectors")
                return deleted_count
            else:
                print(f"⚠️ No vectors found for document_id '{document_id}'")
                return 0
                
        except Exception as e:
            print(f"❌ Error deleting embeddings: {str(e)}")
            return 0
