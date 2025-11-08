import os, re, requests
from datetime import datetime, timezone
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from PIL import Image
import io
import json
import newspaper
from openai import AsyncOpenAI
from utils.config import load_environments,get_scraper
import base64
from urllib.parse import urlparse
from bs4 import BeautifulSoup
mongodb_URL,mongodb,collection,collection2,OPENAI_API_KEY=load_environments()
client = AsyncIOMotorClient(mongodb_URL)
db = client[mongodb]
data_col = db["data"]
EMBEDDING_MODEL = "text-embedding-3-large"
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
async def ai_generate_summary(content: str):
    """Summarize the content using GPT."""
    try:
        prompt = f"Summarize this text in 2-3 lines:\n\n{content}"
        res = await ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return "Summary unavailable."

async def ai_generate_tags(content: str):
    """Generate 5 relevant tags for the content."""
    prompt = (
    "**Role:** You are an expert content analyst and indexer.\n\n"
    "**Task:** Analyze the content below and generate 5 highly specific and relevant tags. \n\n"
    "**Guidelines for Tags:**\n"
    "1.  **Relevance:** Tags must capture the *core concepts* and primary topics. Do not use generic or overly broad tags.\n"
    "2.  **Format:** Tags should be 1-3 word keyphrases. Do not use full sentences.\n"
    "3.  **Quantity:** Provide exactly 5 unique tags.\n"
    "4.  **Output:** Return *only* a valid JSON array of strings. Do not include any explanation or other text.\n\n"
    f"**Content:**\n{content}\n\n"
    "**JSON Output:**")
    try:
        res = await ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60
        )
        tags = re.findall(r'\b\w+\b', res.choices[0].message.content)
        return list({t.lower() for t in tags[:5]})
    except Exception:
        return []

async def ai_classify_category(content: str) -> list[str]:
    """
    Classify content into 2–4 broad categories using GPT.
    Compatible with OpenAI Python SDK v2.7.1.
    """
    prompt = (
        "**Role:** You are an expert taxonomist and data analyst.\n"
        "**Task:** Given the text below, return 2–4 broad, high-level categories.\n\n"
        "**Format:** Respond ONLY as a valid JSON object with this structure:\n"
        '{"categories": ["Technology", "AI", "Machine Learning"]}\n\n'
        f"**Content:**\n{content}\n\n"
        "**JSON Output:**"
    )

    try:
        # Create completion request
        res = await ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            response_format={"type": "json_object"}  
        )
        message = res.choices[0].message
        raw_output = getattr(message, "content", None)
        categories = []
        if raw_output:
            try:
                
                parsed = json.loads(raw_output)
                categories = parsed.get("categories", [])
            except json.JSONDecodeError as je:
                categories = []

        # Default fallback
        if not categories:
            categories = ["General"]

        # Clean formatting
        clean_categories = [c.strip().title() for c in categories if isinstance(c, str)]
        return clean_categories

    except Exception as e:
        return ["General"]


def extract_source_platform(url: str) -> str:
    """Extract platform name from URL."""
    try:
        domain = urlparse(url).netloc
        if "youtube" in domain:
            return "YouTube"
        elif "medium" in domain:
            return "Medium"
        elif "perplexity" in domain:
            return "Perplexity"
        else:
            return domain.split(".")[0].capitalize()
    except Exception:
        return "Web"

async def generate_embedding(text: str) -> list[float]:
    """
    Generate a semantic embedding vector for combined text data.
    Returns a list of floats for MongoDB vector storage.
    """
    try:
        if not text or len(text.strip()) == 0:
            return []

        response = await ai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )

        return response.data[0].embedding

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

def fetch_url_content(url: str):
    """Extract readable text and title from a URL using newspaper3k."""
    try:
        
        article = newspaper.Article(url)
        article.download()
        article.parse()
        title = article.title if article.title else "Untitled"
        text = article.text
        
        if not text:
            
            return title, "No readable content found."

        return title, text[:5000]  # Return title and cleaned text

    except Exception as e:
        print(f"Error fetching with newspaper3k: {e}")
        # Raise the same exception your other code expects
        raise HTTPException(status_code=400, detail=f"Failed to fetch or parse URL content: {e}")
def compress_image(image_bytes: bytes, max_size=(800, 800)):
    image = Image.open(io.BytesIO(image_bytes))
    image.thumbnail(max_size)
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
async def ai_describe_image(image_bytes: bytes) -> str:
    """Generate a short caption for an image using GPT-4o."""
    try:
        # 1️⃣ Encode image bytes to Base64
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # 2️⃣ Create a data URL
        data_url = f"data:image/png;base64,{base64_image}"

        # 3️⃣ Send to GPT-4o
        res = await ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "You are an AI generating descriptive ALT text. Provide a concise, 2-3 sentence description of the image. Focus on the main subject, a brief note of the setting, and any significant actions. Do not interpret emotions or intentions."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=150,
        )

        description = res.choices[0].message.content.strip()
        print("🖼️ AI Image Description:", description)
        return description or "Image description unavailable."

    except Exception as e:
        print("🔥 Error in ai_describe_image:", e)
        return "Image description unavailable."


async def ai_generate_title(content: str) -> str:
    """
    Generate a short, meaningful title for a given content using GPT.
    """
    try:
        prompt = (
            "Generate a short, relevant and catchy title (max 10 words) "
            "that best represents the following content:\n\n"
            f"{content[:2000]}"  
        )
        res = await ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20
        )
        title = res.choices[0].message.content.strip()
        return title if title else "Untitled"
    except Exception:
        return "Untitled"


async def save_user_stuff(user_id: str, data_type: str, content:str=None, media_url: str = None):
    """
    Save user-uploaded text, image, or URL intelligently into MongoDB.
    """
    try:
        if data_type not in ["text", "url", "image"]:
            raise HTTPException(status_code=400, detail="Invalid data type")

        summary = ""
        tags = []
        category = []
        title = ""
        source_platform = ""
        stored_content = ""

        if data_type == "text":
            stored_content = content
            summary = await ai_generate_summary(content)
            tags = await ai_generate_tags(content)
            category = await ai_classify_category(content)
            title = await ai_generate_title(content)
            source_platform = "Manual Entry"

        elif data_type == "url":
            title, url_content = fetch_url_content(content)
            summary = await ai_generate_summary(url_content)
            tags = await ai_generate_tags(url_content)
            category = await ai_classify_category(url_content)
            stored_content = url_content
            source_platform = extract_source_platform(content)
            media_url = content
        elif data_type == "image":
            summary = await ai_describe_image(content)
            tags = await ai_generate_tags(summary)
            category = await ai_classify_category(summary)
            title = await ai_generate_title(summary)
            stored_content = await ai_generate_summary(summary)  
            source_platform = "User Upload"
        combined_text = f"""
        Title: {title}
        Summary: {summary}
        Content: {stored_content}
        Tags: {', '.join(tags) if tags else ''}
        Categories: {', '.join(category) if isinstance(category, list) else category}
        """

        embedding_vector = await generate_embedding(combined_text)
        doc = {
            "user_id": user_id,
            "type": data_type,
            "title": title,
            "content": stored_content,
            "summary": summary,
            "tags": tags,
            "category": category,
            "source_platform": source_platform,
            "media_url": media_url,
            "embedding": embedding_vector,
            "created_at": datetime.now(timezone.utc)
        }

        await data_col.insert_one(doc)
        return {"message": "Data saved successfully", "summary": summary, "tags": tags, "category": category}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")