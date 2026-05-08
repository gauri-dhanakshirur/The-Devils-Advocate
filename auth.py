"""
Devil's Advocate — Authentication Module
JWT-based authentication with SQLite-persisted users.
"""

import os
import jwt
import bcrypt
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger("auth")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "da-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

DB_PATH = "devils_advocate.db"
security = HTTPBearer()


# ── Pydantic models ───────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: str
    password: str
    name: str = ""


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── DB helpers ────────────────────────────────────────────────────────

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_users_table():
    """Create users table if it doesn't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT DEFAULT '',
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


# Create table on import
_ensure_users_table()


# ── User class ────────────────────────────────────────────────────────

class User:
    @classmethod
    def create(cls, email: str, password: str, name: str = "") -> dict:
        email = email.lower().strip()
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        display_name = name.strip() or email.split("@")[0]
        try:
            with _get_conn() as conn:
                conn.execute(
                    "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
                    (email, display_name, hashed)
                )
                conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError("An account with this email already exists")
        return {"email": email, "name": display_name}

    @classmethod
    def verify(cls, email: str, password: str) -> Optional[dict]:
        email = email.lower().strip()
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
        if not row:
            return None
        if bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
            return {"email": row["email"], "name": row["name"]}
        return None

    @classmethod
    def get(cls, email: str) -> Optional[dict]:
        email = email.lower().strip()
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT email, name FROM users WHERE email = ?", (email,)
            ).fetchone()
        return dict(row) if row else None


# ── JWT helpers ───────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    payload = decode_token(credentials.credentials)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = User.get(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
