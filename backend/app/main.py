import os
# Fix duplicate OpenMP runtime error on macOS
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.exceptions import RAGException, rag_exception_handler
from app.api.routers import query, library

# Propagate LangSmith settings to environment variables for LangChain discovery
if settings.LANGCHAIN_TRACING_V2.lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT

def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # In production, restrict this to frontend URL
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    app.add_exception_handler(RAGException, rag_exception_handler)

    # Routers
    app.include_router(query.router, prefix=settings.API_V1_STR, tags=["Query"])
    app.include_router(library.router, prefix=settings.API_V1_STR, tags=["Library"])

    return app

app = create_app()

@app.get("/health")
def health_check():
    return {"status": "ok"}
