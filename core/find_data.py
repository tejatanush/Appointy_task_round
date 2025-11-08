import os, requests, json, numpy as np # Make sure numpy is imported
from datetime import datetime, timezone
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from utils.config import load_environments
from bs4 import BeautifulSoup

# --- ENVIRONMENT CONFIG ---
mongodb_URL, mongodb, collection, collection2, OPENAI_API_KEY = load_environments()
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
client = AsyncIOMotorClient(mongodb_URL)
db = client[mongodb]
data_col = db["data"]

# --- 1️⃣ CLASSIFY USER QUERY TYPE ---
async def classify_query_type(query: str) -> str:
    try:
        prompt = f"""
**Role:** You are an expert zero-shot classifier.
**Task:** Classify the user's query into *one* of the following categories:
- `text` (Queries about notes, documents, or general text. e.g., "my note on system design")
- `image` (Queries about photos, pictures, or screenshots. e.g., "show me that photo of a whiteboard")
- `url` (Queries about websites, links, or articles. e.g., "find the article I saved on Python")
- `all` (Queries that are general, ambiguous, or mix multiple types. e.g., "find my stuff", "search everything")

**Rules:**
1.  Respond with *only* the single category name (`text`, `image`, `url`, `linkedin_job`, or `all`).
2.  Do not add explanations, punctuation, markdown, or any other text.
3.  If uncertain, always default to `all`.
**Query:** "{query}"
"""
        res = await ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5
        )
        qtype = res.choices[0].message.content.strip().lower()
        if qtype not in ["text", "image", "url", "all"]:
            qtype = "all"
        return qtype
    except Exception:
        return "all"

# --- 2️⃣ ADD THIS HELPER FUNCTION (THE FALLBACK) ---
async def _local_cosine_search(user_id: str, query_vector: list, mongo_filter: dict, limit: int = 5):
    """
    Performs a local, in-memory cosine similarity search.
    This is a fallback for when Atlas $vectorSearch is not available.
    """
    try:
        # 1. Fetch all candidate documents from local MongoDB
        #    You MUST project the 'embedding' field
        candidates_cursor = data_col.find(mongo_filter, {
            "embedding": 1, "_id": 0, "title": 1, "summary": 1,
            "tags": 1, "category": 1, "type": 1, "source_platform": 1,
            "media_url": 1, "created_at": 1
        })
        
        candidates = await candidates_cursor.to_list(length=None) # Fetch all
        
        if not candidates:
            return []

        # 2. Extract embeddings and calculate cosine similarity
        embeddings = np.array([doc['embedding'] for doc in candidates if 'embedding' in doc])
        query_vec = np.array(query_vector).reshape(1, -1)
        
        if embeddings.shape[0] == 0:
            return [] # No documents with embeddings found

        # Calculate norms
        query_norm = np.linalg.norm(query_vec)
        embed_norms = np.linalg.norm(embeddings, axis=1)
        
        # Avoid division by zero
        if query_norm == 0 or np.any(embed_norms == 0):
            print("⚠️ Local Search Warning: Zero-norm vector found.")
            return []

        # 3. Calculate scores
        # (embeddings @ query_vec.T) gives a (N, 1) matrix, .flatten() makes it (N,)
        scores = (embeddings @ query_vec.T).flatten() / (embed_norms * query_norm)
        
        # 4. Combine docs with scores, sort, and return
        scored_results = []
        for i, doc in enumerate(candidates):
            if 'embedding' in doc:
                doc['score'] = scores[i]
                del doc['embedding'] # Don't send the full vector back
                scored_results.append(doc)
            
        top_results = sorted(scored_results, key=lambda x: x['score'], reverse=True)
        return top_results[:limit]
        
    except Exception as e:
        print(f"🚨 Local cosine search *itself* failed: {e}")
        # Raise error from here to be caught by the main endpoint
        raise HTTPException(status_code=500, detail=f"Local cosine search failed: {e}")
async def vector_search(user_id: str, query_vector: list, query_type: str, limit: int = 5):
    """
    Performs a vector search. Tries Atlas $vectorSearch first,
    and falls back to local cosine similarity if it fails.
    """
    mongo_filter = {"user_id": user_id}
    if query_type != "all":
        mongo_filter["type"] = query_type

    try:
        results = await data_col.aggregate([
            {
                "$vectorSearch": {
                    "index": "vector_index", 
                    "queryVector": query_vector,
                    "path": "embedding",
                    "numCandidates": 100,
                    "limit": limit,
                    "filter": mongo_filter
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "title": 1, "summary": 1,
                    "type": 1, "source_platform": 1, "media_url": 1, "created_at": 1
                }
            }
        ]).to_list(length=limit)
        print("✅ Atlas vector search successful.")
        return results

    except Exception as e:
        print(f"⚠️ Atlas vector search failed: {e}. Falling back to local similarity.")
        return await _local_cosine_search(user_id, query_vector, mongo_filter, limit)