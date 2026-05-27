# BookBrain Agentic RAG

A multi-agent Retrieval-Augmented Generation (RAG) system that uses LangGraph to route queries between a local knowledge base and the external Google Books API, complete with LLM-agnostic support (Gemini & Claude).

## 🚀 Features

- **Multi-Agent Routing**: A Supervisor Agent routes queries to either external search or the local RAG system.
- **Milvus Lite Vector Store**: Local, light-weight vector database (`milvus-lite` and `pymilvus`) for fast similarity searches over embedded book chunks.
- **SQLite Metadata DB**: Local SQL DB to cache book metadata (title, author, cover) to supply structured info to the user interface.
- **LangSmith Tracing**: Deep observability and tracing support to debug agent decision logic, routing, and LLM calls.
- **External API Search**: Direct Google Books API integration for queries fallback.
- **Evaluator Validation**: Evaluation agent that validates retrieval relevance to ensure hallucination-free matching.
- **LLM Abstraction**: Factory pattern for easy switching between Gemini (Google GenAI) and Claude (AWS Bedrock).
- **FastAPI Backend**: Extensible and typed API layer.
- **Next.js/React Frontend**: Polished full-stack user interface.

---

## 🛠️ Getting Started

### 1. Prerequisites
- **Python**: `3.11` to `3.14`
- **Node.js**: `18+` (with `pnpm` or `npm`)

### 2. Environment Variables

Create and configure your environment variables for both backend and frontend layers.

#### Backend Configuration
Copy `.env.example` to `.env` inside the `backend` folder and populate your keys:
```bash
cp backend/.env.example backend/.env
```

Ensure your `.env` contains:
```env
# General Settings
PROJECT_NAME="BookBrain Agentic RAG"
API_V1_STR="/api/v1"

# LLM Providers (Active: 'gemini' or 'claude')
ACTIVE_PROVIDER="gemini"

# Google Gemini API Config
GOOGLE_API_KEY="your-gemini-api-key"
GEMINI_API_KEY="your-gemini-api-key"

# AWS Bedrock Config (If ACTIVE_PROVIDER="claude")
AWS_ACCESS_KEY_ID="your-aws-access-key"
AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
AWS_REGION="us-east-1"

# Milvus Database Settings (Milvus Lite)
MILVUS_DB_PATH="data/milvus_books.db"
MILVUS_COLLECTION_NAME="book_chunks"

# LangSmith Tracing & Observability
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_API_KEY="your-langsmith-api-key"
LANGCHAIN_PROJECT="bookbrain-agentic-rag"
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
```

---

### 3. Backend Setup

Setting up the FastAPI server inside a Python virtual environment:

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies (includes pymilvus, milvus-lite, langsmith, etc.)
pip install -r requirements.txt

# Run the FastAPI server with hot-reloading
uvicorn app.main:app --reload
```

The backend server will be running at `http://127.0.0.1:8000`. You can access the API documentation at `http://127.0.0.1:8000/docs`.

---

### 4. Frontend Setup

Install UI dependencies and run the development server:

```bash
# Navigate to the frontend directory
cd ../frontend

# Install dependencies using pnpm (or npm)
pnpm install

# Run the frontend server in development mode
pnpm dev
```

The frontend will be running at `http://localhost:3000`.

---

### 5. Document Ingestion

To ingest a new document (PDF or EPUB), index it into **Milvus Lite**, and automatically extract metadata (like title and author) using the LLM:

Start a python session in your activated backend environment or write a simple script:

```python
from app.services.ingestion import IngestionService

# Instantiate the service
service = IngestionService()

# Ingest an EPUB or PDF document
# This chunks the document, embeds it with HuggingFace,
# extracts metadata via LLM, and inserts it into Milvus Lite.
result = service.ingest_document("path/to/your/book.pdf")
print(f"Successfully ingested: {result['title']} by {result['author']}")
```

---

## 📈 Observability & Debugging

With **LangSmith Tracing** enabled in your `.env` file, all LLM prompts, LangGraph routing steps, retrieval logs, and agent tool usages will automatically be logged to your LangSmith dashboard. This is extremely helpful to debug:
- How the Supervisor agent decides to route the query.
- What content is retrieved from Milvus Lite.
- How the Evaluator agent decides if the retrieved information is relevant.

---

## 🐳 Deployment

Dockerfiles are provided in both `backend` and `frontend`.
- **Backend**: Can be deployed on Render, Fly.io, or AWS ECS using the provided `Dockerfile`.
- **Frontend**: Seamlessly deployable on Vercel or Netlify, or self-hosted via Next.js standalone outputs.

