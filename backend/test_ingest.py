import sys
import os

# Add parent dir to path
sys.path.append(os.getcwd())

from app.services.ingestion import IngestionService

def main():
    service = IngestionService()
    epub_path = "data/uploads/Crouch Blake - Recursion_ A Novel 2019 Crown_Archetype - libgen.li.epub"
    if not os.path.exists(epub_path):
        print(f"Error: {epub_path} not found.")
        return
        
    print(f"Testing ingestion of {epub_path}...")
    result = service.ingest_document(epub_path)
    if result:
        print(f"\nSuccessfully ingested: {result['title']} by {result['author']}")
    else:
        print("\nIngestion failed.")

if __name__ == "__main__":
    main()
