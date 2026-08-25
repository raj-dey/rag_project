import os
import sys
import streamlit as st
import requests
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.core.config import settings

# Page Configuration
st.set_page_config(
    page_title="Enterprise RAG Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for premium look & feel
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }

    /* Metric Card Styling */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8));
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        backdrop-filter: blur(8px);
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #38bdf8;
        margin-top: 4px;
    }
    .metric-value.green { color: #4ade80; }
    .metric-value.orange { color: #fb923c; }

    /* Latency Badge */
    .badge-latency {
        background-color: #1e293b;
        color: #38bdf8;
        border: 1px solid #0284c7;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 8px;
        margin-bottom: 4px;
    }
    .badge-score {
        background-color: #14532d;
        color: #4ade80;
        border: 1px solid #16a34a;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 8px;
        margin-bottom: 4px;
    }
    .badge-cost {
        background-color: #312e81;
        color: #c7d2fe;
        border: 1px solid #6366f1;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 8px;
        margin-bottom: 4px;
    }
    .badge-tokens {
        background-color: #701a75;
        color: #f0abfc;
        border: 1px solid #c026d3;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 8px;
        margin-bottom: 4px;
    }
    .badge-firebase {
        background-color: #7c2d12;
        color: #fed7aa;
        border: 1px solid #ea580c;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 8px;
        margin-bottom: 4px;
    }
    .badge-synapse {
        background-color: #1a1a3e;
        color: #a78bfa;
        border: 1px solid #7c3aed;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 8px;
        margin-bottom: 4px;
    }

    /* File card in admin panel */
    .file-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.8));
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
        transition: border-color 0.2s;
    }
    .file-card:hover {
        border-color: rgba(99, 102, 241, 0.7);
    }
    .file-name {
        font-size: 1rem;
        font-weight: 700;
        color: #e2e8f0;
    }
    .file-meta {
        font-size: 0.78rem;
        color: #64748b;
        margin-top: 2px;
    }
    .firebase-tag {
        background: linear-gradient(90deg, #f97316, #ef4444);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .synonym-tag {
        background: linear-gradient(90deg, #8b5cf6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 0.8rem;
    }

    /* Admin gate */
    .admin-gate {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border: 1px solid rgba(239, 68, 68, 0.4);
        border-radius: 14px;
        padding: 32px;
        text-align: center;
        max-width: 400px;
        margin: 40px auto;
    }
</style>
""", unsafe_allow_html=True)

# Application State Initialization
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
# Resolve the Backend URL from Secrets or Env Variables
backend_url_secret = None
try:
    if "BACKEND_URL" in st.secrets:
        backend_url_secret = st.secrets["BACKEND_URL"]
    elif "API_URL" in st.secrets:
        backend_url_secret = st.secrets["API_URL"]
except Exception:
    pass

default_api_url = backend_url_secret or os.getenv("BACKEND_URL") or os.getenv("API_URL") or "http://localhost:8000"

# Set or override cached localhost:8000 if we have a valid cloud URL
if "api_url" not in st.session_state or (st.session_state.api_url == "http://localhost:8000" and default_api_url != "http://localhost:8000"):
    st.session_state.api_url = default_api_url
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "confirm_delete_all" not in st.session_state:
    st.session_state.confirm_delete_all = False

# Sidebar - Settings & Pipeline Parameters
with st.sidebar:
    st.markdown("<h1 style='font-size: 3rem; margin-top: -20px; margin-bottom: 5px;'>🧠</h1>", unsafe_allow_html=True)
    st.title("RAG Controls")
    
    api_url = st.text_input("Backend API Server URL", value=st.session_state.api_url)
    st.session_state.api_url = api_url.rstrip("/")

    st.markdown("---")
    st.subheader("🔑 API & Provider Setup")
    gemini_key = st.text_input(
        "Gemini API Key (Optional)",
        value=settings.GEMINI_API_KEY or "",
        type="password",
        help="If provided, uses Google Gemini (gemini-3.6-flash) & gemini-embedding-001. If omitted, uses local BGE embeddings and fallback synthesizer."
    )
    
    embedding_provider = st.selectbox(
        "Embedding Model",
        options=["huggingface", "gemini"],
        index=0,
        help="huggingface = BAAI/bge-small-en-v1.5 (Local/Free), gemini = gemini-embedding-001 (Google)"
    )

    st.markdown("---")
    st.subheader("⚙️ Pipeline Hyperparameters")
    
    chunk_size = st.slider("Chunk Size (Tokens/Chars)", min_value=250, max_value=4000, value=1200, step=50)
    max_overlap = max(0, chunk_size - 50)
    chunk_overlap = st.slider("Chunk Overlap", min_value=0, max_value=max_overlap, value=min(300, max_overlap), step=25)
    
    top_k = st.slider("Top-K Candidates (Qdrant Vector Search)", min_value=1, max_value=100, value=50)
    top_n = st.slider("Top-N Retained (BGE Reranker)", min_value=1, max_value=30, value=12)
    score_threshold = st.slider("Min Rerank Relevance Score", min_value=0.0, max_value=1.0, value=0.05, step=0.01)

    st.markdown("---")
    st.caption("🚀 Production RAG Pipeline v1.1.0 | FastAPI + Qdrant + Firebase + BGE")

# Header & System Health Status
st.title("⚡ Enterprise RAG Assistant")
st.caption("Multi-format Document Ingestion · Qdrant Vector Storage · BGE Cross-Encoder Reranking · Firebase Storage · Synonym Query Expansion")

# System Health Check
def check_health():
    try:
        # Increased timeout to 15 seconds to give Render's spin-up time a chance
        r = requests.get(f"{st.session_state.api_url}/api/health", timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "healthy":
                st.session_state.firebase_enabled = data.get("firebase_enabled", False)
                return True, data
            else:
                st.session_state.firebase_enabled = False
                return False, data
    except Exception as e:
        st.session_state.firebase_enabled = False
        return False, {"error": str(e)}
    st.session_state.firebase_enabled = False
    return False, {}

is_healthy, health_data = check_health()
firebase_enabled = st.session_state.get("firebase_enabled", False)

col_status1, col_status2, col_status3, col_status4 = st.columns(4)
with col_status1:
    status_color = "🟢 Online" if is_healthy else "🔴 Offline"
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Backend Service</div><div class='metric-value'>{status_color}</div></div>", unsafe_allow_html=True)

with col_status2:
    total_chunks = health_data.get("vector_store", {}).get("total_chunks", 0) if is_healthy else 0
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Qdrant Vector Chunks</div><div class='metric-value'>{total_chunks:,}</div></div>", unsafe_allow_html=True)

with col_status3:
    unique_files = health_data.get("vector_store", {}).get("unique_files", 0) if is_healthy else 0
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Indexed Documents</div><div class='metric-value green'>{unique_files}</div></div>", unsafe_allow_html=True)

with col_status4:
    firebase_status = "Active" if firebase_enabled else "⚪ Disabled"
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Firebase Storage</div><div class='metric-value orange'>{firebase_status}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Render Cold Start Notice
if not is_healthy:
    st.info(f"ℹ️ **Render Free Tier Notice**: Your backend on Render may be sleeping due to inactivity. It can take **50–90 seconds** to wake up. Click this link to open the backend directly and wake it up: [{st.session_state.api_url}/api/health]({st.session_state.api_url}/api/health), then refresh this Streamlit page once the backend responds.")
    if "error" in health_data:
        st.error(f"❌ **Backend Error Details:**\n\n`{health_data['error']}`")
        if "traceback" in health_data:
            with st.expander("🛠️ View Full Stack Trace"):
                st.code(health_data["traceback"])

# Main Navigation Tabs
tab_query, tab_admin = st.tabs(["💬 Query & Chat", "🛡️ Admin Panel"])

# ============================================================
# TAB 1: Query & Chat Interface
# ============================================================
with tab_query:
    col_chat_title, col_chat_clear = st.columns([4, 1])
    with col_chat_title:
        st.subheader("💬 AI Intelligence Assistant")
        st.caption("Ask questions across all indexed documents. Queries are auto-expanded with document synonyms for better recall.")
    with col_chat_clear:
        if st.button("🗑️ Clear Chat", type="secondary", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    # Display Chat History
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            if "sources" in msg and msg["sources"]:
                with st.expander("📚 View Verified Source Citations"):
                    for src in msg["sources"]:
                        st.markdown(f"**{src['source_tag']}** — `{src['filename']}` ({src.get('location', 'Document Body')})")
                        st.caption(f"Vector Sim Score: `{src.get('vector_score', 0):.3f}` | BGE Rerank Score: `{src.get('rerank_score', 0):.3f}`")
                        st.code(src.get("text_snippet", ""), language="text")

            if "metrics" in msg and msg["metrics"]:
                metrics = msg["metrics"]
                model_used = msg.get("model_used", "LLM")
                cost_usd = metrics.get("estimated_cost_usd", 0.0)
                cost_inr = metrics.get("estimated_cost_inr", 0.0)
                p_tok = metrics.get("prompt_tokens", 0)
                c_tok = metrics.get("completion_tokens", 0)
                t_tok = metrics.get("total_tokens", 0)
                mq = metrics.get("multi_queries_used", 1)

                st.markdown(
                    f"<span class='badge-score'>🤖 {model_used}</span>"
                    f"<span class='badge-synapse'>🔤 Synonym Expanded</span>"
                    f"<span class='badge-synapse'>🔍 {mq} Query Variants</span>"
                    f"<span class='badge-cost'>💰 Est. Cost: ${cost_usd:.5f} (₹{cost_inr:.3f})</span>"
                    f"<span class='badge-tokens'>🪙 Tokens: {t_tok:,} (Prompt: {p_tok:,}, Gen: {c_tok:,})</span>"
                    f"<span class='badge-latency'>Search: {metrics['qdrant_search_time_ms']}ms</span>"
                    f"<span class='badge-latency'>Rerank: {metrics['rerank_time_ms']}ms</span>"
                    f"<span class='badge-latency'>LLM: {metrics['llm_gen_time_ms']}ms</span>"
                    f"<span class='badge-latency'>Total: {metrics['total_latency_ms']}ms</span>",
                    unsafe_allow_html=True
                )

    # Chat Input Box
    user_query = st.chat_input("Ask a question about your uploaded documents...")
    final_query = user_query

    if final_query:
        st.session_state.chat_history.append({"role": "user", "content": final_query})
        with st.chat_message("user"):
            st.markdown(final_query)

        with st.chat_message("assistant"):
            with st.spinner("Searching vectors, reranking relevance & synthesizing response..."):
                try:
                    payload = {
                        "query": final_query,
                        "top_k": top_k,
                        "top_n": top_n,
                        "score_threshold": score_threshold,
                        "gemini_api_key": gemini_key if gemini_key else None,
                        "model": "gemini-3.6-flash"
                    }
                    headers = {}
                    if gemini_key:
                        headers["X-Gemini-API-Key"] = gemini_key

                    res = requests.post(
                        f"{st.session_state.api_url}/api/query",
                        json=payload,
                        headers=headers,
                        timeout=120
                    )

                    if res.status_code == 200:
                        data = res.json()
                        answer = data["answer"]
                        sources = data.get("sources", [])
                        metrics = data.get("metrics", {})
                        model_used = data.get("model_used", "gemini-3.6-flash")

                        st.markdown(answer)

                        if sources:
                            with st.expander("📚 View Verified Source Citations"):
                                for src in sources:
                                    st.markdown(f"**{src['source_tag']}** — `{src['filename']}` ({src.get('location', 'Document Body')})")
                                    st.caption(f"Vector Sim Score: `{src.get('vector_score', 0):.3f}` | BGE Rerank Score: `{src.get('rerank_score', 0):.3f}`")
                                    st.code(src.get("text_snippet", ""), language="text")

                        cost_usd = metrics.get("estimated_cost_usd", 0.0)
                        cost_inr = metrics.get("estimated_cost_inr", 0.0)
                        p_tok = metrics.get("prompt_tokens", 0)
                        c_tok = metrics.get("completion_tokens", 0)
                        t_tok = metrics.get("total_tokens", 0)
                        mq = metrics.get("multi_queries_used", 1)

                        st.markdown(
                            f"<span class='badge-score'>🤖 {model_used}</span>"
                            f"<span class='badge-synapse'>🔤 Synonym Expanded</span>"
                            f"<span class='badge-synapse'>🔍 {mq} Query Variants</span>"
                            f"<span class='badge-cost'>💰 Est. Cost: ${cost_usd:.5f} (₹{cost_inr:.3f})</span>"
                            f"<span class='badge-tokens'>🪙 Tokens: {t_tok:,} (Prompt: {p_tok:,}, Gen: {c_tok:,})</span>"
                            f"<span class='badge-latency'>Search: {metrics['qdrant_search_time_ms']}ms</span>"
                            f"<span class='badge-latency'>Rerank: {metrics['rerank_time_ms']}ms</span>"
                            f"<span class='badge-latency'>LLM: {metrics['llm_gen_time_ms']}ms</span>"
                            f"<span class='badge-latency'>Total: {metrics['total_latency_ms']}ms</span>",
                            unsafe_allow_html=True
                        )

                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": answer,
                            "sources": sources,
                            "metrics": metrics,
                            "model_used": model_used
                        })
                        st.rerun()

                    else:
                        err_detail = res.json().get("detail", "Error processing request")
                        st.error(f"API Error ({res.status_code}): {err_detail}")

                except Exception as e:
                    st.error(f"Failed to connect to backend query endpoint: {e}")


# Tab 2 (Upload Documents) was integrated directly into Tab 2 (Admin Panel) below.


# ============================================================
# TAB 3: Admin Panel
# ============================================================
with tab_admin:
    st.subheader("🛡️ Admin Panel")

    # Admin Password Gate
    if not st.session_state.admin_authenticated:
        st.markdown("""
        <div class='admin-gate'>
            <div style='font-size:2rem;margin-bottom:8px;'>🔐</div>
            <div style='font-size:1.1rem;font-weight:700;color:#e2e8f0;'>Admin Access Required</div>
            <div style='font-size:0.85rem;color:#64748b;margin-top:4px;'>Enter your admin password to manage documents.</div>
        </div>
        """, unsafe_allow_html=True)

        col_pw1, col_pw2, col_pw3 = st.columns([1, 2, 1])
        with col_pw2:
            admin_pw = st.text_input("Admin Password", type="password", key="admin_pw_input", label_visibility="collapsed", placeholder="Enter admin password...")
            if st.button("🔓 Unlock Admin Panel", type="primary", use_container_width=True):
                if admin_pw == settings.ADMIN_PASSWORD:
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Incorrect password.")
        st.stop()

    # --- Admin Panel Content (authenticated) ---
    col_admin_title, col_logout = st.columns([4, 1])
    with col_admin_title:
        st.markdown("### 📂 Document Management")
        if firebase_enabled:
            st.caption("🔥 Firebase Active — Showing files from Firestore + Firebase Storage. Deletion cascades to Qdrant + Firestore + Storage.")
        else:
            st.caption("⚪ Firebase disabled — Showing files from Qdrant only. Deletion removes vector chunks only.")
    with col_logout:
        if st.button("🔒 Logout", type="secondary", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

    if not is_healthy:
        st.error("⚠️ Backend API is offline. Start the FastAPI backend to manage documents.")
        st.stop()

    # --- Document Ingestion & Upload (Integrated) ---
    st.markdown("---")
    st.markdown("#### 📁 Upload & Index New Documents")
    if firebase_enabled:
        st.info("🔥 **Firebase Active** — Files will be stored in Firebase Storage + metadata tracked in Firestore + synonyms extracted automatically.")
    else:
        st.warning("⚪ Firebase is disabled. Files will be indexed into Qdrant only (no persistent file storage). Enable in `.env` to activate Firebase.")

    uploaded_files = st.file_uploader(
        "Select files to upload and index into Qdrant",
        type=["pdf", "docx", "doc", "xlsx", "xls", "csv", "txt", "md"],
        accept_multiple_files=True,
        key="admin_file_uploader"
    )

    if uploaded_files:
        if st.button("🚀 Process & Index Documents", type="primary", key="admin_process_btn"):
            files_to_send = []
            for file in uploaded_files:
                mime_type = file.type if file.type else "application/octet-stream"
                files_to_send.append(("files", (file.name, file.getvalue(), mime_type)))

            with st.spinner("Parsing documents, splitting chunks, generating embeddings & uploading to Firebase..."):
                try:
                    params = {
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap,
                        "embedding_provider": embedding_provider
                    }
                    if gemini_key:
                        params["gemini_api_key"] = gemini_key

                    headers = {}
                    if gemini_key:
                        headers["X-Gemini-API-Key"] = gemini_key

                    res = requests.post(
                        f"{st.session_state.api_url}/api/upload",
                        files=files_to_send,
                        params=params,
                        headers=headers,
                        timeout=300
                    )
                    if res.status_code == 200:
                        data = res.json()
                        st.success(f"✅ {data['message']}")
                        col_r1, col_r2, col_r3 = st.columns(3)
                        with col_r1:
                            st.metric("Files Indexed", data["files_processed"])
                        with col_r2:
                            st.metric("Chunks Created", data["total_chunks_created"])
                        with col_r3:
                            st.metric("Processing Time", f"{data['processing_time_seconds']}s")

                        if data.get("firebase_storage"):
                            st.markdown(
                                "<span class='badge-firebase'>🔥 Uploaded to Firebase Storage</span>"
                                "<span class='badge-synapse'>🔤 Synonym extraction running in background...</span>",
                                unsafe_allow_html=True
                            )
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Ingestion failed: {res.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend upload endpoint: {e}")

    st.markdown("---")
    st.markdown("#### 📄 Current Indexed Documents")

    # --- Fetch Documents ---
    try:
        docs_res = requests.get(f"{st.session_state.api_url}/api/documents", timeout=10)
        docs_data = docs_res.json() if docs_res.status_code == 200 else {}
    except Exception:
        docs_data = {}

    source = docs_data.get("source", "qdrant")
    firebase_docs = docs_data.get("documents", []) if source == "firestore" else []
    qdrant_stats = docs_data.get("qdrant_stats", docs_data) if source == "firestore" else docs_data
    filenames_qdrant = qdrant_stats.get("filenames", [])

    # Merge: Firestore docs take priority
    if firebase_docs:
        st.markdown(f"**{len(firebase_docs)} document(s) tracked in Firebase Firestore:**")
        st.markdown("---")

        for doc in firebase_docs:
            fn = doc.get("filename", "Unknown")
            chunks = doc.get("total_chunks", "?")
            size_bytes = doc.get("file_size_bytes", 0)
            size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes else "?"
            uploaded_at = doc.get("uploaded_at", "")
            storage_url = doc.get("storage_url", "")
            file_type = doc.get("file_type", fn.split(".")[-1].upper())

            # Format upload time
            try:
                dt = datetime.fromisoformat(uploaded_at.replace("Z", "+00:00"))
                time_str = dt.strftime("%d %b %Y, %H:%M")
            except Exception:
                time_str = uploaded_at[:19] if uploaded_at else "—"

            col_info, col_actions = st.columns([4, 1])
            with col_info:
                st.markdown(f"""
                <div class='file-card'>
                    <div class='file-name'>📄 {fn}</div>
                    <div class='file-meta'>
                        <span class='firebase-tag'>🔥 Firebase</span> &nbsp;
                        Type: <b>{file_type.upper()}</b> &nbsp;|&nbsp;
                        Chunks: <b>{chunks}</b> &nbsp;|&nbsp;
                        Size: <b>{size_str}</b> &nbsp;|&nbsp;
                        Uploaded: <b>{time_str}</b>
                        {f"&nbsp;|&nbsp; <a href='{storage_url}' target='_blank' style='color:#38bdf8;'>📥 Download</a>" if storage_url else ""}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_actions:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Delete", key=f"del_{fn}", type="secondary", use_container_width=True):
                    with st.spinner(f"Deleting '{fn}' from Qdrant + Firestore + Storage..."):
                        try:
                            del_res = requests.delete(
                                f"{st.session_state.api_url}/api/documents/{fn}",
                                timeout=30
                            )
                            if del_res.status_code == 200:
                                del_data = del_res.json()
                                st.success(del_data.get("message", f"'{fn}' deleted successfully."))
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error(f"Delete failed: {del_res.text}")
                        except Exception as e:
                            st.error(f"Error: {e}")

    elif filenames_qdrant:
        # Fallback: show Qdrant-only files (no Firebase metadata)
        st.info("ℹ️ Showing files from Qdrant (Firebase not enabled or no Firestore records found).")
        st.markdown(f"**{len(filenames_qdrant)} file(s) indexed in Qdrant:**")
        st.markdown("---")

        for fn in filenames_qdrant:
            col_info, col_actions = st.columns([4, 1])
            with col_info:
                st.markdown(f"""
                <div class='file-card'>
                    <div class='file-name'>📄 {fn}</div>
                    <div class='file-meta'>Indexed in Qdrant · No Firebase metadata available</div>
                </div>
                """, unsafe_allow_html=True)
            with col_actions:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Delete", key=f"del_q_{fn}", type="secondary", use_container_width=True):
                    with st.spinner(f"Deleting '{fn}' chunks from Qdrant..."):
                        try:
                            del_res = requests.delete(
                                f"{st.session_state.api_url}/api/documents/{fn}",
                                timeout=30
                            )
                            if del_res.status_code == 200:
                                del_data = del_res.json()
                                st.success(del_data.get("message", f"'{fn}' deleted."))
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error(f"Delete failed: {del_res.text}")
                        except Exception as e:
                            st.error(f"Error: {e}")
    else:
        st.info("📭 No documents are currently indexed. Go to the 'Upload Documents' tab to add your first files.")

    # --- Danger Zone: Clear All ---
    st.markdown("---")
    st.markdown("### ⚠️ Danger Zone")
    st.markdown("Permanently deletes **all** documents from Qdrant, Firestore, and Firebase Storage.")

    col_danger1, col_danger2 = st.columns([2, 1])
    with col_danger1:
        if not st.session_state.confirm_delete_all:
            if st.button("☠️ Clear ALL Documents", type="secondary"):
                st.session_state.confirm_delete_all = True
                st.rerun()
        else:
            st.error("⚠️ Are you absolutely sure? This cannot be undone.")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("✅ Yes, Delete Everything", type="primary", use_container_width=True):
                    with st.spinner("Wiping all data from Qdrant + Firestore + Storage..."):
                        try:
                            res = requests.delete(f"{st.session_state.api_url}/api/documents", timeout=60)
                            if res.status_code == 200:
                                st.success("✅ All documents cleared successfully!")
                                st.session_state.confirm_delete_all = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Failed to clear collection.")
                        except Exception as e:
                            st.error(f"Error: {e}")
            with col_no:
                if st.button("❌ Cancel", type="secondary", use_container_width=True):
                    st.session_state.confirm_delete_all = False
                    st.rerun()
