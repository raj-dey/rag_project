import math
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder
from backend.core.config import settings

_global_reranker_models = {}

class BGEReranker:
    """Reranks top-K retrieved candidate chunks using BGE Cross-Encoder."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.RERANKER_MODEL_NAME

    @property
    def _model(self):
        return _global_reranker_models.get(self.model_name)

    def _load_model(self):
        if self.model_name not in _global_reranker_models:
            print(f"[BGEReranker] Loading Cross-Encoder model: {self.model_name}")
            try:
                _global_reranker_models[self.model_name] = CrossEncoder(self.model_name, max_length=512)
            except Exception as e:
                print(f"[BGEReranker] Failed to load {self.model_name}: {e}. Falling back to default cross-encoder.")
                _global_reranker_models[self.model_name] = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)

    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_n: int = 3,
        score_threshold: float = 0.25
    ) -> List[Dict[str, Any]]:
        """
        Reranks query-chunk pairs using BGE Cross-Encoder logits.
        Applies sigmoid normalization to convert raw logits to a 0.0-1.0 relevance probability score.
        Filters out candidate chunks below score_threshold and returns top_n chunks.
        """
        if not chunks:
            return []

        self._load_model()

        # Build pair inputs: (query, passage_text)
        pairs = [[query, chunk["text"]] for chunk in chunks]

        try:
            raw_scores = self._model.predict(pairs)
            
            # Compute sigmoid score for intuitive 0-1 relevance rating
            reranked_chunks = []
            for chunk, raw_score in zip(chunks, raw_scores):
                # Sigmoid formula: 1 / (1 + exp(-x))
                score_val = float(raw_score)
                sigmoid_score = 1.0 / (1.0 + math.exp(-score_val))
                
                updated_chunk = {
                    **chunk,
                    "vector_score": chunk.get("score", 0.0),
                    "rerank_score": round(sigmoid_score, 4),
                    "raw_logit": round(score_val, 4)
                }
                reranked_chunks.append(updated_chunk)

            # Sort descending by rerank_score
            reranked_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)

            # Filter low relevancy chunks
            filtered_chunks = [c for c in reranked_chunks if c["rerank_score"] >= score_threshold]

            # If filtering left 0 chunks, retain top 1 candidate if available
            if not filtered_chunks and reranked_chunks:
                filtered_chunks = [reranked_chunks[0]]

            return filtered_chunks[:top_n]

        except Exception as e:
            print(f"[BGEReranker] Reranking error: {e}. Returning un-reranked top candidate chunks.")
            for c in chunks:
                c["rerank_score"] = round(float(c.get("score", 0.0)), 4)
            return chunks[:top_n]
