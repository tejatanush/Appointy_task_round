from fastapi import FastAPI
from routes.login_routes import log_router
from routes.add_data_routes import data_router
from routes.search_data import search_router

app = FastAPI(title="Appointy Simple API")

app.include_router(log_router)
app.include_router(data_router)
app.include_router(search_router)

@app.get("/")
def home():
    return {"message": "✅ Appointy Backend Running Successfully!"}
