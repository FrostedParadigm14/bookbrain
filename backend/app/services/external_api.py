import requests
from typing import List, Dict, Any
from app.core.config import settings

class GoogleBooksService:
    BASE_URL = "https://www.googleapis.com/books/v1/volumes"
    
    @classmethod
    def search(cls, query: str, max_results: int = 3) -> str:
        """Search Google Books API and return formatted results"""
        try:
            params = {
                "q": query,
                "maxResults": max_results
            }
            # Check for API Key in settings
            api_key = settings.GOOGLE_BOOKS_API_KEY
            if not api_key and settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY.startswith("AIzaSy"):
                api_key = settings.GOOGLE_API_KEY
            if api_key:
                params["key"] = api_key
                
            response = requests.get(cls.BASE_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                return "No external information found on Google Books."
                
            results = []
            for item in items:
                info = item.get("volumeInfo", {})
                title = info.get("title", "Unknown Title")
                authors = ", ".join(info.get("authors", ["Unknown Author"]))
                description = info.get("description", "No description available.")
                
                results.append(f"Title: {title}\nAuthors: {authors}\nDescription: {description}")
                
            return "\n\n---\n\n".join(results)
        except Exception as e:
            return f"Error fetching from Google Books API: {str(e)}"

    @classmethod
    def fetch_cover_from_open_library(cls, title: str, author: str) -> Dict[str, Any]:
        """Search Open Library API for a book cover and metadata as a fallback."""
        try:
            # Clean title to strip subtitles (e.g. split by ':' or '-')
            search_title = title
            if ":" in search_title:
                search_title = search_title.split(":")[0]
            if " - " in search_title:
                search_title = search_title.split(" - ")[0]
            search_title = search_title.strip()

            print(f"[Open Library Fallback] Searching for '{search_title}' by '{author}'...")
            url = "https://openlibrary.org/search.json"
            params = {
                "title": search_title,
                "limit": 3
            }
            if author:
                params["author"] = author
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            docs = data.get("docs", [])
            if not docs:
                return {}
                
            def _extract_ol_metadata(doc) -> Dict[str, Any]:
                # Safe description extraction (prevents string-slicing first character if it's a string)
                first_sent = doc.get("first_sentence")
                if isinstance(first_sent, list) and first_sent:
                    desc = first_sent[0]
                elif isinstance(first_sent, str) and first_sent:
                    desc = first_sent
                else:
                    desc = "No description available via Open Library."
                    
                # Safe page count extraction
                pages = doc.get("number_of_pages_median") or doc.get("number_of_pages")
                if isinstance(pages, list) and pages:
                    pages = pages[0]
                try:
                    pages = int(pages) if pages is not None else None
                except:
                    pass
                    
                # Safe genre extraction
                genres = doc.get("subject", [])
                genre = genres[0] if genres else None
                
                return {
                    "description": desc,
                    "genre": genre,
                    "page_count": pages,
                    "title": doc.get("title", title),
                    "author": ", ".join(doc.get("author_name", [])) if doc.get("author_name") else author,
                }
                
            for doc in docs:
                cover_i = doc.get("cover_i")
                if cover_i:
                    cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"
                    meta = _extract_ol_metadata(doc)
                    
                    return {
                        "cover_url": cover_url,
                        "description": meta["description"],
                        "genre": meta["genre"],
                        "page_count": meta["page_count"],
                        "title": meta["title"],
                        "author": meta["author"],
                        "source": "Open Library API"
                    }
            
            # Fallback if no cover image is found in any doc
            meta = _extract_ol_metadata(docs[0])
            return {
                "cover_url": None,
                "description": meta["description"],
                "genre": meta["genre"],
                "page_count": meta["page_count"],
                "title": meta["title"],
                "author": meta["author"],
                "source": "Open Library API"
            }
        except Exception as e:
            print(f"Error searching Open Library: {e}")
            return {}

    @classmethod
    def find_cover_and_metadata(cls, title: str, author: str) -> Dict[str, Any]:
        """Search Google Books for cover and metadata, and pivot to Open Library if unavailable."""
        google_success = False
        result = {}
        
        try:
            # Clean title to strip subtitles (e.g. split by ':' or '-')
            search_title = title
            if ":" in search_title:
                search_title = search_title.split(":")[0]
            if " - " in search_title:
                search_title = search_title.split(" - ")[0]
            search_title = search_title.strip()

            # Check for GCP-format API key in settings
            api_key = settings.GOOGLE_BOOKS_API_KEY
            if not api_key and settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY.startswith("AIzaSy"):
                api_key = settings.GOOGLE_API_KEY
                
            query = f'intitle:"{search_title}" inauthor:"{author}"'
            params = {
                "q": query,
                "maxResults": 3
            }
            if api_key:
                params["key"] = api_key
                print("[Google Books API] Using configured API key for volume search.")
            else:
                print("[Google Books API] Using public access (no GCP key found/valid).")
                
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                # Try a broader search if the exact match fails
                query_broad = f"{search_title} {author}"
                params["q"] = query_broad
                response = requests.get(cls.BASE_URL, params=params, timeout=10)
                data = response.json()
                items = data.get("items", [])
                
            if items:
                # Find the first item that has imageLinks or has info
                for item in items:
                    info = item.get("volumeInfo", {})
                    image_links = info.get("imageLinks", {})
                    cover_url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
                    if cover_url:
                        # Upgrade http to https to avoid mixed-content issues in frontend
                        if cover_url.startswith("http://"):
                            cover_url = cover_url.replace("http://", "https://", 1)
                        
                        result = {
                            "cover_url": cover_url,
                            "description": info.get("description"),
                            "genre": info.get("categories", ["Unknown"])[0] if info.get("categories") else None,
                            "page_count": info.get("pageCount"),
                            "title": info.get("title"),
                            "author": ", ".join(info.get("authors", [])) if info.get("authors") else author,
                            "source": "Google Books API"
                        }
                        google_success = True
                        break
                        
                if not google_success:
                    # Fallback to metadata of first item (but no cover found)
                    first_info = items[0].get("volumeInfo", {})
                    result = {
                        "cover_url": None,
                        "description": first_info.get("description"),
                        "genre": first_info.get("categories", ["Unknown"])[0] if first_info.get("categories") else None,
                        "page_count": first_info.get("pageCount"),
                        "title": first_info.get("title"),
                        "author": ", ".join(first_info.get("authors", [])) if first_info.get("authors") else author,
                        "source": "Google Books API"
                    }
                    google_success = True
        except Exception as e:
            print(f"[Google Books API] Error encountered: {e}")
            
        # PIVOT IF FAILED OR NO COVER IMAGE FOUND
        if not google_success or not result.get("cover_url"):
            print("[Bookkeeper Service] Google Books cover was empty or API failed. Pivoting to Open Library API...")
            ol_result = cls.fetch_cover_from_open_library(title, author)
            
            # 1. If Open Library successfully found a cover, return it
            if ol_result and ol_result.get("cover_url"):
                return ol_result
                
            # 2. If Open Library did NOT find a cover, but Google Books succeeded in finding rich metadata,
            #    favor Google Books' metadata instead of Open Library's cover-less metadata.
            if google_success and result and result.get("description"):
                return result
                
            # 3. If Google Books failed completely, fallback to whatever Open Library returned (even if cover-less)
            if ol_result:
                return ol_result
                
        return result
