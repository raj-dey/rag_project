import os
from typing import List, Dict, Any, Optional, Union
from qdrant_client import QdrantClient as RawQdrantClient
from qdrant_client.http import models as rest_models
from backend.core.config import settings

_global_client = None

def get_shared_qdrant_client():
    global _global_client
    if _global_client is None:
        if settings.QDRANT_MODE == "memory":
            print("[QdrantVectorStore] Initializing Qdrant in MEMORY mode")
            _global_client = RawQdrantClient(":memory:")
        elif settings.QDRANT_MODE == "server":
            if settings.QDRANT_HOST.startswith("http://") or settings.QDRANT_HOST.startswith("https://"):
                print(f"[QdrantVectorStore] Initializing Qdrant SERVER mode using URL ({settings.QDRANT_HOST})")
                _global_client = RawQdrantClient(
                    url=settings.QDRANT_HOST,
                    api_key=settings.QDRANT_API_KEY
                )
            else:
                print(f"[QdrantVectorStore] Initializing Qdrant SERVER mode ({settings.QDRANT_HOST}:{settings.QDRANT_PORT})")
                _global_client = RawQdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    api_key=settings.QDRANT_API_KEY
                )
        else:  # "disk"
            storage_path = os.path.abspath(settings.QDRANT_PATH)
            os.makedirs(storage_path, exist_ok=True)
            print(f"[QdrantVectorStore] Initializing Qdrant DISK mode at {storage_path}")
            _global_client = RawQdrantClient(path=storage_path)
    return _global_client

class QdrantVectorStore:
    """Manages Qdrant vector database connection, collection lifecycle, and similarity searches."""

    def __init__(self, collection_name: str = None, vector_size: int = 384):
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        self.vector_size = vector_size
        self.client = get_shared_qdrant_client()
        self.ensure_collection(vector_size=self.vector_size)

    def ensure_collection(self, vector_size: int):
        """Creates collection if it does not exist, or verifies dimension."""
        collections = [c.name for c in self.client.get_collections().collections]
        
        if self.collection_name not in collections:
            print(f"[QdrantVectorStore] Creating collection '{self.collection_name}' with vector size {vector_size}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest_models.VectorParams(
                    size=vector_size,
                    distance=rest_models.Distance.COSINE
                )
            )
        else:
            # Check existing collection vector size
            try:
                col_info = self.client.get_collection(collection_name=self.collection_name)
                existing_size = col_info.config.params.vectors.size
                if existing_size != vector_size:
                    print(f"[QdrantVectorStore] Vector size mismatch ({existing_size} vs {vector_size}). Recreating collection...")
                    self.client.delete_collection(collection_name=self.collection_name)
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=rest_models.VectorParams(
                            size=vector_size,
                            distance=rest_models.Distance.COSINE
                        )
                    )
            except Exception as e:
                print(f"[QdrantVectorStore] Collection check notice: {e}")

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
        """
        Upserts chunk vectors and payload metadata into Qdrant.
        Returns count of stored chunks.
        """
        if not chunks or not embeddings:
            return 0

        # Ensure collection matches vector dimension
        vector_dim = len(embeddings[0])
        self.ensure_collection(vector_size=vector_dim)

        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            chunk_id = chunk["chunk_id"]
            points.append(
                rest_models.PointStruct(
                    id=chunk_id,
                    vector=vector,
                    payload={
                        "text": chunk["text"],
                        **chunk["metadata"]
                    }
                )
            )

        # Batch upsert points
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        print(f"[QdrantVectorStore] Successfully upserted {len(points)} chunks into '{self.collection_name}'")
        return len(points)

    def search_similarity(self, query_vector: List[float], top_k: int = 10, filter_filename: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes dense vector similarity search in Qdrant.
        Returns list of matched chunks with cosine similarity score and payload metadata.
        """
        query_filter = None
        if filter_filename:
            query_filter = rest_models.Filter(
                must=[
                    rest_models.FieldCondition(
                        key="filename",
                        match=rest_models.MatchValue(value=filter_filename)
                    )
                ]
            )

        try:
            if hasattr(self.client, "query_points"):
                res = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=top_k,
                    query_filter=query_filter
                )
                results = res.points
            else:
                results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=top_k,
                    query_filter=query_filter
                )
        except Exception as e:
            print(f"[QdrantVectorStore] Search warning ({e}). Recreating collection for vector dimension: {len(query_vector)}")
            self.client.delete_collection(collection_name=self.collection_name)
            self.ensure_collection(vector_size=len(query_vector))
            return []

        matched_chunks = []
        for hit in results:
            matched_chunks.append({
                "chunk_id": str(hit.id),
                "score": float(hit.score),
                "text": hit.payload.get("text", ""),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
            })

        return matched_chunks

    def get_stats(self) -> Dict[str, Any]:
        """Returns collection stats, total vector points, and unique ingested filenames."""
        try:
            col_info = self.client.get_collection(collection_name=self.collection_name)
            points_count = col_info.points_count
            
            # Scroll payloads to discover unique filenames
            records, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                with_payload=True,
                with_vectors=False
            )
            filenames = sorted(list(set(r.payload.get("filename") for r in records if r.payload and "filename" in r.payload)))
            
            return {
                "collection_name": self.collection_name,
                "total_chunks": points_count,
                "unique_files": len(filenames),
                "filenames": filenames
            }
        except Exception as e:
            return {
                "collection_name": self.collection_name,
                "total_chunks": 0,
                "unique_files": 0,
                "filenames": [],
                "error": str(e)
            }

    def clear_collection(self):
        """Deletes all records from collection."""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            self.ensure_collection(vector_size=self.vector_size)
            print(f"[QdrantVectorStore] Cleared collection '{self.collection_name}'")
        except Exception as e:
            print(f"[QdrantVectorStore] Error clearing collection: {e}")

    def delete_chunks_by_ids(self, chunk_ids: List[Union[str, int]]) -> int:
        """
        Surgically deletes specific chunks by their point IDs.
        This is the primary deletion path when Firestore tracks chunk IDs.
        Returns number of deleted points.
        """
        if not chunk_ids:
            return 0
        try:
            # Qdrant accepts both integer and UUID string IDs
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=rest_models.PointIdsList(points=chunk_ids)
            )
            print(f"[QdrantVectorStore] Deleted {len(chunk_ids)} chunks by ID from '{self.collection_name}'")
            return len(chunk_ids)
        except Exception as e:
            print(f"[QdrantVectorStore] Error deleting chunks by IDs: {e}")
            return 0

    def delete_chunks_by_filename(self, filename: str) -> int:
        """
        Fallback: deletes all chunks in the collection matching a given filename
        using a Qdrant payload filter. Returns estimated deleted count.
        """
        try:
            # First count how many match
            records, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=rest_models.Filter(
                    must=[
                        rest_models.FieldCondition(
                            key="filename",
                            match=rest_models.MatchValue(value=filename)
                        )
                    ]
                ),
                limit=10000,
                with_payload=False,
                with_vectors=False
            )
            count = len(records)

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=rest_models.FilterSelector(
                    filter=rest_models.Filter(
                        must=[
                            rest_models.FieldCondition(
                                key="filename",
                                match=rest_models.MatchValue(value=filename)
                            )
                        ]
                    )
                )
            )
            print(f"[QdrantVectorStore] Deleted ~{count} chunks for filename '{filename}' from '{self.collection_name}'")
            return count
        except Exception as e:
            print(f"[QdrantVectorStore] Error deleting chunks by filename '{filename}': {e}")
            return 0

