import re
from dotenv import load_dotenv
import os
from fastapi import WebSocket, WebSocketException, status
import jwt
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone

load_dotenv(override=True)

password_hash = PasswordHash.recommended()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 720  # expire in 12 hours

PASSWORD_REGEX = r"^((?=\S*?[A-Z])(?=\S*?[a-z])(?=\S*?[0-9]).{6,})\S$"


def create_token(subject: str, role: str):
    """
    Genarate a jwt token with a username and role
    """

    expire = datetime.now(timezone.utc) + \
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    token_payload = {
        "sub": subject,
        "role": role,
        "exp": expire
    }
    jwt_token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)
    return jwt_token


def encryptPassword(password: str):
    return password_hash.hash(password)


def verify_paasword(plain_password: str, hash_password: str) -> str:
    return password_hash.verify(plain_password, hash_password)


def validate_password(password: str) -> bool:
    return bool(re.match(PASSWORD_REGEX, password))


async def ws_authenticate(websocket: WebSocket) -> dict:
    """
    Validates JWT passed as ?token=<jwt> query param on WS connections.
    Raises WebSocketException (403) if missing or invalid.
    """
    token = websocket.query_params.get("token")

    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
