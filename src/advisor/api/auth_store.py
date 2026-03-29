from __future__ import annotations

import json
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "storage" / "app_state" / "advisor.db"
SESSION_DAYS = 14


@dataclass
class SessionUser:
    user_id: int
    name: str
    email: str
    picture: str
    session_token: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_sub TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                picture TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                message_text TEXT NOT NULL,
                response_json TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )


def upsert_google_user(google_sub: str, email: str, name: str, picture: str = "") -> int:
    timestamp = utc_now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users (google_sub, email, name, picture, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(google_sub) DO UPDATE SET
                email = excluded.email,
                name = excluded.name,
                picture = excluded.picture,
                updated_at = excluded.updated_at
            """,
            (google_sub, email, name, picture, timestamp, timestamp),
        )
        row = conn.execute(
            "SELECT id FROM users WHERE google_sub = ?",
            (google_sub,),
        ).fetchone()
        return int(row["id"])


def upsert_local_user(username: str, name: str) -> int:
    pseudo_sub = f"local:{username}"
    pseudo_email = f"{username}@local.demo"
    return upsert_google_user(
        google_sub=pseudo_sub,
        email=pseudo_email,
        name=name,
        picture="",
    )


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(days=SESSION_DAYS)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, created_at.isoformat(timespec="seconds"), expires_at.isoformat(timespec="seconds")),
        )
    return token


def get_user_for_token(token: str | None) -> SessionUser | None:
    if not token:
        return None
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT users.id, users.name, users.email, users.picture, sessions.token, sessions.expires_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
        if row is None:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at <= datetime.now(timezone.utc):
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
        return SessionUser(
            user_id=int(row["id"]),
            name=str(row["name"]),
            email=str(row["email"]),
            picture=str(row["picture"] or ""),
            session_token=str(row["token"]),
        )


def delete_session(token: str | None) -> None:
    if not token:
        return
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def save_chat_turn(user_id: int, question: str, response: dict[str, Any]) -> None:
    timestamp = utc_now()
    payload = json.dumps(response, ensure_ascii=False)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (user_id, role, message_text, response_json, created_at)
            VALUES (?, 'user', ?, '', ?)
            """,
            (user_id, question, timestamp),
        )
        conn.execute(
            """
            INSERT INTO chat_messages (user_id, role, message_text, response_json, created_at)
            VALUES (?, 'assistant', ?, ?, ?)
            """,
            (user_id, response.get("summary", ""), payload, timestamp),
        )


def get_chat_history(user_id: int, limit: int = 24) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT role, message_text, response_json, created_at
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    history: list[dict[str, Any]] = []
    for row in reversed(rows):
        role = str(row["role"])
        if role == "assistant":
            payload = json.loads(row["response_json"]) if row["response_json"] else {}
            history.append(
                {
                    "role": "assistant",
                    "summary": payload.get("summary", row["message_text"]),
                    "recommendations": payload.get("recommendations", []),
                    "notes": payload.get("notes", []),
                    "sources": payload.get("sources", []),
                    "created_at": row["created_at"],
                }
            )
        else:
            history.append(
                {
                    "role": "user",
                    "text": row["message_text"],
                    "created_at": row["created_at"],
                }
            )
    return history


def get_google_client_ids() -> list[str]:
    raw = os.getenv("GOOGLE_CLIENT_ID", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


init_db()
