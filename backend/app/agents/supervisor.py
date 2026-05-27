from langchain_core.prompts import PromptTemplate
from app.core.llm_factory import LLMFactory
from app.agents.state import GraphState

class SupervisorAgent:
    def __init__(self):
        # We initialize dynamically in __call__ to support dynamic providers,
        # but compiling logic is here.
        self.prompt = PromptTemplate.from_template(
            """You are a routing supervisor. Your job is to decide whether to route the user's query about books to the local RAG agent (which searches through uploaded personal PDFs) or an external agent (which searches the Google Books API).
            
            If the query seems like it's asking about personal notes, specific uploaded books, or internal knowledge, route to 'rag'.
            If the query is asking for general information about a book, publishing details, broad summaries, or recommendations not specific to personal notes, route to 'external'.
            
            Query: {query}
            
            Format your response as a single word: either "rag" or "external".
            """
        )

    def route(self, state: GraphState) -> GraphState:
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
        if decision not in ["rag", "external"]:
            decision = "rag"
            
        print(f"[Supervisor] Routing query to: {decision}")
        
        return {
            "agent_path": ["Supervisor", decision.upper() + "_AGENT"],
        }
