from fastapi import APIRouter, File, UploadFile, HTTPException
import sqlite3
import os
import shutil
from pathlib import Path
from pydantic import BaseModel
from typing import List

from app.services.ingestion import IngestionService
from app.core.config import settings
from pymilvus import MilvusClient

router = APIRouter()
ingestion_service = IngestionService()

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    coverUrl: str
    filePath: str

class ChunkSchema(BaseModel):
    id: str
    text: str
    filePath: str
    page: int
    title: str
    author: str

class DiagnosticsResponse(BaseModel):
    collectionName: str
    totalChunks: int
    dbFileSize: int
    vectorDimension: int
    embeddingModel: str
    activeLlmProvider: str
    chunks: List[ChunkSchema]

@router.get("/books", response_model=List[BookResponse])
def get_books():
    """Retrieve all books stored in the library."""
    index_dir = os.path.dirname(settings.FAISS_INDEX_PATH) or '.'
    db_path = os.path.join(index_dir, 'books.sqlite')
    
    if not os.path.exists(db_path):
        return []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, author, cover_url, file_path FROM books")
        rows = cursor.fetchall()
        
        books = []
        for row in rows:
            books.append(BookResponse(
                id=row['id'],
                title=row['title'] or 'Unknown Title',
                author=row['author'] or 'Unknown Author',
                coverUrl=row['cover_url'] or '',
                filePath=row['file_path'] or ''
            ))
        return books
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.post("/upload")
async def upload_book(file: UploadFile = File(...)):
    """Upload a PDF or EPUB and ingest it into the RAG system."""
    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".epub"]:
        raise HTTPException(status_code=400, detail="Only PDF and EPUB files are supported.")
    
    # Save the file temporarily (or permanently into a data folder)
    upload_dir = os.path.join(os.getcwd(), "data", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    temp_file_path = os.path.join(upload_dir, file.filename)
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Trigger ingestion and metadata extraction
        metadata = ingestion_service.ingest_document(temp_file_path)
        
        if not metadata:
            raise HTTPException(status_code=500, detail="Failed to parse document.")
            
        # Return the new book data for the UI
        return {
            "id": int(os.urandom(2).hex(), 16),
            "title": metadata.get("title", file.filename),
            "author": metadata.get("author", "Unknown Author"),
            "coverUrl": metadata.get("cover_url", ""),
            "filePath": temp_file_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading and parsing file: {str(e)}")

@router.get("/diagnostics", response_model=DiagnosticsResponse)
def get_diagnostics():
    """Retrieve Milvus vector database statistics and raw chunks."""
    try:
        client = MilvusClient(settings.MILVUS_DB_PATH)
        
        total_chunks = 0
        chunks = []
        vector_dimension = 384
        
        if client.has_collection(settings.MILVUS_COLLECTION_NAME):
            client.load_collection(settings.MILVUS_COLLECTION_NAME)
            # Query chunks
            results = client.query(
                collection_name=settings.MILVUS_COLLECTION_NAME,
                filter="",
                limit=100, # Display up to 100 raw chunks for live inspection
                output_fields=["id", "text", "file_path", "page", "title", "author"]
            )
            
            # Simple count query
            count_res = client.query(
                collection_name=settings.MILVUS_COLLECTION_NAME,
                filter="",
                limit=10000
            )
            total_chunks = len(count_res)
            
            for r in results:
                chunks.append(ChunkSchema(
                    id=str(r.get("id", "")),
                    text=r.get("text", ""),
                    filePath=r.get("file_path", ""),
                    page=int(r.get("page", 0)),
                    title=r.get("title", "Unknown"),
                    author=r.get("author", "Unknown")
                ))
                
        # DB Size
        db_size = 0
        if os.path.exists(settings.MILVUS_DB_PATH):
            if os.path.isdir(settings.MILVUS_DB_PATH):
                for dirpath, _, filenames in os.walk(settings.MILVUS_DB_PATH):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        db_size += os.path.getsize(fp)
            else:
                db_size = os.path.getsize(settings.MILVUS_DB_PATH)
                
        return DiagnosticsResponse(
            collectionName=settings.MILVUS_COLLECTION_NAME,
            totalChunks=total_chunks,
            dbFileSize=db_size,
            vectorDimension=vector_dimension,
            embeddingModel="all-MiniLM-L6-v2",
            activeLlmProvider=settings.ACTIVE_PROVIDER,
            chunks=chunks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading database diagnostics: {str(e)}")

