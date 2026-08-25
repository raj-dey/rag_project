from typing import List
import os
from google import genai
from backend.core.config import settings

_global_hf_models = {}

class EmbeddingService:
    """Generates dense vector embeddings using HuggingFace BGE or Gemini models."""

    def __init__(self, provider: str = None, model_name: str = None, gemini_api_key: str = None, openai_api_key: str = None):
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.gemini_api_key = gemini_api_key or openai_api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        self.hf_model_name = model_name or settings.HF_EMBEDDING_MODEL
        self.gemini_model_name = settings.GEMINI_EMBEDDING_MODEL.replace("models/", "")
        
        if self.provider == "huggingface":
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                print("[EmbeddingService] sentence-transformers package not found. Auto-fallback to 'gemini'.")
                self.provider = "gemini"
        
        if self.provider == "huggingface":
            self._load_hf_model()

    @property
    def _hf_model(self):
        return _global_hf_models.get(self.hf_model_name)

    def _load_hf_model(self):
        if self.hf_model_name not in _global_hf_models:
            from sentence_transformers import SentenceTransformer
            print(f"[EmbeddingService] Loading HuggingFace model: {self.hf_model_name}")
            _global_hf_models[self.hf_model_name] = SentenceTransformer(self.hf_model_name)

    @property
    def vector_dimension(self) -> int:
        if self.provider in ["gemini", "google"]:
            return 3072
        else:
            self._load_hf_model()
            if hasattr(self._hf_model, "get_embedding_dimension"):
                return self._hf_model.get_embedding_dimension()
            return self._hf_model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if self.provider in ["gemini", "google"] and self.gemini_api_key:
            try:
                client = genai.Client(api_key=self.gemini_api_key)
                response = client.models.embed_content(
                    model=self.gemini_model_name,
                    contents=texts
                )
                embeddings = [e.values for e in response.embeddings]
                return embeddings
            except Exception as e:
                print(f"[EmbeddingService] Gemini Embedding failed: {e}. Falling back to HuggingFace BGE.")
                try:
                    from sentence_transformers import SentenceTransformer
                    self.provider = "huggingface"
                except ImportError:
                    raise Exception(f"Gemini embedding failed: {str(e)} (HuggingFace fallback unavailable)")

        self._load_hf_model()
        embeddings = self._hf_model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        if self.provider in ["gemini", "google"] and self.gemini_api_key:
            try:
                client = genai.Client(api_key=self.gemini_api_key)
                response = client.models.embed_content(
                    model=self.gemini_model_name,
                    contents=query
                )
                return response.embeddings[0].values
            except Exception as e:
                print(f"[EmbeddingService] Gemini Query Embedding failed: {e}. Falling back to HuggingFace BGE.")
                try:
                    from sentence_transformers import SentenceTransformer
                    self.provider = "huggingface"
                except ImportError:
                    raise Exception(f"Gemini query embedding failed: {str(e)} (HuggingFace fallback unavailable)")

        self._load_hf_model()
        
        # BGE models work best with instruction prefix for queries
        if "bge" in self.hf_model_name.lower():
            query_input = f"Represent this sentence for searching relevant passages: {query}"
        else:
            query_input = query

        embedding = self._hf_model.encode(query_input, normalize_embeddings=True)
        return embedding.tolist()
