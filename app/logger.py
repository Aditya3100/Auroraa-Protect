from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import os
import httpx

# =========================
# Environment
# =========================

AUTH_BASE_URL = os.getenv("AUTH_LOGIN_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ISSUER = os.getenv("JWT_ISSUER")

if not AUTH_BASE_URL or not JWT_SECRET_KEY or not JWT_ISSUER:
    raise RuntimeError("Auth configuration missing")

AUTH_BASE_URL = AUTH_BASE_URL.rstrip("/")
ALGORITHM = "HS256"

# =========================
# OAuth2 (JWT is optional for public routes)
# =========================

OAUTH2_SCHEME = OAuth2PasswordBearer(
    tokenUrl=f"{AUTH_BASE_URL}/login",
    auto_error=False,   # 🔑 IMPORTANT
)

# =========================
# Current User (protected routes)
# =========================

def get_current_user(token: str | None = Depends(OAUTH2_SCHEME)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=JWT_ISSUER,
            options={"verify_aud": False},
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {
            "user_id": user_id,
            "username": payload.get("username"),
            "role": payload.get("role", "user"),
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

# =========================
# Public username lookup
# =========================

async def get_username_from_auth(user_id: str) -> str | None:
    url = f"{AUTH_BASE_URL}/get/{user_id}"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0)) as client:
            r = await client.get(url)
    except httpx.RequestError as e:
        print("AUTH NETWORK ERROR:", e)
        return None

    print("AUTH STATUS:", r.status_code)
    print("AUTH BODY:", r.text)

    if r.status_code != 200:
        return None

    return r.json().get("username")