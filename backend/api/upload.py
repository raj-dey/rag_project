import time
import re
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Header
from pydantic import BaseModel

from backend.core.document_parser import DocumentParser
from backend.core.chunking import DocumentChunker
from backend.core.embeddings import EmbeddingService
from backend.core.qdrant_client import QdrantVectorStore
from backend.core.config import settings
from backend.core.firebase_client import (
    get_firestore_client,
    get_storage_bucket,
    is_firebase_enabled,
)
from backend.core.synonym_service import (
    extract_and_store_synonyms,
    delete_synonyms_for_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Document Ingestion"])

# Firestore collection for document metadata
DOCS_COLLECTION = "documents"


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class IngestionResponse(BaseModel):
    status: str
    message: str
    files_processed: int
    total_sections_parsed: int
    total_chunks_created: int
    total_vectors_indexed: int
    processing_time_seconds: float
    files: List[str]
    firebase_storage: bool = False


class DeleteFileResponse(BaseModel):
    status: str
    filename: str
    chunks_deleted: int
    firestore_cleaned: bool
    storage_cleaned: bool
    message: str


# ---------------------------------------------------------------------------
# Firestore Helpers
# ---------------------------------------------------------------------------

def _safe_doc_id(filename: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', filename)


def _save_document_metadata(
    filename: str,
    chunk_ids: List,
    total_chunks: int,
    file_size: int,
    file_type: str,
    storage_url: Optional[str] = None
):
    """Persists document metadata + chunk ID list to Firestore."""
    if not is_firebase_enabled():
        return
    try:
        db = get_firestore_client()
        safe_id = _safe_doc_id(filename)
        db.collection(DOCS_COLLECTION).document(safe_id).set({
            "filename": filename,
            "chunk_ids": chunk_ids,
            "total_chunks": total_chunks,
            "file_size_bytes": file_size,
            "file_type": file_type,
            "storage_url": storage_url,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"[Upload] Saved Firestore metadata for '{filename}' ({total_chunks} chunks)")
    except Exception as e:
        logger.warning(f"[Upload] Failed to save Firestore metadata for '{filename}': {e}")


def _upload_to_storage(file_bytes: bytes, filename: str) -> Optional[str]:
    """Uploads raw file bytes to Firebase Storage. Returns public URL or None."""
    if not is_firebase_enabled():
        return None
    try:
        bucket = get_storage_bucket()
        blob = bucket.blob(f"documents/{filename}")
        blob.upload_from_string(file_bytes, content_type="application/octet-stream")
        # Make the blob publicly readable (optional — comment out if you want private)
        blob.make_public()
        url = blob.public_url
        logger.info(f"[Upload] Uploaded '{filename}' to Firebase Storage: {url}")
        return url
    except Exception as e:
        logger.warning(f"[Upload] Firebase Storage upload failed for '{filename}': {e}")
        return None


def _delete_from_storage(filename: str) -> bool:
    """Deletes a file from Firebase Storage. Returns True on success."""
    if not is_firebase_enabled():
        return True
    try:
        bucket = get_storage_bucket()
        blob = bucket.blob(f"documents/{filename}")
        blob.delete()
        logger.info(f"[Upload] Deleted '{filename}' from Firebase Storage.")
        return True
    except Exception as e:
        logger.warning(f"[Upload] Failed to delete '{filename}' from Firebase Storage: {e}")
        return False


def _delete_firestore_metadata(filename: str) -> bool:
    """Deletes the Firestore document metadata record. Returns True on success."""
    if not is_firebase_enabled():
        return True
    try:
        db = get_firestore_client()
        safe_id = _safe_doc_id(filename)
        db.collection(DOCS_COLLECTION).document(safe_id).delete()
        logger.info(f"[Upload] Deleted Firestore metadata for '{filename}'.")
        return True
    except Exception as e:
        logger.warning(f"[Upload] Failed to delete Firestore metadata for '{filename}': {e}")
        return False


def _get_chunk_ids_from_firestore(filename: str) -> Optional[List]:
    """Fetches the chunk IDs stored in Firestore for a given filename."""
    if not is_firebase_enabled():
        return None
    try:
        db = get_firestore_client()
        safe_id = _safe_doc_id(filename)
        doc = db.collection(DOCS_COLLECTION).document(safe_id).get()
        if doc.exists:
            return doc.to_dict().get("chunk_ids", [])
        return None
    except Exception as e:
        logger.warning(f"[Upload] Failed to fetch chunk IDs from Firestore for '{filename}': {e}")
        return None


def _list_firestore_documents() -> List[dict]:
    """Returns all document metadata records from Firestore."""
    if not is_firebase_enabled():
        return []
    try:
        db = get_firestore_client()
        docs = db.collection(DOCS_COLLECTION).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.warning(f"[Upload] Failed to list Firestore documents: {e}")
        return []


# ---------------------------------------------------------------------------
# Upload Endpoint
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=IngestionResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    chunk_size: int = Query(default=settings.DEFAULT_CHUNK_SIZE, ge=50, le=4000),
    chunk_overlap: int = Query(default=settings.DEFAULT_CHUNK_OVERLAP, ge=0, le=2000),
    embedding_provider: Optional[str] = Query(default=None),
    gemini_api_key: Optional[str] = Query(default=None),
    openai_api_key: Optional[str] = Query(default=None),
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-API-Key"),
    x_openai_api_key: Optional[str] = Header(None, alias="X-OpenAI-API-Key")
):
    """
    Ingests multi-format documents (PDF, DOCX, CSV, XLSX, TXT).
    - Parses → chunks → embeds → indexes into Qdrant
    - Uploads raw file to Firebase Storage
    - Saves chunk IDs + metadata to Firestore
    - Runs async synonym/keyword extraction via Gemini → stored in Firestore
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    if chunk_overlap >= chunk_size:
        chunk_overlap = max(0, chunk_size - 20)

    api_key = (
        x_gemini_api_key or gemini_api_key or
        x_openai_api_key or openai_api_key or
        settings.GEMINI_API_KEY
    )

    start_time = time.time()
    processed_filenames = []
    all_chunks = []
    total_sections = 0
    file_bytes_cache = {}  # filename → bytes, for Storage upload

    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    for file in files:
        filename = file.filename
        try:
            content = await file.read()
            file_bytes_cache[filename] = content

            sections = DocumentParser.parse_file(content, filename)
            total_sections += len(sections)

            file_chunks = chunker.chunk_sections(sections)
            all_chunks.extend(file_chunks)
            processed_filenames.append(filename)

        except Exception as e:
            logger.error(f"[Upload] Error processing {filename}: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Error parsing file '{filename}': {str(e)}"
            )

    if not all_chunks:
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted from the uploaded files."
        )

    # --- Embeddings ---
    provider = embedding_provider or settings.EMBEDDING_PROVIDER
    try:
        embedding_service = EmbeddingService(provider=provider, gemini_api_key=api_key)
        chunk_texts = [c["text"] for c in all_chunks]
        embeddings = embedding_service.embed_documents(chunk_texts)
    except Exception as e:
        logger.warning(f"[Upload] Embedding provider '{provider}' failed ({e}). Falling back to huggingface.")
        try:
            embedding_service = EmbeddingService(provider="huggingface")
            chunk_texts = [c["text"] for c in all_chunks]
            embeddings = embedding_service.embed_documents(chunk_texts)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {str(err)}")

    # --- Upsert to Qdrant ---
    try:
        qdrant_store = QdrantVectorStore(vector_size=embedding_service.vector_dimension)
        indexed_count = qdrant_store.upsert_chunks(all_chunks, embeddings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant storage error: {str(e)}")

    elapsed_time = round(time.time() - start_time, 3)
    firebase_ok = is_firebase_enabled()

    # --- Firebase: Storage + Firestore (per file) ---
    if firebase_ok:
        # Group chunks by filename for per-file Firestore metadata
        chunks_by_file: dict = {}
        for chunk in all_chunks:
            fn = chunk["metadata"].get("filename", "unknown")
            if fn not in chunks_by_file:
                chunks_by_file[fn] = []
            chunks_by_file[fn].append(chunk["chunk_id"])

        for filename in processed_filenames:
            raw_bytes = file_bytes_cache.get(filename, b"")
            chunk_ids = chunks_by_file.get(filename, [])
            file_type = filename.lower().split(".")[-1]

            # 1. Upload to Firebase Storage
            storage_url = _upload_to_storage(raw_bytes, filename)

            # 2. Save metadata to Firestore
            _save_document_metadata(
                filename=filename,
                chunk_ids=chunk_ids,
                total_chunks=len(chunk_ids),
                file_size=len(raw_bytes),
                file_type=file_type,
                storage_url=storage_url,
            )

        # 3. Async synonym extraction (fire-and-forget, won't block the response)
        all_text_by_file: dict = {}
        for chunk in all_chunks:
            fn = chunk["metadata"].get("filename", "unknown")
            all_text_by_file.setdefault(fn, [])
            all_text_by_file[fn].append(chunk["text"])

        async def run_synonym_extraction():
            for fn, texts in all_text_by_file.items():
                combined_text = "\n\n".join(texts)
                try:
                    await asyncio.to_thread(
                        extract_and_store_synonyms, combined_text, fn, api_key
                    )
                except Exception as e:
                    logger.warning(f"[Upload] Synonym extraction failed for '{fn}': {e}")

        asyncio.create_task(run_synonym_extraction())

    return IngestionResponse(
        status="success",
        message=f"Successfully processed and indexed {len(processed_filenames)} files into Qdrant.",
        files_processed=len(processed_filenames),
        total_sections_parsed=total_sections,
        total_chunks_created=len(all_chunks),
        total_vectors_indexed=indexed_count,
        processing_time_seconds=elapsed_time,
        files=processed_filenames,
        firebase_storage=firebase_ok,
    )


# ---------------------------------------------------------------------------
# Per-File Delete Endpoint (cascade)
# ---------------------------------------------------------------------------

@router.delete("/documents/{filename:path}", response_model=DeleteFileResponse)
async def delete_document(filename: str):
    """
    Cascade-deletes a single document:
    1. Fetches chunk IDs from Firestore
    2. Deletes those chunks from Qdrant (surgical delete)
    3. Deletes the synonym map from Firestore
    4. Deletes the metadata record from Firestore
    5. Deletes the raw file from Firebase Storage
    """
    embedding_service = EmbeddingService()
    qdrant_store = QdrantVectorStore(vector_size=embedding_service.vector_dimension)

    # Step 1: Get chunk IDs from Firestore (preferred) or fallback to filter
    chunk_ids = _get_chunk_ids_from_firestore(filename)

    # Step 2: Delete from Qdrant
    if chunk_ids is not None and len(chunk_ids) > 0:
        deleted_count = qdrant_store.delete_chunks_by_ids(chunk_ids)
    else:
        # Fallback: filter delete by filename
        deleted_count = qdrant_store.delete_chunks_by_filename(filename)

    # Step 3: Delete synonym map
    synonym_ok = delete_synonyms_for_file(filename)

    # Step 4: Delete Firestore metadata
    firestore_ok = _delete_firestore_metadata(filename)

    # Step 5: Delete from Firebase Storage
    storage_ok = _delete_from_storage(filename)

    return DeleteFileResponse(
        status="success",
        filename=filename,
        chunks_deleted=deleted_count,
        firestore_cleaned=firestore_ok and synonym_ok,
        storage_cleaned=storage_ok,
        message=(
            f"Deleted '{filename}': {deleted_count} Qdrant chunks removed, "
            f"Firestore {'✓' if firestore_ok else '✗'}, "
            f"Storage {'✓' if storage_ok else '✗ (not in Firebase or Firebase disabled)'}."
        )
    )


# ---------------------------------------------------------------------------
# List Documents (from Firestore if enabled, else Qdrant stats)
# ---------------------------------------------------------------------------

@router.get("/documents")
async def list_documents():
    """
    Returns indexed document metadata.
    If Firebase is enabled → returns rich Firestore metadata.
    Otherwise → returns Qdrant vector store stats.
    """
    if is_firebase_enabled():
        fb_docs = _list_firestore_documents()
        if fb_docs:
            # Also get Qdrant stats for chunk counts
            embedding_service = EmbeddingService()
            qdrant_store = QdrantVectorStore(vector_size=embedding_service.vector_dimension)
            stats = qdrant_store.get_stats()
            return {
                "source": "firestore",
                "documents": fb_docs,
                "qdrant_stats": stats,
            }

    embedding_service = EmbeddingService()
    qdrant_store = QdrantVectorStore(vector_size=embedding_service.vector_dimension)
    stats = qdrant_store.get_stats()
    return {"source": "qdrant", **stats}


# ---------------------------------------------------------------------------
# Clear All Documents
# ---------------------------------------------------------------------------

@router.delete("/documents")
async def clear_documents():
    """Clears ALL document vectors from Qdrant AND all Firestore/Storage records."""
    embedding_service = EmbeddingService()
    qdrant_store = QdrantVectorStore(vector_size=embedding_service.vector_dimension)
    qdrant_store.clear_collection()

    if is_firebase_enabled():
        # Delete all Firestore document records
        try:
            db = get_firestore_client()
            batch = db.batch()
            for doc in db.collection(DOCS_COLLECTION).stream():
                batch.delete(doc.reference)
            batch.commit()
        except Exception as e:
            logger.warning(f"[Upload] Failed to clear Firestore documents: {e}")

        # Delete all synonym records
        try:
            from backend.core.synonym_service import SYNONYM_COLLECTION
            batch = db.batch()
            for doc in db.collection(SYNONYM_COLLECTION).stream():
                batch.delete(doc.reference)
            batch.commit()
        except Exception as e:
            logger.warning(f"[Upload] Failed to clear Firestore synonyms: {e}")

        # Delete all Storage files under documents/
        try:
            bucket = get_storage_bucket()
            blobs = bucket.list_blobs(prefix="documents/")
            for blob in blobs:
                blob.delete()
        except Exception as e:
            logger.warning(f"[Upload] Failed to clear Firebase Storage: {e}")

    return {"status": "success", "message": "All documents cleared (Qdrant + Firestore + Storage)."}
