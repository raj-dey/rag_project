# Production RAG System with FastAPI, Qdrant & BGE Reranker

End-to-End Retrieval-Augmented Generation (RAG) system with a FastAPI backend, Qdrant vector database, BGE Cross-Encoder reranker, multi-format document parser, and interactive Streamlit UI.

---

## 🏗️ Core Features & Architecture

1. **Multi-Format Ingestion**: Supports PDF (PyMuPDF), DOCX (python-docx), Excel/CSV (Pandas/openpyxl), TXT, and Markdown files.
2. **Intelligent Chunking**: LangChain RecursiveCharacterTextSplitter with configurable chunk size (500–1000 tokens) and overlap.
3. **Dense Embeddings**: Local HuggingFace BGE embeddings (`BAAI/bge-small-en-v1.5`) or OpenAI (`text-embedding-3-small`).
4. **Vector Database**: Qdrant Vector Store with Cosine similarity search and metadata filtering.
5. **Cross-Encoder Reranking**: BGE Reranker (`BAAI/bge-reranker-small`) scoring query-chunk pairs with Sigmoid score normalization and relevance threshold filtering.
6. **Grounded LLM Answers & Citations**: OpenAI GPT generation (or fallback synthesizer) producing grounded answers with explicit source citations `[Source N]` (filename, page number, sheet name).
7. **Streamlit UI**: Dashboard with drag-and-drop document upload, live vector store stats, interactive chat, and latency benchmarks (search ms, rerank ms, llm ms, total ms).

---

## ⚡ Quick Start

### 1. Set Up Virtual Environment

```bash
cd rag_project
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

### 3. Run FastAPI Backend

```bash
# From rag_project root directory:
PYTHONPATH=. uvicorn backend.main:app --reload --port 8000
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Endpoint: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 4. Run Streamlit Frontend

Open a new terminal window:

```bash
cd rag_project
source venv/bin/activate
streamlit run frontend/app.py
```
- Streamlit Web App: [http://localhost:8501](http://localhost:8501)

---

## 📁 Directory Structure

```text
rag_project/
├── backend/
│   ├── main.py                # FastAPI entry point & CORS configuration
│   ├── api/
│   │   ├── upload.py          # /api/upload and /api/documents routes
│   │   └── query.py           # /api/query RAG pipeline route
│   ├── core/
│   │   ├── config.py          # Settings and environment variables
│   │   ├── document_parser.py # PDF, DOCX, XLSX, CSV, TXT extraction
│   │   ├── chunking.py        # LangChain text splitter & metadata
│   │   ├── embeddings.py      # BGE & OpenAI embedding models
│   │   ├── qdrant_client.py   # Qdrant client & vector operations
│   │   ├── reranker.py        # BGE Cross-Encoder reranker
│   │   └── llm.py             # Prompt builder & GPT citation engine
│   └── requirements.txt       # Backend dependencies
├── frontend/
│   ├── app.py                 # Streamlit UI dashboard
│   └── requirements.txt       # Frontend dependencies
├── .env.example               # Configuration template
└── README.md                  # Project documentation
```
