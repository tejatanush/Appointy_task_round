from fastapi import FastAPI
from routes.login_routes import log_router

app = FastAPI(title="Appointy Simple API")

app.include_router(log_router)

@app.get("/")
def home():
    return {"message": "✅ Appointy Backend Running Successfully!"}
