import requests
from typing import List, Dict, Any

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
