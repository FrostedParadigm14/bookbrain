import os
from pymilvus import MilvusClient
from langchain_community.embeddings import HuggingFaceEmbeddings
import langchain_core.documents as lc_docs
from app.core.config import settings

class RetrievalService:
    _client = None
    _embeddings = None

    @classmethod
    def get_client(cls):
        """Returns the MilvusClient instance"""
        if cls._client is None:
            os.makedirs(os.path.dirname(settings.MILVUS_DB_PATH) or '.', exist_ok=True)
            cls._client = MilvusClient(settings.MILVUS_DB_PATH)
        return cls._client

    @classmethod
    def get_embeddings(cls):
        """Returns the embedding model"""
        if cls._embeddings is None:
            cls._embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return cls._embeddings

    @classmethod
    def retrieve(cls, query: str, k: int = 4, selected_books: list[str] = None):
        """Retrieves top k documents for a given query from Milvus Lite, with optional book filter"""
        client = cls.get_client()
        
        if not client.has_collection(settings.MILVUS_COLLECTION_NAME):
            print(f"[Retrieval] Collection '{settings.MILVUS_COLLECTION_NAME}' does not exist yet. Returning empty.")
            return []

        # Ensure collection is loaded
        client.load_collection(settings.MILVUS_COLLECTION_NAME)

        # Build filter expression if selected books are specified
        filter_expr = None
        if selected_books:
            # Pymilvus syntax: file_path in ["path1", "path2"]
            paths_str = ", ".join([f'"{p}"' for p in selected_books])
            filter_expr = f'file_path in [{paths_str}]'
            print(f"[Retrieval] Applying filter expression: {filter_expr}")

        print(f"[Retrieval] Embedding query: '{query}'...")
        query_vector = cls.get_embeddings().embed_query(query)
        
        print(f"[Retrieval] Searching Milvus Lite...")
        search_res = client.search(
            collection_name=settings.MILVUS_COLLECTION_NAME,
            data=[query_vector],
            filter=filter_expr,
            limit=k,
            output_fields=["text", "file_path", "page", "title", "author"]
        )

        hits = search_res[0] if search_res else []
        print(f"[Retrieval] Found {len(hits)} matching chunks.")

        docs = []
        for hit in hits:
            entity = hit.get("entity", {})
            docs.append(lc_docs.Document(
                page_content=entity.get("text", ""),
                metadata={
                    "source": entity.get("file_path", ""),
                    "page": entity.get("page", 0),
                    "title": entity.get("title", "Unknown Title"),
                    "author": entity.get("author", "Unknown Author"),
                    "score": hit.get("distance", 0.0)
                }
            ))
        return docs

