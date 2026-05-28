from fastapi import APIRouter, File, UploadFile, HTTPException
import sqlite3
import os
import shutil
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional

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
    genre: Optional[str] = None
    readingStatus: Optional[str] = "unread"
    rating: Optional[int] = None
    notes: Optional[str] = None
    lastReadAt: Optional[str] = None
    pageCount: Optional[int] = None
    description: Optional[str] = None
    addedAt: Optional[str] = None

class BookUpdateRequest(BaseModel):
    genre: Optional[str] = None
    readingStatus: Optional[str] = None
    rating: Optional[int] = None
    notes: Optional[str] = None
    lastReadAt: Optional[str] = None
    pageCount: Optional[int] = None
    description: Optional[str] = None

class ChunkSchema(BaseModel):
    id: str
    text: str
    filePath: str
    page: int
    title: str
    author: str

class UniqueBookSchema(BaseModel):
    filePath: str
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
    uniqueBooks: List[UniqueBookSchema]

def _get_db_path() -> str:
    index_dir = os.path.dirname(settings.FAISS_INDEX_PATH) or '.'
    return os.path.join(index_dir, 'books.sqlite')

def _row_to_book(row: sqlite3.Row) -> BookResponse:
    # Handle the description field if it is present (safe migration / fallback)
    description = row['description'] if 'description' in row.keys() else None
    return BookResponse(
        id=row['id'],
        title=row['title'] or 'Unknown Title',
        author=row['author'] or 'Unknown Author',
        coverUrl=row['cover_url'] or '',
        filePath=row['file_path'] or '',
        genre=row['genre'],
        readingStatus=row['reading_status'] or 'unread',
        rating=row['rating'],
        notes=row['notes'],
        lastReadAt=row['last_read_at'],
        pageCount=row['page_count'],
        description=description,
        addedAt=row['added_at'],
    )

