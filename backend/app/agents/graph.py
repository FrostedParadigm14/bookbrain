from langgraph.graph import StateGraph, END
from app.agents.state import GraphState
from app.agents.supervisor import SupervisorAgent
from app.agents.rag_agent import RAGAgent
from app.agents.external_agent import ExternalAgent
from app.agents.evaluator import EvaluatorAgent

def create_workflow():
    workflow = StateGraph(GraphState)
    
    supervisor = SupervisorAgent()
    rag_agent = RAGAgent()
    external_agent = ExternalAgent()
    evaluator = EvaluatorAgent()
    
    # Define Nodes
    workflow.add_node("supervisor", supervisor.route)
    workflow.add_node("rag", rag_agent.process)
    workflow.add_node("external", external_agent.process)
    workflow.add_node("evaluator", evaluator.process)
    
    # Define Entry Point
    workflow.set_entry_point("supervisor")
    
    def route_condition(state: GraphState):
        path = state.get("agent_path", [])
        if "RAG_AGENT" in path:
            return "rag"
        elif "EXTERNAL_AGENT" in path:
            return "external"
        return "rag"  # Fallback
        
    workflow.add_conditional_edges("supervisor", route_condition, {
        "rag": "rag",
        "external": "external"
    })
    
    workflow.add_edge("rag", "evaluator")
    workflow.add_edge("external", "evaluator")
    workflow.add_edge("evaluator", END)
    
    return workflow.compile()

# Global graph instance
graph = create_workflow()
