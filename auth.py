from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from utils.config import get_JWT_settings
from fastapi import HTTPException, status
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
ALGORITHM,SECRET_KEY,ACCESS_TOKEN_EXPIRE_MINUTES=get_JWT_settings()


def create_access_token(username: str, user_id: int, expires_delta: timedelta = timedelta(hours=1)):
    now_utc = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "uid": user_id,
        "exp": now_utc + expires_delta,
        "iat": now_utc
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if credentials.scheme != "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            payload = verify_token(credentials.credentials)
            return payload
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization token.")