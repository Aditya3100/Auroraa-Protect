from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import os

OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl=os.getenv("AUTH_LOGIN_URL"))

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ISSUER = os.getenv("JWT_ISSUER")
ALGORITHM = "HS256"

if not SECRET_KEY or not ISSUER: 
    raise RuntimeError("JWT config missing")

def get_current_user(token: str = Depends(OAUTH2_SCHEME)):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"verify_aud": False},
        )

        user_id = payload.get("sub")
        username = payload.get("username")
        role = payload.get("role", "user")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {
            "user_id": user_id,
            "username": username,
            "role": role,
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
