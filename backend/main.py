from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.embeddings import EmbeddingService
from backend.core.reranker import BGEReranker
from backend.core.qdrant_client import QdrantVectorStore
from backend.api.upload import router as upload_router
from backend.api.query import router as query_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("==================================================")
    print(f"  Starting {settings.APP_NAME} (v{settings.VERSION})")
    print("==================================================")
    
    # Pre-warm models asynchronously on startup
    try:
        embed_service = EmbeddingService()
        QdrantVectorStore(vector_size=embed_service.vector_dimension)
        if settings.ENABLE_RERANKER:
            reranker = BGEReranker()
            reranker._load_model()
        print("[Startup] All models and vector stores successfully initialized.")
    except Exception as e:
        print(f"[Startup Warning] Pre-warming initialization issue: {e}")

    yield
    print("[Shutdown] Cleaning up application resources.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="End-to-End Production RAG Application API with Qdrant & BGE Cross-Encoder Reranking",
    lifespan=lifespan
)

# Enable CORS for Streamlit frontend or custom UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(upload_router)
app.include_router(query_router)

@app.get("/", tags=["Health Check"])
async def root():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs"
    }

@app.get("/api/health", tags=["Health Check"])
async def health_check():
    from backend.core.firebase_client import is_firebase_enabled
    embed_service = EmbeddingService()
    qdrant_store = QdrantVectorStore(vector_size=embed_service.vector_dimension)
    stats = qdrant_store.get_stats()
    
    return {
        "status": "healthy",
        "vector_store": stats,
        "embedding_provider": embed_service.provider,
        "reranker_model": settings.RERANKER_MODEL_NAME,
        "firebase_enabled": is_firebase_enabled()
    }

@app.get("/api/debug/chunks")
async def debug_chunks(filename: str = None):
    embed_service = EmbeddingService()
    qdrant_store = QdrantVectorStore(vector_size=embed_service.vector_dimension)
    records, _ = qdrant_store.client.scroll(
        collection_name=qdrant_store.collection_name,
        limit=200,
        with_payload=True,
        with_vectors=False
    )
    results = []
    for r in records:
        payload = r.payload or {}
        fn = payload.get("filename", "")
        if not filename or filename.lower() in fn.lower():
            results.append({
                "id": str(r.id),
                "filename": fn,
                "section": payload.get("section"),
                "text": payload.get("text", "")
            })
    return {"count": len(results), "chunks": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

