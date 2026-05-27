from fastapi import APIRouter, Depends, HTTPException
from app.schemas.dtos import QueryRequest, QueryResponse
from app.agents.graph import graph

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    try:
        # Initialize graph state
        # The provider can be overridden in the request, otherwise uses default
        initial_state = {
            "query": request.query,
            "messages": [],
            "provider": request.provider,
            "agent_path": [],
            "selected_books": request.selected_books or []
        }
        
        # Run graph
        result = graph.invoke(initial_state)
        
        return QueryResponse(
            answer=result.get("answer", "No answer generated."),
            sources=result.get("sources", []),
            confidence_score=result.get("confidence_score", 0.0),
            hallucination_grade=result.get("hallucination_grade", "FAIL"),
            agent_path=result.get("agent_path", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
