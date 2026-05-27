import os
import sqlite3
import json
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
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
        )
        self.llm = LLMFactory.get_llm()
        self._init_db()
        self._init_milvus()

    def _init_milvus(self):
        """Initialize local Milvus Lite collection"""
        os.makedirs(os.path.dirname(settings.MILVUS_DB_PATH) or '.', exist_ok=True)
        self.milvus_client = MilvusClient(settings.MILVUS_DB_PATH)
        
        # Check if collection exists and has the correct schema
        recreate = False
        if self.milvus_client.has_collection(settings.MILVUS_COLLECTION_NAME):
            try:
                desc = self.milvus_client.describe_collection(settings.MILVUS_COLLECTION_NAME)
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
                dimension=384,  # all-MiniLM-L6-v2 dimension
                id_type="string",
                max_length=65535,
            )


    def _init_db(self):
        """Initialize local SQLite DB to store book metadata for the UI"""
        os.makedirs(os.path.dirname(self.index_path) or '.', exist_ok=True)
        db_path = os.path.join(os.path.dirname(self.index_path), 'books.sqlite')
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                title TEXT,
                author TEXT,
                cover_url TEXT
            )
        ''')
        self.conn.commit()

    def _extract_metadata(self, first_chunk_text: str) -> dict:
        """Uses LLM to extract JSON metadata from the first few pages."""
        prompt = f"""
        Extract the book metadata from the following text (which is the beginning of a document):
        Return ONLY valid JSON with keys "title", "author",. If unknown, use "Unknown".
        
        Text:
        {first_chunk_text[:3000]}
        """
        try:
            response = self.llm.invoke(prompt)
            # Simple crude fallback parser (Ideally use structured output)
            content = response.content.strip()
            # If the LLM returned markdown code blocks, strip them
            if content.startswith("```json"):
                content = content[7:-3]
            return json.loads(content)
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            return {"title": "Unknown Document", "author": "Unknown Author"}

    def ingest_document(self, file_path: str):
        """Loads a PDF or EPUB, extracts metadata, chunks it, and adds to FAISS."""
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
            return
            
        print("Extracting metadata...")
        metadata = self._extract_metadata(docs[0].page_content)
        title = metadata.get("title", Path(file_path).stem)
        author = metadata.get("author", "Unknown")
        
        print(f"Storing metadata: {title} by {author}")
        # Insert or ignore into sqlite DB
        self.conn.execute(
            "INSERT OR IGNORE INTO books (file_path, title, author, cover_url) VALUES (?, ?, ?, ?)",
            (file_path, title, author, "") # Placeholder for cover_url
        )
        self.conn.commit()

        print("Splitting sentences...")
        chunks = self.text_splitter.split_documents(docs)
        
        print(f"Creating embeddings for {len(chunks)} chunks and storing in Milvus Lite...")
        texts = [chunk.page_content for chunk in chunks]
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
        return {"title": title, "author": author}