@router.get("/books", response_model=List[BookResponse])
def get_books():
    """Retrieve all books stored in the library."""
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        return []

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, author, cover_url, file_path, genre, reading_status, "
            "rating, notes, last_read_at, page_count, description, added_at FROM books"
        )
        return [_row_to_book(row) for row in cursor.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int):
    """Retrieve a single book's metadata by ID."""
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Library database not found.")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, author, cover_url, file_path, genre, reading_status, "
            "rating, notes, last_read_at, page_count, description, added_at FROM books WHERE id = ?",
            (book_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found.")
        return _row_to_book(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.patch("/books/{book_id}", response_model=BookResponse)
def update_book_metadata(book_id: int, update: BookUpdateRequest):
    """Update a book's user-defined metadata (genre, status, rating, notes, etc.)."""
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Library database not found.")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build dynamic update — only set provided fields
        fields = {
            "genre": update.genre,
            "reading_status": update.readingStatus,
            "rating": update.rating,
            "notes": update.notes,
            "last_read_at": update.lastReadAt,
            "page_count": update.pageCount,
            "description": update.description,
        }
        set_clauses = []
        values = []
        for col, val in fields.items():
            if val is not None:
                set_clauses.append(f"{col} = ?")
                values.append(val)
        
        if not set_clauses:
            raise HTTPException(status_code=400, detail="No fields provided to update.")
        
        values.append(book_id)
        cursor.execute(
            f"UPDATE books SET {', '.join(set_clauses)} WHERE id = ?",
            values
        )
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Book not found.")
        
        # Return the updated book
        cursor.execute(
            "SELECT id, title, author, cover_url, file_path, genre, reading_status, "
            "rating, notes, last_read_at, page_count, description, added_at FROM books WHERE id = ?",
            (book_id,)
        )
        return _row_to_book(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()



@router.delete("/books/{book_id}")
def delete_book(book_id: int):
    """Delete a book from SQLite, its vector chunks from Milvus, and the physical file from disk."""
    index_dir = os.path.dirname(settings.FAISS_INDEX_PATH) or '.'
    db_path = os.path.join(index_dir, 'books.sqlite')
    
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Library database not found.")

    conn = None
    file_path = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Fetch file_path from SQLite to identify the book
        cursor.execute("SELECT file_path, title FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found in database.")
        
        file_path = row[0]
        title = row[1]
        
        # 2. Delete from SQLite
        cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        print(f"[Library API] Deleted book '{title}' from SQLite metadata.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQLite deletion error: {str(e)}")
    finally:
        if conn:
            conn.close()

    # 3. Delete from Milvus Lite using file_path
    if file_path:
        try:
            client = MilvusClient(settings.MILVUS_DB_PATH)
            if client.has_collection(settings.MILVUS_COLLECTION_NAME):
                delete_filter = f'file_path == "{file_path}"'
                print(f"[Library API] Deleting Milvus entities with filter: {delete_filter}")
                client.delete(
                    collection_name=settings.MILVUS_COLLECTION_NAME,
                    filter=delete_filter
                )
                print(f"[Library API] Milvus deletion successful.")
        except Exception as e:
            print(f"[Library API] Warning: Failed to delete vector chunks from Milvus: {e}")

        # 4. Delete the physical file from disk
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"[Library API] Purged physical file: {file_path}")
        except Exception as e:
            print(f"[Library API] Warning: Failed to delete physical file: {e}")

    return {"message": "Book successfully deleted from SQLite, Milvus, and storage."}

@router.post("/upload")
async def upload_book(file: UploadFile = File(...)):
    """Upload a PDF or EPUB and ingest it into the RAG system."""
    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".epub"]:
        raise HTTPException(status_code=400, detail="Only PDF and EPUB files are supported.")
    
    # Save the file temporarily (or permanently into a data folder)
    upload_dir = os.path.join(os.getcwd(), "data", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Sanitize the filename to strip special/glob-magic characters like [] which crash pypandoc
    import re
    clean_stem = re.sub(r'[^a-zA-Z0-9._\s-]', '', Path(file.filename).stem)
    clean_stem = re.sub(r'\s+', ' ', clean_stem).strip()
    if not clean_stem:
        clean_stem = "uploaded_book_" + os.urandom(4).hex()
    safe_filename = clean_stem + ext
    temp_file_path = os.path.join(upload_dir, safe_filename)
    
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
def get_diagnostics(file_path: Optional[str] = None):
    """Retrieve Milvus vector database statistics and raw chunks.
    
    Optional query param:
      ?file_path=<path>  — filter chunks to a specific book only
    """
    try:
        client = MilvusClient(settings.MILVUS_DB_PATH)
        
        total_chunks = 0
        chunks = []
        unique_books = []
        vector_dimension = settings.EMBEDDING_DIMENSION
        
        if client.has_collection(settings.MILVUS_COLLECTION_NAME):
            client.load_collection(settings.MILVUS_COLLECTION_NAME)
            
            # Build filter expression
            book_filter = f'file_path == "{file_path}"' if file_path else ""
            
            # Total chunk count across the whole collection (unfiltered)
            count_res = client.query(
                collection_name=settings.MILVUS_COLLECTION_NAME,
                filter="",
                limit=10000,
                output_fields=["file_path", "title", "author"]
            )
            total_chunks = len(count_res)
            
            # Extract unique books directly from Milvus Lite
            unique_books_map = {}
            for r in count_res:
                fp = r.get("file_path")
                if fp and fp not in unique_books_map:
                    unique_books_map[fp] = {
                        "filePath": fp,
                        "title": r.get("title", os.path.basename(fp) if fp else "Unknown Title"),
                        "author": r.get("author", "Unknown Author")
                    }
            unique_books = [
                UniqueBookSchema(
                    filePath=fp,
                    title=info["title"],
                    author=info["author"]
                )
                for fp, info in unique_books_map.items()
            ]
            
            # Chunks to display — filtered by book if requested, all chunks returned
            results = client.query(
                collection_name=settings.MILVUS_COLLECTION_NAME,
                filter=book_filter,
                limit=10000,  # Return all chunks for the selected book
                output_fields=["id", "text", "file_path", "page", "title", "author"]
            )
            
            for r in results:
                chunks.append(ChunkSchema(
                    id=str(r.get("id", "")),
                    text=r.get("text", ""),
                    filePath=r.get("file_path", ""),
                    page=int(r.get("page", 0)),
                    title=r.get("title", "Unknown"),
                    author=r.get("author", "Unknown")
                ))
            
            # Sort chunks by page number
            chunks.sort(key=lambda c: c.page)
                
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
            embeddingModel=settings.EMBEDDING_MODEL_NAME,
            activeLlmProvider=settings.ACTIVE_PROVIDER,
            chunks=chunks,
            uniqueBooks=unique_books
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading database diagnostics: {str(e)}")


