from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "BookBrain Agentic RAG"
    API_V1_STR: str = "/api/v1"
    
    # LLM Settings
    ACTIVE_PROVIDER: str = "gemini" # 'gemini' or 'claude'
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # Retrieval
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    FAISS_INDEX_PATH: str = "data/faiss_index"
    MILVUS_DB_PATH: str = "data/milvus_books.db"
    MILVUS_COLLECTION_NAME: str = "book_chunks"
    
    # LangSmith Tracing
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "bookbrain-agentic-rag"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
