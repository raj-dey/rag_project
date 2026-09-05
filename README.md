<div align="center">

# ⚡ Enterprise Production RAG System

[![Live Demo](https://img.shields.io/badge/🚀%20Live%20Demo-Streamlit%20App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://ragproject-raj-dey.streamlit.app)
[![GitHub](https://img.shields.io/badge/GitHub-raj--dey%2Frag__project-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/raj-dey/rag_project)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-DC2626?style=for-the-badge&logo=qdrant&logoColor=white)](https://qdrant.tech)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)

An enterprise-grade Retrieval-Augmented Generation (RAG) platform featuring multi-format document ingestion, two-stage vector retrieval with BGE cross-encoder reranking, automated synonym mining, strict source citations, and real-time latency & cost analytics.

[Live Demo](#-live-demo) • [Features](#-key-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [Configuration](#-configuration) • [API](#-api-endpoints) • [Hosting](#-hosting--deployment)

---

</div>

## 🚀 Live Demo

| Service | Platform | Link | Status |
| :--- | :--- | :--- | :---: |
| **Frontend UI** | Streamlit Cloud | [👉 ragproject-raj-dey.streamlit.app](https://ragproject-raj-dey.streamlit.app) | ![Active](https://img.shields.io/badge/Status-Live-brightgreen?style=flat-square) |
| **Backend API** | Render | Configured via UI / Secrets | ![Active](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square) |

---

## ✨ Key Features

- **Multi-Format Ingestion**: Native parsing for **PDF**, **DOCX**, **Excel (XLSX/XLS)**, **CSV**, **TXT**, and **Markdown** with page, sheet, and section metadata preservation.
- **Two-Stage Retrieval & Reranking**: High-recall candidate search in **Qdrant** ($K=50$) paired with precision **BGE Cross-Encoder** reranking (`BAAI/bge-reranker-base`, $N=12$).
- **Dual Embeddings**: Supports **Google Gemini** (`gemini-embedding-001`, 3072-dim) and local **HuggingFace** (`BAAI/bge-small-en-v1.5`, 384-dim).
- **Domain Synonym Mining & Multi-Query**: Automated extraction of domain synonyms during upload and dynamic multi-query variant generation at search time for higher recall.
- **3-Tier Resilient Generation**: Primary generation with **Gemini 3.6 Flash** $\to$ fallback to **Local Ollama (Llama-3)** $\to$ fallback to **Offline Context Synthesizer**.
- **Source Attribution & Provenance**: Grounded responses with inline `[Source N]` tags showing file, page/sheet, and raw text snippets.
- **Cost & Latency Analytics**: Live tracking of search, rerank, and LLM latency alongside exact token usage and cost estimation in **USD ($)** and **INR (₹)**.
- **Admin Dashboard**: Password-protected portal for document ingestion, batch indexing, and cascading deletion across Qdrant, Firestore, and Storage.

---

## 🏗️ Architecture

```text
[ User Query ] ──► [ Synonym Expansion & Multi-Query ] ──► [ Embedding ]
                                                                 │
                                                                 ▼
[ Documents ] ──► [ Chunker ] ──► [ Vector Store ] ──► [ Top-50 Retrieval ]
                                                                 │
                                                                 ▼
                                                    [ BGE Cross-Encoder ]
                                                                 │
                                                                 ▼
                                                        [ Top-12 Chunks ]
                                                                 │
                                                                 ▼
[ Grounded Answer + Citations ] ◄── [ Gemini / Ollama / Offline LLM ]
```

---

## ⚡ Quick Start

### 1. Clone & Setup Environment

```bash
git clone https://github.com/raj-dey/rag_project.git
cd rag_project

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```dotenv
GEMINI_API_KEY=your_gemini_api_key_here
ADMIN_PASSWORD=your_admin_password
```

### 3. Run Backend (FastAPI)

```bash
PYTHONPATH=. uvicorn backend.main:app --reload --port 8000
```
- API Health: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Run Frontend (Streamlit)

In a separate terminal:
```bash
source venv/bin/activate
streamlit run frontend/app.py
```
- Web Dashboard: [http://localhost:8501](http://localhost:8501)

---

## ⚙️ Configuration

Key environment variables in `.env` (see `.env.example` for all options):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | *None* | Google Gemini API key for LLM and embeddings |
| `ADMIN_PASSWORD` | `admin123` | Password to unlock Admin Panel tab in Streamlit |
| `EMBEDDING_PROVIDER` | `huggingface` | `huggingface` (local BGE) or `gemini` (cloud 3072-dim) |
| `QDRANT_MODE` | `disk` | Vector database mode: `disk`, `memory`, or `server` |
| `QDRANT_PATH` | `./qdrant_storage` | Local directory for on-disk vector storage |
| `ENABLE_RERANKER` | `false` | Enable/disable BGE cross-encoder reranking stage |
| `OLLAMA_URL` | `http://localhost:11434`| Endpoint for local Ollama fallback |
| `FIREBASE_ENABLED` | `false` | Enable Firebase Firestore & Cloud Storage sync |

---

## 📡 API Endpoints

Interactive Swagger docs available at `/docs`.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/upload` | Uploads and indexes documents (`.pdf`, `.docx`, `.xlsx`, `.csv`, `.txt`, `.md`) |
| `POST` | `/api/query` | Executes RAG query pipeline (retrieval, rerank, generation, citations) |
| `GET` | `/api/documents` | Lists all indexed documents, chunk counts, and storage records |
| `DELETE` | `/api/documents/{filename}` | Cascades deletion of a document across vectors, metadata, and storage |
| `GET` | `/api/health` | Health check reporting vector store stats and active providers |

---

## 🚀 Hosting & Deployment

### Streamlit Community Cloud (Frontend)
1. Fork or push to GitHub (`raj-dey/rag_project`).
2. Go to [share.streamlit.io](https://share.streamlit.io/) $\to$ **New app**.
3. Set **Main file path**: `frontend/app.py`.
4. In **Settings** $\to$ **Secrets**, configure:
   ```toml
   API_URL = "https://your-backend.onrender.com"
   ADMIN_PASSWORD = "your_admin_password"
   ```

### Render (Backend API)
1. Create a new **Web Service** on [render.com](https://render.com/) linked to this repository.
2. **Build Command**: `pip install -r backend/requirements.txt`
3. **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. **Environment Variables**:
   - `PYTHONPATH` = `.`
   - `GEMINI_API_KEY` = `<your_key>`
   - `ADMIN_PASSWORD` = `<your_password>`
   - `QDRANT_MODE` = `disk`

---

## 📁 Repository Structure

```text
rag_project/
├── backend/
│   ├── api/             # FastAPI routes (/api/upload, /api/query, /api/documents)
│   ├── core/            # Parsers, chunking, embeddings, Qdrant, reranker, LLM, synonyms
│   ├── main.py          # FastAPI application entry point & CORS
│   └── requirements.txt # Backend dependencies
├── frontend/
│   ├── app.py           # Streamlit UI (Chat assistant & Admin panel)
│   └── requirements.txt # Frontend dependencies
├── qdrant_storage/      # On-disk persistent vector database
├── .env.example         # Environment variable template
├── requirements.txt     # Consolidated dependencies
└── README.md            # Project documentation
```

---

## 📄 License

Distributed under the [MIT License](LICENSE).
