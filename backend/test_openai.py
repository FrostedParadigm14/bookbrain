import sys
import os

# Fix duplicate OpenMP runtime error on macOS
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Add parent dir to path
sys.path.append(os.getcwd())

from app.core.config import settings
from app.agents.graph import graph

def run_test(query, selected_books=[]):
    print(f"\n=========================================")
    print(f"Testing LangGraph workflow with OpenAI and query: '{query}'")
    if selected_books:
        print(f"Selected books: {selected_books}")
    print(f"=========================================")
    
    # We specify "openai" as the provider explicitly
    initial_state = {
        "query": query,
        "messages": [],
        "provider": "openai",
        "agent_path": [],
        "selected_books": selected_books
    }
    
    try:
        result = graph.invoke(initial_state)
        print("\n--- QUERY RESULT ---")
        print(f"Answer: {result.get('answer')}")
        print("\n--- METADATA & OBSERVABILITY ---")
        print(f"Agent Path: {' -> '.join(result.get('agent_path', []))}")
        print(f"Hallucination Shield Grade: {result.get('hallucination_grade')}")
        print(f"Confidence Score: {result.get('confidence_score')}")
        
        sources = result.get('sources', [])
        print(f"\nSources retrieved: {len(sources)}")
        for idx, src in enumerate(sources):
            meta = src.get('metadata', {})
            print(f"  [{idx + 1}] Source: {os.path.basename(meta.get('source', 'Unknown'))}, Page: {meta.get('page', 0)}, Distance Score: {meta.get('score', 0.0):.4f}")
    except Exception as e:
        print(f"Error during query execution: {e}")

def main():
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-openai-api-key":
        print("\n[!] Please configure your OPENAI_API_KEY in backend/.env to run this test!")
        return

    # Run Test: Local RAG Query (Forced to RAG by specifying the book path) using OpenAI's gpt-4o-mini
    book_path = "data/uploads/Crouch, Blake - Recursion_ A Novel (2019, Crown_Archetype) - libgen.li.epub"
    run_test("What is False Memory Syndrome in the story?", selected_books=[book_path])

if __name__ == "__main__":
    main()
