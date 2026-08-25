import time
import re
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from backend.core.embeddings import EmbeddingService
from backend.core.qdrant_client import QdrantVectorStore
from backend.core.reranker import BGEReranker
from backend.core.llm import LLMGenerator
from backend.core.config import settings
from backend.core.synonym_service import get_combined_synonym_map, expand_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Retrieval & Generation"])

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, example="What are the main findings in the document?")
    top_k: int = Field(default=settings.DEFAULT_TOP_K, ge=1, le=200)
    top_n: int = Field(default=settings.DEFAULT_TOP_N, ge=1, le=50)
    score_threshold: float = Field(default=settings.DEFAULT_SCORE_THRESHOLD, ge=0.0, le=1.0)
    filter_filename: Optional[str] = None
    embedding_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

class SourceCitation(BaseModel):
    source_id: int
    source_tag: str
    filename: str
    location: str
    rerank_score: float
    vector_score: float
    text_snippet: str

class QueryMetrics(BaseModel):
    embedding_time_ms: float
    qdrant_search_time_ms: float
    rerank_time_ms: float
    llm_gen_time_ms: float
    total_latency_ms: float
    candidate_chunks_retrieved: int
    reranked_chunks_retained: int
    multi_queries_used: int = 1
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    estimated_cost_inr: float = 0.0

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceCitation]
    metrics: QueryMetrics
    model_used: str


# ---------------------------------------------------------------------------
# Multi-Query Generation
# ---------------------------------------------------------------------------

def _generate_query_variants(query: str, api_key: str, n: int = 3) -> List[str]:
    """
    Uses Gemini to generate N alternate phrasings of the user query.
    This maximises coverage across different parts of the document.
    Falls back to just the original query if Gemini is unavailable.
    """
    if not api_key:
        return [query]
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""Generate {n} different search queries that could retrieve relevant information for the following user question.
Each variant should approach the question from a different angle or use different terminology.
Return ONLY the queries, one per line, no numbering, no extra text.

