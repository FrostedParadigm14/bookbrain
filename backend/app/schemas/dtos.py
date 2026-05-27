from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class QueryRequest(BaseModel):
    query: str
    provider: Optional[str] = None
    selected_books: Optional[List[str]] = None

class SourceDoc(BaseModel):
    content: str
    metadata: Dict[str, Any]

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceDoc]
    confidence_score: float
    hallucination_grade: str
    agent_path: List[str]
