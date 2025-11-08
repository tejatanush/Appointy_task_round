from fastapi import APIRouter, Depends, HTTPException, Query
from auth import JWTBearer
from core.add_data import generate_embedding 
import math
from core.find_data import vector_search,classify_query_type

search_router = APIRouter(prefix="/data", tags=["Search"])

@search_router.get("/search", dependencies=[Depends(JWTBearer())], summary="Semantic search across all user data")
async def semantic_search(
    query: str = Query(..., description="Your natural language search query."),
    token_payload: dict = Depends(JWTBearer()),
    limit: int = Query(5, description="Number of top results to return (default: 5)")
):
    """
    Perform semantic search over user's saved data (text, URL, images, etc.)
    using vector similarity search on precomputed embeddings.
    """
    try:
        user_id = token_payload.get("uid")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token or missing user ID.")
        vector_query=await generate_embedding(query)
        query_type=await classify_query_type(query)
        print(query_type)
        result=await vector_search(user_id,vector_query,query_type,limit)

        return {
            "query": query,
            "results_found": len(result),
            "results": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
