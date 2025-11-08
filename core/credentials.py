from utils.config import load_environments,get_JWT_settings
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
from datetime import datetime,timedelta,timezone
from passlib.context import CryptContext
from jose import jwt 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
mongodb_URL,mongodb,collection,collection2,OPENAI_API_KEY=load_environments()
ALGORITHM, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES = get_JWT_settings()
client=AsyncIOMotorClient(mongodb_URL)
database=client[mongodb]
collection=database[collection]


async def register_user(name: str, email: str, password: str):
    existing = await collection.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = pwd_context.hash(password)
    new_user = {
        "name": name,
        "email": email,
        "password_hash": hashed_pw,
        "created_at": datetime.now(timezone.utc)
    }
    await collection.insert_one(new_user)

    return {"message": "User registered successfully"}

async def login_user(email: str, password: str):
    user = await collection.find_one({"email": email})
    if not user or not pwd_context.verify(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Safety check
    if "email" not in user:
        raise HTTPException(status_code=500, detail="Corrupted user record: missing email")

    payload = {
        "uid": str(user["_id"]),
        "email": user["email"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user["_id"]),
        "email": user["email"]
    }