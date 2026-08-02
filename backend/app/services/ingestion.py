import os
import sqlite3
import json
from typing import Optional
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, UnstructuredEPubLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from pymilvus import MilvusClient
from app.core.config import settings
from app.core.llm_factory import LLMFactory
class IngestionService:
    def __init__(self, index_path: str = settings.FAISS_INDEX_PATH):
        self.index_path = index_path
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL_NAME,
            model_kwargs=settings.EMBEDDING_MODEL_KWARGS
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
        )
        self.llm = LLMFactory.get_llm()
        self._init_milvus()

    def _init_milvus(self):
        """Initialize local Milvus Lite collection"""
        os.makedirs(os.path.dirname(settings.MILVUS_DB_PATH) or '.', exist_ok=True)
        self.milvus_client = MilvusClient(settings.MILVUS_DB_PATH)
        
        # Check if collection exists and has the correct schema and dimension
        recreate = False
        if self.milvus_client.has_collection(settings.MILVUS_COLLECTION_NAME):
            try:
                desc = self.milvus_client.describe_collection(settings.MILVUS_COLLECTION_NAME)
                
                # Check vector dimension mismatch
                vector_field = next((f for f in desc.get('fields', []) if f.get('name') == 'vector'), None)
                if vector_field:
                    params = vector_field.get('params', {})
                    current_dim = params.get('dim') or params.get('dimension')
                    if current_dim and int(current_dim) != settings.EMBEDDING_DIMENSION:
                        print(f"Collection '{settings.MILVUS_COLLECTION_NAME}' has dimension {current_dim}, but {settings.EMBEDDING_DIMENSION} is required. Recreating collection...")
                        recreate = True

                # Find primary key field
                pk_field = next((f for f in desc.get('fields', []) if f.get('is_primary')), None)
                # DataType.VARCHAR is 21
                if pk_field and pk_field.get('type') != 21:
                    print(f"Collection '{settings.MILVUS_COLLECTION_NAME}' has primary key of type {pk_field.get('type')}, but string is required. Recreating collection...")
                    recreate = True
            except Exception as e:
                print(f"Error describing collection: {e}. Force recreating...")
                recreate = True
                
        if recreate:
            try:
                self.milvus_client.drop_collection(settings.MILVUS_COLLECTION_NAME)
            except Exception as e:
                print(f"Failed to drop collection: {e}")
                
        if recreate or not self.milvus_client.has_collection(settings.MILVUS_COLLECTION_NAME):
            self.milvus_client.create_collection(
                collection_name=settings.MILVUS_COLLECTION_NAME,
                dimension=settings.EMBEDDING_DIMENSION,
                id_type="string",
                max_length=65535,
            )
            self._init_db(clear=True)
        else:
            self._init_db(clear=False)

    def _init_db(self, clear: bool = False):
        """Initialize local SQLite DB to store book metadata for the UI"""
        os.makedirs(os.path.dirname(self.index_path) or '.', exist_ok=True)
        db_path = os.path.join(os.path.dirname(self.index_path), 'books.sqlite')
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        if clear:
            print("Resetting SQLite books metadata table...")
            self.conn.execute('DROP TABLE IF EXISTS books')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                title TEXT,
                author TEXT,
                cover_url TEXT,
                genre TEXT,
                reading_status TEXT DEFAULT 'unread',
                rating INTEGER,
                notes TEXT,
                last_read_at TEXT,
                page_count INTEGER,
                description TEXT,
                added_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        # Safe migration: add new columns to existing tables
        # Note: SQLite ALTER TABLE only allows constant defaults (not expressions like datetime('now'))
        existing_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(books)")}
        new_cols = {
            "genre": "TEXT",
            "reading_status": "TEXT DEFAULT 'unread'",
            "rating": "INTEGER",
            "notes": "TEXT",
            "last_read_at": "TEXT",
            "page_count": "INTEGER",
            "description": "TEXT",
            "added_at": "TEXT",  # populated at insert time by application
        }
        for col, col_type in new_cols.items():
            if col not in existing_cols:
                self.conn.execute(f"ALTER TABLE books ADD COLUMN {col} {col_type}")
                print(f"[DB Migration] Added column '{col}' to books table.")
        self.conn.commit()

    def _extract_embedded_cover(self, file_path: str) -> Optional[str]:
        """Extracts the cover image directly embedded in an EPUB or PDF file and saves to data/covers/."""
        try:
            covers_dir = os.path.join(os.getcwd(), "data", "covers")
            os.makedirs(covers_dir, exist_ok=True)
            stem = Path(file_path).stem
            ext = Path(file_path).suffix.lower()

            if ext == '.epub':
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as z:
                    file_list = z.namelist()
                    # 1. Look for images with 'cover' in filename
                    image_files = [f for f in file_list if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                    cover_candidates = [f for f in image_files if 'cover' in f.lower()]
                    
                    target_file = cover_candidates[0] if cover_candidates else (image_files[0] if image_files else None)
                    if target_file:
                        img_bytes = z.read(target_file)
                        img_ext = Path(target_file).suffix.lower() or ".jpg"
                        out_name = f"cover_{stem}_{os.urandom(4).hex()}{img_ext}"
                        out_path = os.path.join(covers_dir, out_name)
                        with open(out_path, 'wb') as f:
                            f.write(img_bytes)
                        print(f"[Cover Extractor] Extracted embedded EPUB cover image: {out_path}")
                        return f"http://127.0.0.1:8000/static/covers/{out_name}"

            elif ext == '.pdf':
                try:
                    import pypdf
                    reader = pypdf.PdfReader(file_path)
                    if reader.pages:
                        page = reader.pages[0]
                        for count, image_file_object in enumerate(page.images):
                            img_bytes = image_file_object.data
                            img_ext = Path(image_file_object.name).suffix.lower() or ".jpg"
                            out_name = f"cover_{stem}_{os.urandom(4).hex()}{img_ext}"
                            out_path = os.path.join(covers_dir, out_name)
                            with open(out_path, 'wb') as f:
                                f.write(img_bytes)
                            print(f"[Cover Extractor] Extracted embedded PDF page 1 image: {out_path}")
                            return f"http://127.0.0.1:8000/static/covers/{out_name}"
                except Exception as pe:
                    print(f"[Cover Extractor] PDF image extraction info: {pe}")

        except Exception as e:
            print(f"[Cover Extractor] Error extracting embedded cover: {e}")

        return None

    def _extract_metadata(self, sample_text: str) -> dict:
        """Uses LLM to extract JSON metadata from the first few pages of text, then enriches via Google Books & Open Library."""
        prompt = f"""
        You are an expert librarian AI. Analyze the following opening text from a book or document and extract metadata:
        Return ONLY valid JSON with keys:
        - "title": Title of the book (string)
        - "author": Author name(s) (string)
        - "genre": Primary genre or topic (string)
        - "description": A concise 2-3 sentence summary of what this book is about based on the text.
        - "search_query": Keywords to search Google Books for official metadata (string)

        If a specific field cannot be determined, use your best estimation or "Unknown".

        Opening Text:
        {sample_text[:4500]}
        """
        extracted = {"title": "Unknown Document", "author": "Unknown Author", "genre": "Non-Fiction", "description": ""}
        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            extracted = json.loads(content)
        except Exception as e:
            print(f"[Ingestion] Error extracting AI metadata from text: {e}")

        # Enrich using Google Books / Open Library API searching
        title = extracted.get("title") or "Unknown Document"
        author = extracted.get("author") or "Unknown Author"

        try:
            from app.services.external_api import GoogleBooksService
            ext_meta = GoogleBooksService.find_cover_and_metadata(title, author)
            if ext_meta:
                if ext_meta.get("cover_url"):
                    extracted["google_cover_url"] = ext_meta["cover_url"]
                if ext_meta.get("description"):
                    extracted["description"] = ext_meta["description"]
                if ext_meta.get("genre") and ext_meta["genre"] != "Unknown":
                    extracted["genre"] = ext_meta["genre"]
                if ext_meta.get("page_count"):
                    extracted["page_count"] = ext_meta["page_count"]
                if ext_meta.get("title") and title.lower() in ["unknown", "unknown document"]:
                    extracted["title"] = ext_meta["title"]
                if ext_meta.get("author") and author.lower() in ["unknown", "unknown author"]:
                    extracted["author"] = ext_meta["author"]
        except Exception as e:
            print(f"[Ingestion] Error enriching metadata via external APIs: {e}")

        return extracted

    def ingest_document(self, file_path: str):
        """Loads a PDF or EPUB, extracts AI metadata, enriches details, chunks text, and stores vectors in Milvus Lite."""
        print(f"Loading Document from {file_path}...")
        
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            loader = PyPDFLoader(file_path)
        elif ext == '.epub':
            try:
                loader = UnstructuredEPubLoader(file_path)
            except ImportError:
                print("unstructured library required for EPUB. Run: pip install unstructured")
                return None
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        docs = loader.load()
        if not docs:
            print("No content found.")
            return None

        # 1. Try to extract embedded cover directly from file (page 1 / zip cover)
        embedded_cover = self._extract_embedded_cover(file_path)

        print("Extracting AI metadata & fetching external book details from first pages...")
        sample_text = "\n\n".join([doc.page_content for doc in docs[:5]])
        metadata = self._extract_metadata(sample_text)
        
        title = metadata.get("title") or Path(file_path).stem
        author = metadata.get("author") or "Unknown Author"
        # Prioritize embedded cover image from file itself; fallback to Google Books API cover if unavailable
        cover_url = embedded_cover or metadata.get("google_cover_url") or metadata.get("cover_url", "")
        genre = metadata.get("genre", "General")
        description = metadata.get("description", "")
        page_count = metadata.get("page_count", len(docs))
        
        print(f"Storing metadata: '{title}' by '{author}' (Cover: {'Embedded' if embedded_cover else ('Google Books' if cover_url else 'None')})")
        
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM books WHERE file_path = ?", (file_path,))
        existing = cursor.fetchone()
        if existing:
            self.conn.execute(
                "UPDATE books SET title = ?, author = ?, cover_url = ?, genre = ?, description = ?, page_count = ? WHERE file_path = ?",
                (title, author, cover_url, genre, description, page_count, file_path)
            )
        else:
            self.conn.execute(
                "INSERT INTO books (file_path, title, author, cover_url, genre, description, page_count, added_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (file_path, title, author, cover_url, genre, description, page_count, now_utc)
            )
        self.conn.commit()

        print("Splitting sentences...")
        chunks = self.text_splitter.split_documents(docs)
        
        print(f"Creating embeddings for {len(chunks)} chunks and storing in Milvus Lite...")
        texts = [f"{settings.EMBEDDING_DOC_PREFIX}{chunk.page_content}" for chunk in chunks]
        embeddings_list = self.embeddings.embed_documents(texts)
        
        data = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings_list)):
            data.append({
                "id": f"{Path(file_path).stem}_{idx}_{os.urandom(4).hex()}",
                "vector": embedding,
                "text": chunk.page_content,
                "file_path": file_path,
                "page": chunk.metadata.get("page", 0),
                "title": title,
                "author": author
            })
            
        self.milvus_client.insert(
            collection_name=settings.MILVUS_COLLECTION_NAME,
            data=data
        )
            
        print("Ingestion complete.")
        return {
            "title": title,
            "author": author,
            "cover_url": cover_url,
            "genre": genre,
            "description": description,
            "page_count": page_count
        }
