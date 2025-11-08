import os, re, requests
from datetime import datetime, timezone
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from utils.config import load_environments
from urllib.parse import urlparse
from bs4 import BeautifulSoup
mongodb_URL,mongodb,collection,collection2,OPENAI_API_KEY=load_environments()
client = AsyncIOMotorClient(mongodb_URL)
db = client[mongodb]
data_col = db["data"]

ai_client = AsyncOpenAI(api_key=OPENAI_KEY)
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
    prompt = f"Generate 5 short, relevant tags for this content:\n\n{content}"
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

async def ai_classify_category(content: str):
    """Classify the main category of this content."""
    prompt = f"Classify this content into one broad topic (e.g. AI, Design, Business, Education, Science, etc.):\n\n{content}"
    try:
        res = await ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20
        )
        return res.choices[0].message.content.strip().title()
    except Exception:
        return "General"


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

def fetch_url_content(url: str):
    """Extract readable text and title from a URL."""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string if soup.title else "Untitled"
        text = ' '.join([p.get_text() for p in soup.find_all('p')])
        return title, text[:5000]  # limit content length
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to fetch URL content.")

async def ai_describe_image(image_bytes: bytes):
    """Generate a short caption for an image."""
    try:
        res = await ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image briefly in one sentence:"},
                        {"type": "image_url", "image_url": image_bytes}
                    ],
                }
            ],
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return "Image description unavailable."


async def save_user_stuff(user_id: str, data_type: str, content:str=None, media_url: str = None):
    """
    Save user-uploaded text, image, or URL intelligently into MongoDB.
    """
    try:
        if data_type not in ["text", "url", "image"]:
            raise HTTPException(status_code=400, detail="Invalid data type")

        summary = ""
        tags = []
        category = ""
        title = ""
        source_platform = ""
        stored_content = ""

        if data_type == "text":
            stored_content = content
            summary = await ai_generate_summary(content)
            tags = await ai_generate_tags(content)
            category = await ai_classify_category(content)
            title = content[:50] + "..." if len(content) > 50 else content
            source_platform = "Manual Entry"

        elif data_type == "url":
            title, url_content = fetch_url_content(content)
            summary = await ai_generate_summary(url_content)
            tags = await ai_generate_tags(url_content)
            category = await ai_classify_category(url_content)
            stored_content = url_content
            source_platform = extract_source_platform(content)
            media_url = content

        # --- Handle Image ---
        elif data_type == "image":
            summary = await ai_describe_image(content)
            tags = await ai_generate_tags(summary)
            category = await ai_classify_category(summary)
            title = "Image Upload"
            stored_content = summary  # textual description for indexing
            source_platform = "User Upload"
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
            "created_at": datetime.now(timezone.utc)
        }

        await data_col.insert_one(doc)
        return {"message": "✅ Data saved successfully", "summary": summary, "tags": tags, "category": category}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")