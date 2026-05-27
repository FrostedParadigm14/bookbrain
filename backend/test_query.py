import sys
import os

# Fix duplicate OpenMP runtime error on macOS
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Add parent dir to path
sys.path.append(os.getcwd())

from app.agents.graph import graph

def run_test(query, selected_books=[]):
    print(f"\n=========================================")
    print(f"Testing LangGraph workflow with query: '{query}'")
    if selected_books:
        print(f"Selected books: {selected_books}")
    print(f"=========================================")
    
    initial_state = {
        "query": query,
        "messages": [],
        "provider": "gemini",
        "agent_path": [],
        "selected_books": selected_books
    }
    
    try:
        result = graph.invoke(initial_state)
        print("\n--- QUERY RESULT ---")
        print(f"Answer: {result.get('answer')}")
        print("\n--- METADATA & OBSERVABILITY ---")
        print(f"Agent Path: {' -> '.join(result.get('agent_path', []))}")
        print(f"Hallucination Grade: {result.get('hallucination_grade')}")
        print(f"Confidence Score: {result.get('confidence_score')}")
        
        sources = result.get('sources', [])
        print(f"\nSources retrieved: {len(sources)}")
        for idx, src in enumerate(sources):
            meta = src.get('metadata', {})
            print(f"  [{idx + 1}] Source: {os.path.basename(meta.get('source', 'Unknown'))}, Page: {meta.get('page', 0)}, Distance Score: {meta.get('score', 0.0):.4f}")
    except Exception as e:
        print(f"Error during query execution: {e}")

def main():
    # Only run Test 2: Local RAG Query (Forced to RAG by specifying the book path) to avoid exceeding Gemini minute rate limits
    book_path = "data/uploads/Crouch, Blake - Recursion_ A Novel (2019, Crown_Archetype) - libgen.li.epub"
    run_test("What is False Memory Syndrome?", selected_books=[book_path])

if __name__ == "__main__":
    main()
