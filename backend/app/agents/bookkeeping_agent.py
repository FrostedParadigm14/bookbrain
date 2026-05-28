from app.agents.state import GraphState
from app.services.external_api import GoogleBooksService
from app.core.config import settings
import sqlite3
import os
from typing import Dict, Any

class BookkeepingAgent:
    def __init__(self):
        pass

    def _get_db_path(self) -> str:
        index_dir = os.path.dirname(settings.FAISS_INDEX_PATH) or '.'
        return os.path.join(index_dir, 'books.sqlite')

    def _get_book_details_by_path(self, db_path: str, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(db_path):
            return {}
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, author, file_path, cover_url FROM books WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    def _find_book_by_title_in_query(self, db_path: str, query: str) -> Dict[str, Any]:
        if not os.path.exists(db_path):
            return {}
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, author, file_path, cover_url FROM books")
            rows = cursor.fetchall()
            query_lower = query.lower()
            for row in rows:
                title = row['title'].lower()
                if title and title in query_lower:
                    return dict(row)
            return {}
        finally:
            conn.close()

    def _update_book_cover(self, db_path: str, book_id: int, cover_url: str, genre: str = None, page_count: int = None, description: str = None) -> bool:
        if not os.path.exists(db_path):
            print(f"[Bookkeeping DB] DB file does not exist at: {db_path}")
            return False
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            print(f"[Bookkeeping DB] Preparing to update book ID: {book_id} with cover: '{cover_url}'")
            # Update cover URL
            cursor.execute("UPDATE books SET cover_url = ? WHERE id = ?", (cover_url, book_id))
            print(f"[Bookkeeping DB] Cover URL updated.")
            
            # Optionally update genre, page count, and description if they are empty
            if genre:
                cursor.execute("UPDATE books SET genre = ? WHERE id = ? AND (genre IS NULL OR genre = '')", (genre, book_id))
                print(f"[Bookkeeping DB] Genre updated.")
            if page_count:
                cursor.execute("UPDATE books SET page_count = ? WHERE id = ? AND (page_count IS NULL OR page_count = 0 OR page_count = '')", (page_count, book_id))
                print(f"[Bookkeeping DB] Page count updated.")
            if description:
                cursor.execute("UPDATE books SET description = ? WHERE id = ? AND (description IS NULL OR description = '')", (description, book_id))
                print(f"[Bookkeeping DB] Description updated.")
                
            conn.commit()
            print(f"[Bookkeeping DB] SQLite Transaction COMMITTED successfully.")
            return True
        except Exception as e:
            print(f"[Bookkeeping DB] Error updating SQLite cover: {e}")
            return False
        finally:
            conn.close()

    def process(self, state: GraphState) -> GraphState:
        print("[Bookkeeping Agent] Processing library update task...")
        
        db_path = self._get_db_path()
        query = state["query"]
        selected_books = state.get("selected_books", [])
        
        # 1. Determine target book
        book = {}
        if selected_books:
            print(f"[Bookkeeping Agent] Target from selected books list: {selected_books[0]}")
            book = self._get_book_details_by_path(db_path, selected_books[0])
            
        if not book:
            print("[Bookkeeping Agent] No selected books or not found. Attempting title extraction from query...")
            book = self._find_book_by_title_in_query(db_path, query)
            
        if not book:
            # Get list of all books in DB to suggest
            books_list = []
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT title FROM books LIMIT 5")
                books_list = [r[0] for r in cursor.fetchall()]
                conn.close()
                
            msg = "I couldn't identify which book you'd like me to find the cover for. Please select a book first, or mention its exact title in your message."
            if books_list:
                msg += f" Books in your library: {', '.join(books_list)}"
                
            return {
                "context": "No matching book found in library SQLite database.",
                "sources": [],
                "answer": msg
            }
            
        title = book.get("title", "Unknown Title")
        author = book.get("author", "Unknown Author")
        book_id = book.get("id")
        file_path = book.get("file_path")
        
        print(f"[Bookkeeping Agent] Found target book: '{title}' by {author} (ID: {book_id})")
        
        # 2. Query Google Books API
        metadata = GoogleBooksService.find_cover_and_metadata(title, author)
        
        if not metadata or not metadata.get("cover_url"):
            # Try searching with just title if author search was empty
            metadata = GoogleBooksService.find_cover_and_metadata(title, "")
            
        cover_url = metadata.get("cover_url")
        
        if not cover_url:
            return {
                "context": f"Google Books search results for '{title}' by {author}",
                "sources": [{"content": f"Failed to retrieve cover URL for {title}.", "metadata": {"source": "Google Books Service"}}],
                "answer": f"I searched Google Books for **{title}** by **{author}** but could not find a suitable cover image. You can try updating it manually in the Edit Metadata drawer."
            }
            
        # 3. Update SQLite database
        success = self._update_book_cover(
            db_path=db_path,
            book_id=book_id,
            cover_url=cover_url,
            genre=metadata.get("genre"),
            page_count=metadata.get("page_count"),
            description=metadata.get("description")
        )
        
        if not success:
            return {
                "context": f"Failed database update execution.",
                "sources": [],
                "answer": f"I found the cover for **{title}** on Google Books, but encountered a database error while attempting to update SQLite."
            }
            
        # Successful bookkeeping
        desc = metadata.get("description", "No description available.")
        genre = metadata.get("genre", "Unknown")
        pages = metadata.get("page_count", "Unknown")
        source_name = metadata.get("source", "Google Books API")
        
        context_str = f"Cover URL found: {cover_url}\nGenre: {genre}\nPages: {pages}\nDescription: {desc[:200]}..."
        sources = [{"content": context_str, "metadata": {"source": source_name, "title": title, "author": author}}]
        
        answer = f"✧ **Bookkeeper Agent Activated** ✧\n\n"
        answer += f"I have successfully found and updated the cover for your book:\n"
        answer += f"- **Book**: **{title}** by {author}\n"
        answer += f"- **Source**: {source_name}\n"
        answer += f"- **Genre**: {genre}\n"
        answer += f"- **Page Count**: {pages} pages\n"
        answer += f"- **Cover Image URL**: [View Image]({cover_url})\n\n"
        answer += f"I've updated the SQLite database with this cover and any missing metadata. **Please refresh your library page** to see the new cover image!"
        
        return {
            "context": context_str,
            "sources": sources,
            "answer": answer
        }
