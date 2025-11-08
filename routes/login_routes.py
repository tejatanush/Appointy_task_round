from fastapi import APIRouter, Depends, HTTPException,status
from passlib.context import CryptContext
from models import SignupRequest, LoginRequest
from core.credentials import register_user, login_user
from utils.config import get_JWT_settings
from auth import create_access_token
from motor.motor_asyncio import AsyncIOMotorClient
log_router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
algo,secrete_key2,time_in_min=get_JWT_settings()
@log_router.post("/signup", summary="Register a new user", response_model=dict)
async def signup(data: SignupRequest):
    """
    Create a new user securely with hashed password.
    Returns success message or error if already registered.
    """
    try:
        await register_user(data.name, data.email, data.password)
        return {"message": "User registered successfully!"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@log_router.post("/login", summary="Login and get access token")
async def login(data: LoginRequest):
    """
    Verify user credentials, generate a JWT access token,
    and return basic user info for the session.
    """
    try:
        result = await login_user(data.email, data.password)
        result["message"] = "✅ Login successful!"
        return result

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    


