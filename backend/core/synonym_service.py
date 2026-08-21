"""
synonym_service.py
------------------
Handles document-level synonym/keyword extraction at upload time
and query expansion at search time.

Flow:
  Upload  → extract_and_store_synonyms(text, filename) → Firestore "synonyms/{filename}"
  Query   → get_combined_synonym_map()                 → expand_query(query, map)
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Firestore collection name
SYNONYM_COLLECTION = "synonyms"


# ---------------------------------------------------------------------------
# Synonym Extraction (called at upload time)
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are a semantic indexing assistant for a RAG (Retrieval-Augmented Generation) system.

Analyze the following document text and extract a comprehensive synonym/keyword map to improve search recall.

Return a **pure JSON object** (no markdown, no explanation) with exactly these keys:
- "main_topics": list of 5-10 primary subject areas or concepts in this document
- "synonyms": dict mapping important terms → list of alternate phrasings/synonyms
- "abbreviations": dict mapping abbreviations → their full forms
- "common_queries": list of 10-15 natural-language questions a user might ask about this document
- "domain_keywords": list of important domain-specific keywords

Document text (truncated to first 6000 chars):
---
{text}
---

Respond with ONLY the JSON object. No extra text."""


def extract_and_store_synonyms(
    text: str,
    filename: str,
    gemini_api_key: Optional[str] = None
) -> Optional[Dict]:
    """
    Uses Gemini to extract synonyms/keywords from document text,
    then stores the result in Firestore under synonyms/{filename}.

    Returns the extracted synonym map dict, or None on failure.
    """
    from backend.core.firebase_client import get_firestore_client, is_firebase_enabled
    from backend.core.config import settings

    # Truncate text to keep prompt manageable
    truncated = text[:6000]

    api_key = gemini_api_key or settings.GEMINI_API_KEY
    synonym_map = None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = EXTRACTION_PROMPT.format(text=truncated)
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        import json
        synonym_map = json.loads(raw)
        logger.info(f"[SynonymService] Extracted synonym map for '{filename}': "
                    f"{len(synonym_map.get('synonyms', {}))} synonym entries, "
                    f"{len(synonym_map.get('common_queries', []))} common queries.")

    except Exception as e:
        logger.warning(f"[SynonymService] Synonym extraction failed for '{filename}': {e}. "
                       f"Using fallback keyword extraction.")
        synonym_map = _fallback_keyword_extraction(text, filename)

    # Persist to Firestore (only if enabled)
    if is_firebase_enabled():
        try:
            db = get_firestore_client()
            safe_doc_id = _safe_doc_id(filename)
            db.collection(SYNONYM_COLLECTION).document(safe_doc_id).set({
                "filename": filename,
                "synonym_map": synonym_map,
                "updated_at": _server_timestamp()
            })
            logger.info(f"[SynonymService] Saved synonym map to Firestore: synonyms/{safe_doc_id}")
        except Exception as e:
            logger.warning(f"[SynonymService] Failed to save to Firestore: {e}")

    return synonym_map


def _fallback_keyword_extraction(text: str, filename: str) -> Dict:
    """Simple TF-IDF style keyword fallback when Gemini is unavailable."""
    import re
    from collections import Counter

    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    stopwords = {
        "this", "that", "with", "have", "from", "they", "will", "been",
        "were", "more", "also", "than", "then", "some", "such", "into",
        "through", "during", "before", "after", "above", "below", "each",
        "when", "where", "while", "about", "which", "their", "there",
        "these", "those", "your", "what", "other", "said", "using",
    }
    filtered = [w for w in words if w not in stopwords]
    top_keywords = [word for word, _ in Counter(filtered).most_common(30)]

    return {
        "main_topics": top_keywords[:10],
        "synonyms": {},
        "abbreviations": {},
        "common_queries": [
            f"What does the document say about {kw}?" for kw in top_keywords[:10]
        ],
        "domain_keywords": top_keywords
    }


# ---------------------------------------------------------------------------
# Query Expansion (called at query time)
# ---------------------------------------------------------------------------

