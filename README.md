<div align="center">

# ⚡ Enterprise Production RAG System
### End-to-End Retrieval-Augmented Generation with FastAPI, Qdrant, BGE Cross-Encoder Reranker & Streamlit

[![Live Demo](https://img.shields.io/badge/🚀%20Live%20Demo-Streamlit%20Cloud-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://ragproject-raj-dey.streamlit.app)
[![GitHub Repo](https://img.shields.io/badge/GitHub-raj--dey%2Frag__project-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/raj-dey/rag_project)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-DC2626?style=for-the-badge&logo=qdrant&logoColor=white)](https://qdrant.tech)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-BGE%20Reranker-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/BAAI)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore%20%26%20Storage-FFA611?style=for-the-badge&logo=firebase&logoColor=white)](https://firebase.google.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<br>

<p align="center">
  <b>A production-grade, enterprise-ready RAG platform engineered with multi-format ingestion, two-stage vector retrieval, BGE cross-encoder reranking, automatic domain synonym expansion, multi-query generation, strict source attribution, live token & cost analytics, and resilient multi-tier LLM fallback.</b>
</p>

[🌐 Live Demo](#-live-demo--hosted-deployments) • [🌟 Key Features](#-key-features) • [🏗️ Architecture](#-system-architecture) • [💻 Tech Stack](#-technology-stack) • [📁 Directory Structure](#-directory-structure) • [⚡ Quick Start](#-quick-start) • [⚙️ Configuration](#-configuration-guide-env) • [📡 API Reference](#-api-reference) • [🖥️ Frontend UI](#-interactive-ui-walkthrough) • [🚀 Hosting & Deployment](#-hosting--deployment-guide)

---

</div>

## 🌐 Live Demo & Hosted Deployments

| Component | Platform / Host | Live URL / Endpoint | Status |
| :--- | :--- | :--- | :---: |
| **Frontend Web App** | **Streamlit Community Cloud** | [👉 ragproject-raj-dey.streamlit.app](https://ragproject-raj-dey.streamlit.app) | ![Online](https://img.shields.io/badge/Status-Online-brightgreen?style=flat-square) |
| **Backend REST API** | **Render Cloud (FastAPI)** | [👉 FastAPI Health Endpoint](https://ragproject-raj-dey.streamlit.app) *(via UI settings)* | ![Online](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square) |
| **Vector Engine** | **Qdrant** | Local Persistent Storage (`./qdrant_storage`) or Qdrant Cloud | ![Active](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square) |
| **Cloud Storage** | **Firebase Firestore & Storage** | Firestore Catalog + Google Cloud Storage Bucket | ![Optional](https://img.shields.io/badge/Status-Configurable-blue?style=flat-square) |

> [!TIP]
> **Try the Live Demo**: Open [ragproject-raj-dey.streamlit.app](https://ragproject-raj-dey.streamlit.app) to interact with the query assistant and explore verified citations, latency profiling, and token cost estimations. For administrative document management, unlock the **Admin Panel** tab using the configured admin password.

---

## 📖 Project Description & Overview

Traditional Retrieval-Augmented Generation (RAG) prototypes often fail in production due to four critical bottlenecks:
1. **Low Retrieval Precision**: Vector-only semantic search frequently surfaces marginally related chunks that dilute generation quality.
2. **Vocabulary Mismatch**: Users formulate questions using terminology or acronyms different from the exact phrases written in documents.
3. **Hallucinations & Untracked Citations**: Models generate confident responses without explicit, verifiable line-item citations.
4. **Cloud Rate Limits & Fragility**: Single-LLM systems crash when hitting provider rate limits or unexpected network downtime.

**Enterprise Production RAG** resolves these challenges with a resilient, two-stage retrieval pipeline:
- **Two-Stage Re-Ranking**: Qdrant retrieves broad candidate chunks ($K=50$), and a **BGE Cross-Encoder** model re-scores and filters them down to the top $N=12$ highest-relevance contexts.
- **Automated Synonym Mining & Multi-Query Expansion**: Incoming queries are expanded with mined domain vocabulary and multi-angle variants to eliminate missed boundary contexts.
- **Fail-Safe 3-Tier Fallback Cascade**: Primary generation via **Google Gemini Flash**, with automatic instant fallback to **Local Ollama (Llama-3)**, followed by a deterministic **Offline Context Synthesizer**.
- **Full Operational Observability**: Live metric tracking of search, reranking, and generation latency, alongside exact token counting and estimated cost calculations in both **USD ($)** and **INR (₹)**.

---

## 🌟 Key Features

### 📄 Multi-Format Ingestion Engine
- **Supported File Types**: High-fidelity parsing of **PDF** (`PyMuPDF`), **Word DOCX** (`python-docx`), **Excel Workbooks** (`openpyxl` / `pandas`), **CSV** spreadsheets, and plain **TXT / Markdown**.
- **Granular Metadata Extraction**: Automatically captures filename, page number, sheet name, section title, and character lengths to ensure end-to-end provenance.

### 🧠 Intelligent Recursive Chunking
- **Structure-Preserving Splitting**: Hierarchical text splitting across natural text boundaries (`\n\n` $\to$ `\n` $\to$ `. ` $\to$ `; ` $\to$ `, ` $\to$ ` `).
- **Zero Boundary Information Loss**: Configured with 1,200 character chunks and 300 character overlap, generating unique UUIDs for each chunk.

### ⚡ Dual Embedding Architecture
- **Cloud Embeddings**: Google Gemini (`gemini-embedding-001`, **3,072 dimensions**) with automated batching in chunks of 90 to respect provider quotas.
- **Local Embeddings**: HuggingFace Sentence Transformers (`BAAI/bge-small-en-v1.5`, **384 dimensions**) for zero-cost, private, high-speed vectorization.

### 🗄️ Multi-Mode Qdrant Vector Store
- **3 Deployment Modes**:
  - `disk`: Persistent on-disk vector storage inside `./qdrant_storage`.
  - `memory`: Ephemeral in-memory vector store for unit tests and local experiments.
  - `server`: Remote connection to local Qdrant server or managed Qdrant Cloud clusters with API key security.
- **Cosine Distance Optimization**: Fast cosine similarity indexing with metadata payload filtering.

### 🎯 Two-Stage Retrieval & Cross-Encoder Reranking
- **High-Recall Candidate Retrieval**: Queries retrieve top $K$ candidate vector matches ($K=50$).
- **Cross-Encoder Precision**: Candidates are re-scored by **BAAI BGE Reranker** (`BAAI/bge-reranker-base`) with sigmoid score normalization, discarding irrelevant context and retaining the top $N$ ($N=12$) chunks for generation.

### 🔤 Domain Synonyms & Multi-Query Expansion
- **Background Synonym Mining**: Uses Gemini at document ingestion to extract main topics, domain synonyms, acronyms, and anticipated user queries into Firestore.
- **Semantic Expansion**: Enriches incoming queries with learned domain synonyms.
- **Multi-Query Formulation**: Dynamically synthesizes diverse query variants to maximize context recall across disparate sections.

### 🤖 Grounded LLM Generation & 3-Tier Fallback Cascade
- **Strict Grounding**: System prompt forces explicit `[Source N]` tags next to every factual statement, list item, and table value.
- **Standardized Response Layout**: Structured into Direct Answer, Program Details/Specializations, Fees & Cost Breakdown tables (with currency symbols), and Key Takeaways.
- **3-Tier Resilient Fallback**:
  1. **Primary**: Google Gemini API (`gemini-3.6-flash` / `gemini-1.5-flash`).
  2. **Secondary (Local)**: Local Ollama daemon (`llama3` via `http://localhost:11434`).
  3. **Tertiary (Offline)**: Deterministic offline context synthesizer for 100% uptime.

### 📊 Real-Time Observability & Financial Cost Auditing
- **Latency Breakdown**: Real-time profiling of embedding time, Qdrant search time, BGE reranker time, LLM generation time, and total roundtrip latency.
- **Cost & Token Auditing**: Live counts of prompt, completion, and total tokens, with estimated costs computed in both **USD ($)** and **INR (₹)**.

### 🔥 Firebase Hybrid Cloud & Admin Console
- **Firestore & Cloud Storage**: Centralized document cataloging, metadata records, synonym storage, and raw file cloud storage.
- **Cascading Deletion**: Removing a document atomically clears Qdrant vector points, Firestore records, Firebase Storage buckets, and synonym entries.
- **Password-Protected Admin Panel**: Secure interface for document ingestion, collection lifecycle management, and index inspection.

---

## 🏗️ System Architecture

### 1. Document Ingestion Pipeline

```text
[ Document Files ] (PDF, DOCX, XLSX, CSV, TXT, MD)
       │
       ▼
[ DocumentParser ] ── PyMuPDF / python-docx / openpyxl / pandas
       │
       ▼
[ DocumentChunker ] ── RecursiveCharacterTextSplitter (1200 chars, 300 overlap)
       │
       ├──► [ Firebase Storage ] (Original File Backup)
       ├──► [ Firestore ] (Metadata & Chunk ID tracking)
       │
       ▼
[ EmbeddingService ] ── Gemini (3072-dim) OR BGE-small (384-dim)
       │
       ▼
[ Qdrant Vector Store ] ── Cosine Similarity Indexing
       │
       ▼
[ SynonymService (Async) ] ── Gemini extracts topics, synonyms & abbreviations ──► Firestore
```

### 2. Retrieval & Synthesis Pipeline

```text
                  [ User Query ]
                        │
       ┌────────────────┴────────────────┐
       ▼                                 ▼
[ Synonym Expansion ]           [ Multi-Query Variants ]
(Firestore Synonym Map)          (Gemini Query Reformulation)
       └────────────────┬────────────────┘
                        │
                        ▼
             [ Embedding Generation ]
                        │
                        ▼
           [ Qdrant Vector Search ] ── (Top-K: 50 Candidates)
                        │
                        ▼
             [ Merge & Deduplicate ]
                        │
                        ▼
          [ BGE Cross-Encoder Reranker ] ── (Sigmoid score normalization & thresholding)
                        │
                        ▼
            [ Top-N Ranked Context Chunks ] ── (Top-N: 12 Chunks)
                        │
                        ▼
       ┌───────────────────────────────────────────────┐
       │             LLM Generation Engine             │
       │                                               │
       │   [1] Google Gemini (gemini-3.6-flash)        │
       │                   │ (on error / 429 quota)    │
       │                   ▼                           │
       │   [2] Local Ollama (llama3)                   │
       │                   │ (on offline / unreachable)│
       │                   ▼                           │
       │   [3] Offline Context Synthesizer             │
       └───────────────────────┬───────────────────────┘
                               │
                               ▼
[ Grounded Answer with [Source N] Citations + Latency & Cost Metrics ]
```

---

## 💻 Technology Stack

| Category | Component / Library | Purpose |
| :--- | :--- | :--- |
| **Backend API** | [FastAPI](https://fastapi.tiangolo.com/) | Asynchronous, OpenAPI-compliant REST API framework |
| **ASGI Server** | [Uvicorn](https://www.uvicorn.org/) | High-concurrency production ASGI server |
| **Frontend UI** | [Streamlit](https://streamlit.io/) | Interactive dashboard with chat, metrics, and admin console |
| **Vector Database** | [Qdrant](https://qdrant.tech/) | Vector search engine (Disk, Memory, or Cloud Server modes) |
| **Document Parsers** | `PyMuPDF`, `python-docx`, `openpyxl`, `pandas` | Text and tabular extraction from PDFs, Word Docs, and Spreadsheets |
| **Text Chunking** | Custom recursive chunker & `langchain-text-splitters` | Structure-aware text splitting with metadata preservation |
| **Embedding Models** | Google Gemini `gemini-embedding-001` / HF `bge-small-en-v1.5` | Dense vector generation for semantic similarity |
| **Cross-Encoder** | HuggingFace `BAAI/bge-reranker-base` | Two-stage relevance scoring and candidate re-ranking |
| **Primary LLM** | Google Gemini `gemini-3.6-flash` / `gemini-1.5-flash` | Grounded generative answer synthesis with citations |
| **Local Fallback LLM** | [Ollama](https://ollama.ai/) (`llama3`) | Offline/local LLM execution when API limits are reached |
| **Cloud Storage** | Google Firebase (Firestore & Storage) | Distributed metadata storage, document files & synonym maps |
| **Config & Typing** | `pydantic-settings` & `pydantic v2` | Strict environment variable parsing and request validation |

---

## 📁 Directory Structure

```text
rag_project/
├── backend/
│   ├── api/
│   │   ├── query.py              # /api/query: multi-query, search, reranking & LLM pipeline
│   │   └── upload.py             # /api/upload, /api/documents: ingestion & lifecycle endpoints
│   ├── core/
│   │   ├── chunking.py           # RecursiveCharacterTextSplitter & DocumentChunker
│   │   ├── config.py             # Pydantic BaseSettings for application configuration
│   │   ├── document_parser.py    # Multi-format parsers (PDF, DOCX, XLSX, CSV, TXT, MD)
│   │   ├── embeddings.py         # EmbeddingService for Google Gemini & HuggingFace models
│   │   ├── firebase_client.py    # Firebase Admin SDK initialization (Firestore & Storage)
│   │   ├── llm.py                # LLMGenerator: prompt engineering, Gemini, Ollama & fallback
│   │   ├── qdrant_client.py      # QdrantVectorStore client (Disk, Memory, Server modes)
│   │   ├── reranker.py           # BGEReranker cross-encoder scoring & sigmoid normalization
│   │   └── synonym_service.py    # Synonym mining, Firestore persistence & query expansion
│   ├── main.py                   # FastAPI application entry point, CORS & lifespan hooks
│   └── requirements.txt          # Backend Python dependencies
├── frontend/
│   ├── app.py                    # Streamlit web application & admin dashboard
│   └── requirements.txt          # Frontend Python dependencies
├── .devcontainer/
│   └── devcontainer.json         # DevContainer specification for VS Code / Codespaces
├── .streamlit/
│   └── config.toml               # Streamlit server & theme settings
├── qdrant_storage/               # Local on-disk Qdrant vector database files
├── .env.example                  # Template of all environment variables
├── requirements.txt              # Consolidated project dependencies
└── README.md                     # Comprehensive project documentation
```

---

## ⚡ Quick Start

### Prerequisites
- **Python 3.10+** installed
- *(Optional)* **Google Gemini API Key** ([Get one from Google AI Studio](https://aistudio.google.com/))
- *(Optional)* **Ollama** installed locally for local LLM fallback ([ollama.ai](https://ollama.ai/))
- *(Optional)* **Firebase Service Account** for cloud document persistence

---

### Step 1: Clone the Repository & Set Up Environment

```bash
# Clone the repository
git clone https://github.com/raj-dey/rag_project.git
cd rag_project

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS / Linux:
source venv/bin/activate
# On Windows (Command Prompt / PowerShell):
# venv\Scripts\activate
```

---

### Step 2: Install Dependencies

```bash
# Install consolidated dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note**: If using local HuggingFace embeddings and BGE reranker, PyTorch and sentence-transformers are included in `backend/requirements.txt`.

---

### Step 3: Configure Environment Variables

Copy the example `.env.example` file to `.env`:

```bash
cp .env.example .env
```

Open `.env` in your editor and configure your settings:

```dotenv
# Gemini API Key (for LLM generation and embeddings)
GEMINI_API_KEY=your_gemini_api_key_here

# Admin Password for Streamlit Admin Tab
ADMIN_PASSWORD=your_secure_password
```

*(See the [Configuration Guide](#-configuration-guide-env) section below for detailed options).*

---

### Step 4: Run the FastAPI Backend

Start the FastAPI application from the project root directory:

```bash
PYTHONPATH=. uvicorn backend.main:app --reload --port 8000
```

Verify backend health:
- **API Health Endpoint**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Step 5: Run the Streamlit Frontend

Open a new terminal window, activate the virtual environment, and launch Streamlit:

```bash
cd rag_project
source venv/bin/activate
streamlit run frontend/app.py
```

- **Streamlit Web Application**: [http://localhost:8501](http://localhost:8501)

---

## ⚙️ Configuration Guide (`.env`)

All parameters are managed through environment variables or a `.env` file via `backend/core/config.py`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| **`APP_NAME`** | `Production RAG Backend` | Name identifier for the backend service |
| **`DEBUG`** | `True` | Enables debug logging and verbose output |
| **`QDRANT_MODE`** | `disk` | Vector store mode: `disk`, `memory`, or `server` |
| **`QDRANT_PATH`** | `./qdrant_storage` | Storage directory when `QDRANT_MODE=disk` |
| **`QDRANT_HOST`** | `localhost` | Qdrant host or cloud endpoint when `QDRANT_MODE=server` |
| **`QDRANT_PORT`** | `6333` | Port for Qdrant server connection |
| **`QDRANT_API_KEY`** | `None` | API key for authenticated Qdrant Cloud clusters |
| **`QDRANT_COLLECTION_NAME`** | `rag_documents` | Collection name in Qdrant |
| **`EMBEDDING_PROVIDER`** | `huggingface` | Embedding provider: `huggingface` or `gemini` |
| **`HF_EMBEDDING_MODEL`** | `BAAI/bge-small-en-v1.5` | HuggingFace embedding model (384 dimensions) |
| **`GEMINI_EMBEDDING_MODEL`** | `gemini-embedding-001` | Google Gemini embedding model (3072 dimensions) |
| **`ENABLE_RERANKER`** | `false` | Enable/disable BGE cross-encoder reranker stage |
| **`RERANKER_MODEL_NAME`** | `BAAI/bge-reranker-base` | Cross-encoder model used for reranking |
| **`GEMINI_API_KEY`** | `None` | Google Gemini API key |
| **`GEMINI_MODEL`** | `gemini-3.6-flash` | Gemini model name (`gemini-3.6-flash`, `gemini-1.5-flash`) |
| **`TEMPERATURE`** | `0.2` | Generation temperature for factual consistency |
| **`MAX_GENERATION_TOKENS`** | `4096` | Maximum token limit for LLM generation |
| **`OLLAMA_URL`** | `http://localhost:11434` | Endpoint for local Ollama fallback service |
| **`OLLAMA_MODEL`** | `llama3` | Model name to invoke in local Ollama |
| **`DEFAULT_CHUNK_SIZE`** | `1200` | Target character size for text splitter chunks |
| **`DEFAULT_CHUNK_OVERLAP`** | `300` | Overlap character length between sequential chunks |
| **`DEFAULT_TOP_K`** | `50` | Candidate vector chunks retrieved in first stage |
| **`DEFAULT_TOP_N`** | `12` | Highest-ranking chunks forwarded to LLM synthesis |
| **`DEFAULT_SCORE_THRESHOLD`** | `0.05` | Minimum relevance score threshold for candidate chunks |
| **`FIREBASE_ENABLED`** | `false` | Enable Firebase Firestore & Cloud Storage integration |
| **`FIREBASE_SERVICE_ACCOUNT_PATH`** | `./serviceAccountKey.json` | Path to downloaded Firebase service account JSON |
| **`FIREBASE_PROJECT_ID`** | `None` | Firebase project identifier |
| **`FIREBASE_STORAGE_BUCKET`** | `None` | Firebase Cloud Storage bucket name |
| **`ADMIN_PASSWORD`** | `admin123` | Password to unlock Admin Panel tab in Streamlit |

---

## 📡 API Reference

The backend exposes an interactive Swagger documentation portal at `http://localhost:8000/docs`.

### 1. Ingest Documents (`POST /api/upload`)
Uploads one or more files, parses text, splits into overlapping chunks, generates embeddings, stores vectors in Qdrant, updates Firestore metadata, and triggers background synonym extraction.

- **URL**: `/api/upload`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Query / Form Parameters**:
  - `files`: One or more files (`.pdf`, `.docx`, `.xlsx`, `.csv`, `.txt`, `.md`)
  - `chunk_size` *(int, optional)*: Default `1200`
  - `chunk_overlap` *(int, optional)*: Default `300`
  - `embedding_provider` *(str, optional)*: `gemini` or `huggingface`

#### Example `curl` Request:
```bash
curl -X POST "http://localhost:8000/api/upload?chunk_size=1200&chunk_overlap=300" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@annual_report.pdf"
```

#### Example Response (`200 OK`):
```json
{
  "status": "success",
  "message": "Successfully processed and indexed 1 file(s).",
  "files_processed": 1,
  "total_sections_parsed": 18,
  "total_chunks_created": 42,
  "total_vectors_indexed": 42,
  "processing_time_seconds": 2.14,
  "files": ["annual_report.pdf"],
  "firebase_storage": false
}
```

---

### 2. Query Knowledge Base (`POST /api/query`)
Executes the RAG pipeline: expands the query with domain synonyms, generates multi-query variants, retrieves vector candidates from Qdrant, executes cross-encoder reranking, and synthesizes a grounded answer with citations.

- **URL**: `/api/query`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### Example `curl` Request:
```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the semester fee breakdowns and key deadlines?",
    "top_k": 50,
    "top_n": 12,
    "score_threshold": 0.05
  }'
```

#### Example Response (`200 OK`):
```json
{
  "query": "What are the semester fee breakdowns and key deadlines?",
  "answer": "### 🎯 Direct Answer\nThe total semester fee is ₹45,000 payable before August 15th [Source 1].\n\n### 💰 Fees, Costs & Financial Structure\n| Fee Component | Amount (₹) |\n| :--- | :--- |\n| Tuition Fee | ₹35,000 [Source 1] |\n| Examination Fee | ₹5,000 [Source 2] |\n| Library & Lab Deposit | ₹5,000 [Source 1] |\n\n### 💡 Key Takeaways & Context\n- Late submissions incur a fee of ₹500 per week [Source 2].",
  "sources": [
    {
      "source_id": 1,
      "source_tag": "[Source 1]",
      "filename": "fee_structure_2026.pdf",
      "location": "Page 3",
      "rerank_score": 0.942,
      "vector_score": 0.817,
      "text_snippet": "The total semester tuition fee of ₹35,000 along with library deposit..."
    }
  ],
  "metrics": {
    "embedding_time_ms": 42.1,
    "qdrant_search_time_ms": 11.5,
    "rerank_time_ms": 65.2,
    "llm_gen_time_ms": 820.4,
    "total_latency_ms": 939.2,
    "candidate_chunks_retrieved": 50,
    "reranked_chunks_retained": 12,
    "multi_queries_used": 3,
    "prompt_tokens": 1420,
    "completion_tokens": 284,
    "total_tokens": 1704,
    "estimated_cost_usd": 0.000192,
    "estimated_cost_inr": 0.0167
  },
  "model_used": "gemini-3.6-flash"
}
```

---

### 3. Lifecycle & Management Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Inspects vector store status, collection points, embedding provider, and Firebase status |
| `GET` | `/api/documents` | Lists all indexed documents, chunk distributions, and cloud storage URLs |
| `DELETE` | `/api/documents/{filename}` | Cascades deletion of a single document across vectors, metadata & storage |
| `DELETE` | `/api/documents` | Clears all documents, vector points, and metadata |
| `GET` | `/api/debug/chunks` | Scrolls and inspects raw chunks and metadata payloads in Qdrant |

---

## 🖥️ Interactive UI Walkthrough

The frontend is built using **Streamlit** with a tailored dark glassmorphism theme:

### 1. 💬 Query & Chat Assistant
- **Conversational Interface**: Ask natural-language questions across all indexed documents.
- **Verified Source Citations**: Expandable card showing exact source document filename, page number, sheet, vector similarity score, and BGE rerank score with original raw text snippets.
- **Operational Badges**:
  - 🤖 Active Model Indicator (`gemini-3.6-flash`, `ollama/llama3`, `offline-synthesizer`)
  - 🔤 Domain Synonym Expansion badge
  - 🔍 Multi-Query variant counter
  - 💰 Estimated query cost in both USD ($) and INR (₹)
  - 🪙 Token usage audit (Prompt Tokens, Completion Tokens, Total Tokens)
  - ⏱️ Latency breakdown (Search ms, Rerank ms, LLM Gen ms, Total ms)

### 2. 🛡️ Enterprise Admin Panel
- **Password-Protected Gate**: Safeguards document upload and deletion behind `ADMIN_PASSWORD`.
- **Drag-and-Drop Ingestion**: Multi-file batch uploader supporting PDF, Word, Excel, CSV, Text, and Markdown.
- **Document Catalog & Lifecycle**: Inspect chunk counts and download links; trigger cascading deletions across Qdrant, Firestore, Firebase Storage, and synonym maps.

---

## 🚀 Hosting & Deployment Guide

This project is architected for seamless hosting across modern cloud platforms:

### 1. Frontend Hosting: Streamlit Community Cloud
The frontend is deployed live on Streamlit Cloud: [ragproject-raj-dey.streamlit.app](https://ragproject-raj-dey.streamlit.app).

To deploy your own instance:
1. Fork or push this repository to GitHub (`raj-dey/rag_project`).
2. Log into [share.streamlit.io](https://share.streamlit.io/).
3. Click **New app**, select your repository, branch (`main`), and set the main file path to:
   ```text
   frontend/app.py
   ```
4. In **Advanced Settings** $\to$ **Secrets**, configure your environment variables:
   ```toml
   API_URL = "https://your-backend-service.onrender.com"
   ADMIN_PASSWORD = "your_admin_password"
   ```
5. Click **Deploy**.

---

### 2. Backend Hosting: Render (FastAPI + Uvicorn)
1. Log into [render.com](https://render.com/) and create a new **Web Service**.
2. Connect your GitHub repository (`raj-dey/rag_project`).
3. Select **Python 3** as the runtime.
4. Configure Build and Start commands:
   - **Build Command**:
     ```bash
     pip install -r backend/requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
5. In **Environment Variables**, configure:
   ```text
   PYTHONPATH = .
   GEMINI_API_KEY = your_gemini_api_key
   ADMIN_PASSWORD = your_admin_password
   QDRANT_MODE = disk
   QDRANT_PATH = ./qdrant_storage
   FIREBASE_ENABLED = false
   ```
   *(If enabling Firebase on Render, paste your service account JSON directly into `FIREBASE_SERVICE_ACCOUNT_JSON`).*

> [!NOTE]
> **Render Free Tier Spin-Down**: On Render's free tier, services spin down after 15 minutes of inactivity and take ~50–90 seconds to wake up. The Streamlit UI automatically detects this state and displays a direct wake-up link for seamless user experience.

---

### 3. Vector Database Hosting: Qdrant Cloud (Optional)
If you prefer a managed cloud vector database instead of local disk storage:
1. Create a free cluster on [cloud.qdrant.io](https://cloud.qdrant.io/).
2. Set the following variables in your `.env` or Render environment:
   ```text
   QDRANT_MODE=server
   QDRANT_HOST=https://your-cluster-id.cloud.qdrant.io:6333
   QDRANT_API_KEY=your_qdrant_api_key
   ```

---

## 🔧 Troubleshooting & FAQ

<details>
<summary><b>1. Error: Rate limit exceeded (Google Gemini 429)</b></summary>
<br>
The system has built-in 3-attempt exponential retries. If the Gemini API hits strict quota limits, the system will automatically fall back to your local Ollama instance (if running) or use the offline context synthesizer without throwing an unhandled exception.
</details>

<details>
<summary><b>2. How do I switch between Google Gemini and HuggingFace embeddings?</b></summary>
<br>
Update <code>EMBEDDING_PROVIDER</code> in your <code>.env</code> file:
<ul>
  <li><code>EMBEDDING_PROVIDER=huggingface</code>: Uses local <code>BAAI/bge-small-en-v1.5</code> (384 dimensions, zero API cost).</li>
  <li><code>EMBEDDING_PROVIDER=gemini</code>: Uses Google <code>gemini-embedding-001</code> (3,072 dimensions, high semantic fidelity).</li>
</ul>
<i>Note: When switching embedding models, re-index your documents or delete existing collections to match the new vector dimensionality.</i>
</details>

<details>
<summary><b>3. Do I need Firebase to run the system?</b></summary>
<br>
No. Firebase is completely optional (<code>FIREBASE_ENABLED=false</code> by default). When disabled, Qdrant handles all vector storage and metadata filtering locally on disk.
</details>

<details>
<summary><b>4. How to use Local Ollama offline?</b></summary>
<br>
Install Ollama from <a href="https://ollama.ai">ollama.ai</a>, pull the model (e.g. <code>ollama pull llama3</code>), and make sure the Ollama daemon is running at <code>http://localhost:11434</code>. The RAG pipeline will automatically detect and query Ollama when Gemini is unreachable.
</details>

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — feel free to use, modify, and distribute it for enterprise and personal applications.

---

<div align="center">
  <sub>Developed with ❤️ for scalable, grounded, and cost-efficient enterprise AI solutions.</sub>
</div>
