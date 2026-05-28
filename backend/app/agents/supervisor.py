from langchain_core.prompts import PromptTemplate
from app.core.llm_factory import LLMFactory
from app.agents.state import GraphState

class SupervisorAgent:
    def __init__(self):
        # We initialize dynamically in __call__ to support dynamic providers,
        # but compiling logic is here.
        self.prompt = PromptTemplate.from_template(
            """You are a routing supervisor. Your job is to decide whether to route the user's query about books to:
            1. 'rag': For queries asking about personal notes, specific uploaded books, or searching the contents of their uploaded PDFs/EPUBs.
            2. 'external': For general literature questions, suggestions, broad publishing details, or book recommendations not related to their specific personal library.
            3. 'bookkeeping': For requests to manage, update, or edit book records (like fetching cover images, updating metadata, or executing bookkeeping tasks).
            
            Query: {query}
            
            Format your response as a single word: either "rag", "external", or "bookkeeping".
            """
        )

    def route(self, state: GraphState) -> GraphState:
        # Check if this is a cover/bookkeeping request first for extreme robustness
        query_lower = state["query"].lower()
        if any(kw in query_lower for kw in ["cover", "cover image", "find cover", "update cover", "fetch cover", "bookkeeper", "bookkeeping", "update db", "update database"]):
            print("[Supervisor] Detected bookkeeping request keyword. Routing directly to BOOKKEEPING.")
            return {
                "agent_path": ["Supervisor", "BOOKKEEPING_AGENT"],
            }

        # If user explicitly selected books, force RAG routing
        if state.get("selected_books"):
            print("[Supervisor] Selected books provided. Routing directly to RAG.")
            return {
                "agent_path": ["Supervisor", "RAG_AGENT"],
            }

        llm = LLMFactory.get_llm(state.get("provider"))
        chain = self.prompt | llm
        
        response = chain.invoke({"query": state["query"]})
        decision = response.content.strip().lower()
        
        # Default to RAG if parsing fails
        if decision not in ["rag", "external", "bookkeeping"]:
            decision = "rag"
            
        print(f"[Supervisor] Routing query to: {decision}")
        
        return {
            "agent_path": ["Supervisor", decision.upper() + "_AGENT"],
        }
