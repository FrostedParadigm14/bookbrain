from app.agents.state import GraphState
from app.core.llm_factory import LLMFactory
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel

class EvaluationResult(BaseModel):
    hallucination_grade: str
    confidence_score: float

class EvaluatorAgent:
    def __init__(self):
        self.prompt = PromptTemplate.from_template(
            """You are an evaluator agent. Your job is to assess the generated answer based on the provided context.
            
            Context: {context}
            
            Generated Answer: {answer}
            
            1. Hallucination Grade: Does the answer contain information NOT present in the context? (PASS if it's strictly based on context, FAIL if it hallucinates information).
            2. Confidence Score: A float between 0.0 and 1.0 indicating how well the answer addresses the user's query based on the context.
            
            Provide your response strictly in the following format:
            Grade: PASS|FAIL
            Score: 0.0-1.0
            """
        )

    def process(self, state: GraphState) -> GraphState:
        print("[Evaluator Agent] Assessing answer...")
        
        llm = LLMFactory.get_llm(state.get("provider"))
        chain = self.prompt | llm
        
        response = chain.invoke({
            "context": state["context"],
            "answer": state["answer"]
        })
        
        content = response.content.strip()
        
        # Parse the output
        grade = "FAIL"
        score = 0.5
        
        try:
            lines = content.split('\n')
            for line in lines:
                if line.startswith("Grade:"):
                    grade = line.split(":")[1].strip()
                if line.startswith("Score:"):
                    score = float(line.split(":")[1].strip())
        except Exception as e:
            print(f"Error parsing evaluator output: {e}")
            
        path = state.get("agent_path", [])
        path.append("Evaluator")
            
        return {
            "hallucination_grade": grade,
            "confidence_score": score,
            "agent_path": path
        }
