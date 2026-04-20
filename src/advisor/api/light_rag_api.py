# API endpoints for the light RAG advisor,

# web server that can receive requests from the frontend and interact with the compact store and authentication system.
from __future__ import annotations

# FastAPI is a modern web framework for building APIs with Python.
from fastapi import FastAPI
# CORSMiddleware is a middleware for handling (CORS) in FastAPI
from fastapi.middleware.cors import CORSMiddleware
# used for data validation and settings management using Python type annotations.
from pydantic import BaseModel

from src.advisor.rag.light.compact_store import (
    DEFAULT_KV_PATH,
    DEFAULT_STORE_PATH,
    build_compact_store,
    query_compact_store,
)

# data models for the API endpoints using Pydantic's BaseModel.


class AdvisorQuery(BaseModel):
    program: str = ""
    question: str
    course_filter: str = ""


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


@app.post("/advisor/query")
def advisor_query(payload: AdvisorQuery) -> dict:
    return query_compact_store(
        program=payload.program,
        question=payload.question,
        course_filter=payload.course_filter,
    )


@app.post("/advisor/build-light-store")
def build_light_store() -> dict:
    path = build_compact_store()
    return {"ok": True, "store_path": str(path)}
