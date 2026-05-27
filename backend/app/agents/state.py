from typing import TypedDict, Annotated, Sequence, List
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class GraphState(TypedDict):
    """The state of the graph."""
    query: str
    messages: Annotated[Sequence[BaseMessage], operator.add]
    agent_path: List[str]
    context: str
    sources: List[dict]
    answer: str
    confidence_score: float
    hallucination_grade: str
    provider: str
    selected_books: List[str]
