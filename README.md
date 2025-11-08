# Synapse Brain: AI-Powered Knowledge Base API

This project is an AI-powered personal knowledge base API built with FastAPI. It allows users to save, process, and perform semantic searches on text, URLs, and images.

The core design philosophy is to not just *store* data, but to *understand* it. By using AI to augment all incoming data, we create a rich, vector-based knowledge base that can be queried using natural language, rather than simple keyword matching.

## 🚀 Key Features

* **User Authentication:** Secure user registration and login using JWT (JSON Web Tokens).
* **Multi-Modal Data Ingestion:** A single endpoint (`/add`) intelligently handles text, URLs, and images.
* **AI Content Augmentation:** All data is automatically processed by `gpt-4o-mini` to generate:
    * **Summaries**
    * **Descriptive Titles**
    * **Key-phrase Tags**
    * **High-Level Categories**
* **Image-to-Text Vision:** Uploaded images are analyzed by `gpt-4o-mini` (vision) to generate descriptive summaries, making them searchable.
* **Semantic Vector Search:** All content is converted into `text-embedding-3-large` embeddings and stored in MongoDB.
* **Hybrid Search Strategy:** Uses **MongoDB Atlas `$vectorSearch`** for high-speed, scalable search, with a **robust `numpy`-based cosine similarity fallback** for non-Atlas deployments.

## 🧠 Approaches & Challenges Solved

This project was built to solve several key challenges in creating a "second brain."

### 1. Unified Data Ingestion

* **Challenge:** How to create a single, simple API for users to add vastly different data types (text, URLs, images) without making three different endpoints.
* **Approach:** We use a single `POST /add` endpoint that accepts `multipart/form-data`.
* **Implementation (`core/add_data.py`):** The `save_user_stuff` function acts as a central controller. It checks the `data_type` form-field (`text`, `url`, or `image`) and branches the logic:
    * `data_type == "url"`: Triggers `fetch_url_content` (using `newspaper3k`) to scrape the article text.
    * `data_type == "image"`: Triggers `ai_describe_image` to process the image bytes.
    * `data_type == "text"`: Uses the raw text content directly.

### 2. Making Unsearchable Data Searchable (Vision AI)

* **Challenge:** Images are just pixels. How can a user find an image using text queries like "that whiteboard diagram"?
* **Approach:** Use a multimodal AI (GPT-4o-mini with vision) to generate a text description *about* the image. This text description is then used as the "content" for summarization, tagging, and vector embedding.
* **Implementation (`core/add_data.py`):** The `ai_describe_image` function:
    1.  Base64-encodes the raw image bytes.
    2.  Sends this data URL to `gpt-4o-mini` with a specific prompt ("*Provide a concise, 2-3 sentence description...*").
    3.  This AI-generated description is then treated just like any other text, allowing it to be found via semantic search.

### 3. Robust, High-Quality AI Metadata

* **Challenge:** AI-generated content can be inconsistent. We need clean, reliable, and *structured* output (like JSON arrays) from the LLM.
* **Approach:** Used specific, role-based prompting and OpenAI's `response_format` feature.
* **Implementation (`core/add_data.py`):**
    * **`ai_classify_category`:** This function's prompt is a key example. It commands the AI to act as an "**expert taxonomist**" and, most importantly, to "**Respond ONLY as a valid JSON object**" with a specific structure: `{"categories": [...]}`. This ensures a machine-readable list of categories every time.
    * **`ai_generate_tags`:** Similarly, this prompt defines the role ("**expert content analyst**") and demands a "**valid JSON array of strings**," ensuring the output can be directly stored in the database.

### 4. Resilient Semantic Search (Atlas + Fallback)

* **Challenge:** MongoDB Atlas `$vectorSearch` is powerful but requires a specific cloud setup. A local MongoDB instance or a misconfigured index would completely break the search functionality.
* **Approach:** Implement a two-stage search strategy. *Try* the fast, indexed Atlas search first. If it fails *for any reason*, automatically fall back to a manual, in-memory cosine similarity search.
* **Implementation (`core/find_data.py`):**
    1.  **Primary:** The `vector_search` function first attempts a MongoDB aggregation pipeline using `$vectorSearch`. This is the preferred, high-performance method.
    2.  **Fallback:** The `$vectorSearch` call is wrapped in a `try...except` block. If it fails, the `except` block prints a warning and then calls `_local_cosine_search`.
    3.  **`_local_cosine_search`:** This fallback function is a pure-Python solution. It:
        * Fetches all document embeddings for the user from MongoDB.
        * Uses `numpy` to manually calculate the cosine similarity between the user's `query_vector` and every document vector.
        * Sorts the results in Python.
    * This "dual-mode" approach makes the application resilient and deployable in any environment, from a local machine to a full-scale Atlas cluster.

### 5. AI-Powered Query Understanding

* **Challenge:** A user's search query might imply a data type. For example, "find my photo of a sunset" should ideally only search images.
* **Approach:** Use an LLM to classify the *user's query itself* before performing the search.
* **Implementation (`core/find_data.py`):**
    * The `semantic_search` endpoint first calls `classify_query_type`.
    * This function sends the user's query (e.g., "show me that photo") to `gpt-4o-mini` with a prompt to classify it as `text`, `image`, `url`, or `all`.
    * This `query_type` is then passed to `vector_search` and inserted into the MongoDB `$vectorSearch` filter (or the local search filter), dramatically narrowing the search space and improving relevance.

## 💻 Technologies Used

* **Backend:** [FastAPI](https://fastapi.tiangolo.com/)
* **Database:** [MongoDB](https://www.mongodb.com/) (using [Motor](https://motor.readthedocs.io/en/stable/) for async operations)
* **AI & Embeddings:** [OpenAI API](https://openai.com/) (GPT-4o-mini, text-embedding-3-large)
* **Authentication:** [python-jose](https://github.com/mpdavis/python-jose) for JWT, [passlib](https://passlib.readthedocs.io/en/stable/) for password hashing.
* **Web Scraping:** [newspaper3k](https://github.com/codelucas/newspaper)
* **Image Handling:** [Pillow (PIL)](https://pillow.readthedocs.io/en/stable/)
* **Vector Math:** [NumPy](https://numpy.org/) (for fallback search)

---

## 🛠️ Setup & Installation

### 1. Prerequisites

* Python 3.8+
* MongoDB database (An Atlas cluster is recommended for `$vectorSearch`).
* An OpenAI API Key.

### 2. Installation

**Install dependencies from `requirements.txt`:**
    ```bash
    pip install -r requirements.txt
    ```
    

### 3. Environment Variables

Create a `.env` file in the root directory:

```.env.example
# --- OpenAI ---
OPENAI_API_KEY="sk-..."

# --- MongoDB ---
MONGODB_URL="mongodb+srv://..."
MONGODB_NAME="YourDatabaseName"
USERS_COLLECTION="users"
DATA_COLLECTION="data"

# --- JWT (must be strong and secret) ---
JWT_SECRET_KEY="your_super_secret_key_for_jwt"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