def get_combined_synonym_map() -> Dict:
    """
    Fetches and merges all synonym maps from Firestore.
    Returns a combined dict for query expansion.
    """
    from backend.core.firebase_client import get_firestore_client, is_firebase_enabled

    if not is_firebase_enabled():
        return {}

    try:
        db = get_firestore_client()
        docs = db.collection(SYNONYM_COLLECTION).stream()
        combined = {
            "main_topics": [],
            "synonyms": {},
            "abbreviations": {},
            "common_queries": [],
            "domain_keywords": []
        }
        for doc in docs:
            data = doc.to_dict()
            sm = data.get("synonym_map", {})
            combined["main_topics"].extend(sm.get("main_topics", []))
            combined["synonyms"].update(sm.get("synonyms", {}))
            combined["abbreviations"].update(sm.get("abbreviations", {}))
            combined["common_queries"].extend(sm.get("common_queries", []))
            combined["domain_keywords"].extend(sm.get("domain_keywords", []))

        return combined
    except Exception as e:
        logger.warning(f"[SynonymService] Failed to load synonym map from Firestore: {e}")
        return {}


def expand_query(query: str, synonym_map: Dict) -> str:
    """
    Expands the user query by appending related terms found in the synonym map.

    Strategy:
    1. Check if any key in synonym_map["synonyms"] or "domain_keywords" appears in the query.
    2. If match found, append its synonyms/alternatives to the query string.
    3. Expand abbreviations found in the query.
    4. Cap total expansion to keep it manageable.

    Returns the expanded query string.
    """
    if not synonym_map:
        return query

    query_lower = query.lower()
    expansion_terms = []

    # Expand synonyms
    for term, synonyms in synonym_map.get("synonyms", {}).items():
        if term.lower() in query_lower and isinstance(synonyms, list):
            expansion_terms.extend(synonyms[:3])  # max 3 per term

    # Expand abbreviations (both directions)
    for abbr, full_form in synonym_map.get("abbreviations", {}).items():
        if abbr.lower() in query_lower:
            expansion_terms.append(full_form)
        elif full_form.lower() in query_lower:
            expansion_terms.append(abbr)

    # Add domain keywords that overlap with query words
    query_words = set(query_lower.split())
    for kw in synonym_map.get("domain_keywords", []):
        if any(word in kw.lower() for word in query_words if len(word) > 3):
            expansion_terms.append(kw)

    # Deduplicate and cap
    seen = set()
    unique_expansions = []
    for t in expansion_terms:
        t_clean = str(t).strip()
        if t_clean and t_clean.lower() not in seen and t_clean.lower() not in query_lower:
            seen.add(t_clean.lower())
            unique_expansions.append(t_clean)
        if len(unique_expansions) >= 10:
            break

    if unique_expansions:
        expanded = f"{query} {' '.join(unique_expansions)}"
        logger.info(f"[SynonymService] Query expanded: '{query}' → appended {len(unique_expansions)} terms")
        return expanded

    return query


def delete_synonyms_for_file(filename: str) -> bool:
    """Deletes the synonym map document for a given filename from Firestore."""
    from backend.core.firebase_client import get_firestore_client, is_firebase_enabled

    if not is_firebase_enabled():
        return True

    try:
        db = get_firestore_client()
        safe_doc_id = _safe_doc_id(filename)
        db.collection(SYNONYM_COLLECTION).document(safe_doc_id).delete()
        logger.info(f"[SynonymService] Deleted synonyms/{safe_doc_id} from Firestore.")
        return True
    except Exception as e:
        logger.error(f"[SynonymService] Failed to delete synonyms for '{filename}': {e}")
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_doc_id(filename: str) -> str:
    """Converts a filename into a safe Firestore document ID."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', filename)


def _server_timestamp():
    """Returns a Firestore SERVER_TIMESTAMP sentinel."""
    try:
        from google.cloud import firestore as gc_firestore
        return gc_firestore.SERVER_TIMESTAMP
    except Exception:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
