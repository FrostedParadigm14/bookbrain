from app.agents.state import GraphState
from app.services.external_api import GoogleBooksService
from app.core.llm_factory import LLMFactory
from langchain_core.prompts import PromptTemplate

class ExternalAgent:
    def __init__(self):
        self.prompt = PromptTemplate.from_template(
            """You are a knowledgeable literature assistant. 
            Use the following context from the Google Books API to answer the user's question.
            
            API Data: {context}
            
            Question: {question}
            
            Answer:"""
        )

    def process(self, state: GraphState) -> GraphState:
        print("[External Agent] Fetching data from Google Books API...")
        
        context = GoogleBooksService.search(state["query"])
        
        sources = [{"content": context, "metadata": {"source": "Google Books API"}}]
        
        llm = LLMFactory.get_llm(state.get("provider"))
        chain = self.prompt | llm
        
        print("[External Agent] Generating answer...")
        response = chain.invoke({"context": context, "question": state["query"]})
        
        return {
            "context": context,
            "sources": sources,
            "answer": response.content
        }