User question: {query}"""

        response = model.generate_content(prompt)
        raw = response.text.strip()
        variants = [line.strip() for line in raw.split("\n") if line.strip()][:n]
        variants = [query] + [v for v in variants if v.lower() != query.lower()]
        logger.info(f"[MultiQuery] Generated {len(variants)} query variants for: '{query[:60]}'")
        return variants
    except Exception as e:
        logger.warning(f"[MultiQuery] Failed to generate variants ({e}). Using original query only.")
        return [query]


def _merge_and_deduplicate(results_list: List[List[Dict]], max_chunks: int) -> List[Dict]:
    """
    Merges multiple Qdrant result lists, deduplicates by chunk_id,
    and keeps the highest score for each duplicate.
    """
    seen: Dict[str, Dict] = {}
    for results in results_list:
        for chunk in results:
            cid = chunk["chunk_id"]
            if cid not in seen or chunk["score"] > seen[cid]["score"]:
                seen[cid] = chunk
    # Sort by score descending, cap at max_chunks
    merged = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
    return merged[:max_chunks]


# ---------------------------------------------------------------------------
# Query Endpoint
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-API-Key"),
    x_openai_api_key: Optional[str] = Header(None, alias="X-OpenAI-API-Key")
):
    """
    Executes end-to-end RAG pipeline with full document coverage:
    0. Synonym query expansion (Firebase-backed)
    1. Multi-query generation (3 query variants) for broader coverage
    2. Embeds each query variant and searches Qdrant separately
    3. Merges + deduplicates all candidate chunks
    4. Reranks with BGE Cross-Encoder & applies score threshold
    5. Constructs grounded context prompt & generates answer with Gemini
    """
    t_start = time.time()

    # Determine API key priority: header → payload → env
    api_key = (
        (x_gemini_api_key or "").strip() or
        (request.gemini_api_key or "").strip() or
        (x_openai_api_key or "").strip() or
        (request.openai_api_key or "").strip() or
        settings.GEMINI_API_KEY
    )

    # ------------------------------------------------------------------
    # Step 0: Synonym Query Expansion (Firebase-backed, graceful fallback)
    # ------------------------------------------------------------------
    synonym_map = get_combined_synonym_map()
    expanded_query = expand_query(request.query, synonym_map)
    if expanded_query != request.query:
        logger.info(f"[Query] Synonym expansion: '{request.query[:60]}' → '{expanded_query[:100]}'")

    # ------------------------------------------------------------------
    # Step 1: Multi-Query Generation
    # Generate alternate phrasings to cover more of the document
    # ------------------------------------------------------------------
    t_embed_start = time.time()

    query_variants = _generate_query_variants(expanded_query, api_key, n=3)
    num_variants = len(query_variants)

    # Initialize embedding service once
    embedding_service = EmbeddingService(
        provider=request.embedding_provider or settings.EMBEDDING_PROVIDER,
        gemini_api_key=api_key
    )

    # Embed all query variants
    all_variant_vectors = []
    for variant in query_variants:
        vec = embedding_service.embed_query(variant)
        all_variant_vectors.append(vec)

    embed_ms = round((time.time() - t_embed_start) * 1000, 2)

    # ------------------------------------------------------------------
    # Step 2: Multi-Search in Qdrant (one search per query variant)
    # ------------------------------------------------------------------
    t_search_start = time.time()
    qdrant_store = QdrantVectorStore(vector_size=embedding_service.vector_dimension)

    all_results: List[List[Dict]] = []
    per_variant_k = max(request.top_k, 30)  # at least 30 per variant

    for vec in all_variant_vectors:
        variant_results = qdrant_store.search_similarity(
            query_vector=vec,
            top_k=per_variant_k,
            filter_filename=request.filter_filename
        )
        all_results.append(variant_results)

    # Merge and deduplicate — keep top top_k * 1.5 before reranking
    candidate_chunks = _merge_and_deduplicate(
        all_results,
        max_chunks=int(request.top_k * 1.5)
    )
    search_ms = round((time.time() - t_search_start) * 1000, 2)

    logger.info(
        f"[Query] Multi-query retrieved: {sum(len(r) for r in all_results)} raw → "
        f"{len(candidate_chunks)} unique candidates across {num_variants} variants"
    )

    # ------------------------------------------------------------------
    # Step 3: BGE Cross-Encoder Reranking
    # Rerank using the ORIGINAL query (not expanded) for precision
    # ------------------------------------------------------------------
    t_rerank_start = time.time()
    if settings.ENABLE_RERANKER:
        reranker = BGEReranker()
        reranked_chunks = reranker.rerank(
            query=request.query,
            chunks=candidate_chunks,
            top_n=request.top_n,
            score_threshold=request.score_threshold
        )
    else:
        # Reranking is disabled, use raw vector scores and format
        reranked_chunks = []
        for c in candidate_chunks:
            c["rerank_score"] = round(float(c.get("score", 0.0)), 4)
            c["raw_logit"] = 0.0
            c["vector_score"] = round(float(c.get("score", 0.0)), 4)
            reranked_chunks.append(c)
        reranked_chunks = reranked_chunks[:request.top_n]

    rerank_ms = round((time.time() - t_rerank_start) * 1000, 2)

    logger.info(f"[Query] After reranking (enabled={settings.ENABLE_RERANKER}): {len(reranked_chunks)} chunks retained (top_n={request.top_n})")

    # ------------------------------------------------------------------
    # Step 4: LLM Answer Generation
    # ------------------------------------------------------------------
    t_llm_start = time.time()
    llm_service = LLMGenerator(gemini_api_key=api_key)
    result = llm_service.generate_answer(
        query=request.query,
        context_chunks=reranked_chunks
    )
    llm_ms = round((time.time() - t_llm_start) * 1000, 2)
    total_ms = round((time.time() - t_start) * 1000, 2)

    token_usage = result.get("token_usage", {})

    metrics = QueryMetrics(
        embedding_time_ms=embed_ms,
        qdrant_search_time_ms=search_ms,
        rerank_time_ms=rerank_ms,
        llm_gen_time_ms=llm_ms,
        total_latency_ms=total_ms,
        candidate_chunks_retrieved=len(candidate_chunks),
        reranked_chunks_retained=len(reranked_chunks),
        multi_queries_used=num_variants,
        prompt_tokens=token_usage.get("prompt_tokens", 0),
        completion_tokens=token_usage.get("completion_tokens", 0),
        total_tokens=token_usage.get("total_tokens", 0),
        estimated_cost_usd=token_usage.get("estimated_cost_usd", 0.0),
        estimated_cost_inr=token_usage.get("estimated_cost_inr", 0.0)
    )

    return QueryResponse(
        query=request.query,
        answer=result["answer"],
        sources=result["sources"],
        metrics=metrics,
        model_used=result["model_used"]
    )
