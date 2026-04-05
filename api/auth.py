import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from api.models import LoginRequest, TokenResponse

logger = logging.getLogger(__name__)

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 24 * 30  # 30 days — only 2 users, long-lived tokens are fine
_USERS_PATH = Path(__file__).parent.parent / "config" / "users.yaml"

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer()

router = APIRouter()


def _get_secret() -> str:
    secret = os.environ.get("PV_JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "PV_JWT_SECRET environment variable is not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret


def _load_users() -> dict[str, str]:
    """Return {username: hashed_password} from users.yaml."""
    with open(_USERS_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return {u["username"]: u["hashed_password"] for u in raw.get("users", [])}


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, _get_secret(), algorithm=_ALGORITHM)


def decode_token(token: str) -> str:
    """Return username from a valid token, or raise HTTPException 401."""
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[_ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise JWTError("missing sub")
        return username
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """FastAPI dependency — validates Bearer token and returns the username."""
    return decode_token(credentials.credentials)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    users = _load_users()
    hashed = users.get(body.username)
    if hashed is None or not _pwd_context.verify(body.password, hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token(body.username)
    logger.info("User '%s' logged in", body.username)
    return TokenResponse(access_token=token)
