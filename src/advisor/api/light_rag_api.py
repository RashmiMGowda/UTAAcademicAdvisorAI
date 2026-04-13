# this file defines the API endpoints for the light RAG advisor,
# including authentication and query handling. It uses FastAPI to create a
# web server that can receive requests from the frontend and interact with
# the compact store and authentication system.
# this line is needed to allow for forward references in type hints, which can help with readability and avoid issues with circular imports.
from __future__ import annotations

# FastAPI is a modern web framework for building APIs with Python. Header and HTTPException are used for handling HTTP headers and exceptions in the API endpoints.
from fastapi import FastAPI
# CORSMiddleware is a middleware for handling Cross-Origin Resource Sharing (CORS) in FastAPI, which allows the API to be accessed from different origins (e.g., frontend running on a different domain or port).
from fastapi.middleware.cors import CORSMiddleware
# BaseModel is a base class from the Pydantic library, which is used for data validation and settings management using Python type annotations. It allows us to define data models for request payloads and responses in a clear and structured way.
from pydantic import BaseModel

# The following imports are from the local project and handle authentication, user management, and interactions with the compact store for the RAG advisor.
from src.advisor.rag.light.compact_store import (
    DEFAULT_KV_PATH,
    DEFAULT_STORE_PATH,
    build_compact_store,
    query_compact_store,
)

# The following classes define the data models for the API endpoints using Pydantic's BaseModel.
# These models specify the expected structure of the request payloads for authentication and advisor queries.


class AdvisorQuery(BaseModel):
    program: str = ""
    question: str
    course_filter: str = ""


# The following code initializes the FastAPI application and sets up CORS middleware
# to allow requests from any origin. The API endpoints are defined below,
# including health check, authentication (Google and local), retrieving user info,
# logging out, retrieving advisor history, handling advisor queries,
#  and building the compact store. Each endpoint includes appropriate
# authentication checks and interactions with the underlying data stores and services.
app = FastAPI(title="UTA RAG Advisor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# This endpoint provides a health check for the API,
# returning information about the existence of the compact store and key-value chunks.


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

# This endpoint triggers the building of the compact store by calling the build_compact_store function.
# It returns a response indicating that the operation was successful and includes the path to the newly built compact store.
#  This endpoint does not require authentication, but in a production system, you might want to restrict access to this functionality to authorized users only.


@app.post("/advisor/build-light-store")
def build_light_store() -> dict:
    path = build_compact_store()
    return {"ok": True, "store_path": str(path)}
