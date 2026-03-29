from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.advisor.api.auth_store import (
    create_session,
    delete_session,
    get_chat_history,
    get_user_for_token,
    save_chat_turn,
    upsert_local_user,
    upsert_google_user,
)
from src.advisor.api.google_auth import verify_google_credential
from src.advisor.rag.light.compact_store import (
    DEFAULT_KV_PATH,
    DEFAULT_STORE_PATH,
    build_compact_store,
    query_compact_store,
)


class AdvisorQuery(BaseModel):
    program: str = ""
    question: str
    course_filter: str = ""


class GoogleAuthPayload(BaseModel):
    credential: str


class LocalLoginPayload(BaseModel):
    username: str
    password: str


app = FastAPI(title="UTA RAG Advisor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "compact_store_exists": DEFAULT_STORE_PATH.exists(),
        "kv_chunks_exists": DEFAULT_KV_PATH.exists(),
    }


@app.post("/auth/google")
def auth_google(payload: GoogleAuthPayload) -> dict:
    profile = verify_google_credential(payload.credential)
    user_id = upsert_google_user(
        google_sub=str(profile["sub"]),
        email=str(profile.get("email", "")),
        name=str(profile.get("name", "UTA Student")),
        picture=str(profile.get("picture", "")),
    )
    token = create_session(user_id)
    return {
        "session_token": token,
        "user": {
            "name": str(profile.get("name", "UTA Student")),
            "email": str(profile.get("email", "")),
            "picture": str(profile.get("picture", "")),
        },
    }


@app.post("/auth/local")
def auth_local(payload: LocalLoginPayload) -> dict:
    username = payload.username.strip()
    password = payload.password.strip()
    if username != "aiproj" or password != "333":
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id = upsert_local_user(username="aiproj", name="AI Project User")
    token = create_session(user_id)
    return {
        "session_token": token,
        "user": {
            "name": "AI Project User",
            "email": "aiproj@local.demo",
            "picture": "",
        },
    }


@app.get("/auth/me")
def auth_me(authorization: str | None = Header(default=None)) -> dict:
    token = _extract_bearer_token(authorization)
    user = get_user_for_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"user": {"name": user.name, "email": user.email, "picture": user.picture}}


@app.post("/auth/logout")
def auth_logout(authorization: str | None = Header(default=None)) -> dict:
    token = _extract_bearer_token(authorization)
    delete_session(token)
    return {"ok": True}


@app.get("/advisor/history")
def advisor_history(authorization: str | None = Header(default=None)) -> dict:
    token = _extract_bearer_token(authorization)
    user = get_user_for_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"messages": get_chat_history(user.user_id)}


@app.post("/advisor/query")
def advisor_query(payload: AdvisorQuery, authorization: str | None = Header(default=None)) -> dict:
    response = query_compact_store(
        program=payload.program,
        question=payload.question,
        course_filter=payload.course_filter,
    )
    token = _extract_bearer_token(authorization)
    user = get_user_for_token(token)
    if user is not None:
        save_chat_turn(user.user_id, payload.question, response)
    return response


@app.post("/advisor/build-light-store")
def build_light_store() -> dict:
    path = build_compact_store()
    return {"ok": True, "store_path": str(path)}


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None
