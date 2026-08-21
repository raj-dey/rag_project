import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App General Settings
    APP_NAME: str = "Production RAG Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Qdrant Database Settings
    QDRANT_MODE: str = "disk"  # Options: "memory", "disk", "server"
    QDRANT_PATH: str = os.path.join(os.path.dirname(__file__), "..", "qdrant_storage")
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "rag_documents"

    # Embeddings Settings
    EMBEDDING_PROVIDER: str = "huggingface"  # "huggingface" or "gemini"
    HF_EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"  # 384 dim, fast & high quality
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"  # 3072 dim

    # Reranker Settings
    RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-base"
    ENABLE_RERANKER: bool = True

    # LLM Settings (Gemini)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL: str = "gemini-3.6-flash"
    MAX_GENERATION_TOKENS: int = 4096
    TEMPERATURE: float = 0.2

    # Ollama Settings (Fallback)
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"                  # e.g., llama3, mistral, gemma2, llama3.2

    # Default RAG Parameters
    DEFAULT_CHUNK_SIZE: int = 1200        # smaller = more granular, better recall
    DEFAULT_CHUNK_OVERLAP: int = 300      # more overlap = fewer missed boundaries
    DEFAULT_TOP_K: int = 50               # retrieve 50 candidates from Qdrant
    DEFAULT_TOP_N: int = 12               # send top 12 to LLM for broader context
    DEFAULT_SCORE_THRESHOLD: float = 0.05 # less aggressive filtering

    # Firebase Settings
    FIREBASE_ENABLED: bool = False
    FIREBASE_SERVICE_ACCOUNT_PATH: Optional[str] = None   # path to serviceAccountKey.json
    FIREBASE_SERVICE_ACCOUNT_JSON: Optional[str] = None   # inline JSON string (alternative)
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_STORAGE_BUCKET: Optional[str] = None         # e.g. "myproject.appspot.com"

    # Admin Panel
    ADMIN_PASSWORD: str = "admin123"                      # change in .env


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
