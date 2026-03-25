# src/core/config.py
import os

# Storage
WORKING_DIR = os.getenv("WORKING_DIR", "./rag_storage")
DATA_SOURCES_DIR = os.getenv("DATA_SOURCES_DIR", "./data/sources")

# Models
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")

# Retrieval knobs
TOP_K = int(os.getenv("TOP_K", "20"))
COSINE_CUTOFF = float(os.getenv("COSINE_CUTOFF", "0.2"))

# Windows / console stability
os.environ.setdefault("LIGHTRAG_DISABLE_SHARED", "1")
os.environ.setdefault("PYTHONUNBUFFERED", "1")
