from app.agents.state import GraphState
from app.services.retrieval import RetrievalService
from app.core.llm_factory import LLMFactory
from langchain_core.prompts import PromptTemplate

class RAGAgent:
    def __init__(self):
        self.prompt = PromptTemplate.from_template(
            """You are a helpful assistant reading personal PDF books and notes. 
            Use the following pieces of retrieved context to answer the question. 
            If you don't know the answer, just say that you don't know based on the provided context.
            
            Context: {context}
            
            Question: {question}
            
            Answer:"""
        )

    def process(self, state: GraphState) -> GraphState:
        print("[RAG Agent] Retrieving context from Milvus Lite...")
        
        docs = RetrievalService.retrieve(state["query"], selected_books=state.get("selected_books"))
        context = "\n\n".join([doc.page_content for doc in docs])
        
        sources = [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]
        
        llm = LLMFactory.get_llm(state.get("provider"))
        chain = self.prompt | llm
        
        print("[RAG Agent] Generating answer...")
        response = chain.invoke({"context": context, "question": state["query"]})
        
        return {
            "context": context,
            "sources": sources,
            "answer": response.content
        }
