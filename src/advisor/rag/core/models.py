# src/core/models.py
import os
from dotenv import load_dotenv

import numpy as np
from openai import AsyncOpenAI

from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", None) or None

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMB_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")

# If you switch embedding models, update these to match
EMB_DIM = int(os.getenv("EMBED_DIM", "3072"))
EMB_MAXTOK = int(os.getenv("EMBED_MAXTOK", "8192"))

# ---------------------------
# LLM (text) function
# ---------------------------
def llm_model_func(prompt, system_prompt=None, history_messages=None, **kwargs):
    if history_messages is None:
        history_messages = []
    return openai_complete_if_cache(
        LLM_MODEL,
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=API_KEY,
        base_url=BASE_URL,
        **kwargs,
    )

# ---------------------------
# Vision function (matches your existing behavior)
# ---------------------------
def vision_model_func(
    prompt,
    system_prompt=None,
    history_messages=None,
    image_data=None,
    messages=None,
    **kwargs,
):
    if history_messages is None:
        history_messages = []

    # If messages present, pass through (RAG-Anything example style)
    if messages:
        return openai_complete_if_cache(
            "gpt-4o",
            "",
            system_prompt=None,
            history_messages=[],
            messages=messages,
            api_key=API_KEY,
            base_url=BASE_URL,
            **kwargs,
        )

    # If image_data present, build a multimodal message
    if image_data:
        mm_messages = []
        if system_prompt:
            mm_messages.append({"role": "system", "content": system_prompt})

        mm_messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }
        )

        return openai_complete_if_cache(
            "gpt-4o",
            "",
            system_prompt=None,
            history_messages=[],
            messages=mm_messages,
            api_key=API_KEY,
            base_url=BASE_URL,
            **kwargs,
        )

    # Fallback to text LLM
    return llm_model_func(prompt, system_prompt, history_messages, **kwargs)

# ---------------------------
# Embeddings (FIXED): bypass lightrag.openai_embed and return numpy array
# ---------------------------
_client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

async def _embed_texts(texts):
    """
    LightRAG expects a numpy array so it can use `.size` internally.
    Must return exactly one vector per input text.
    """
    # Ensure we always pass a list[str]
    if isinstance(texts, str):
        texts = [texts]

    resp = await _client.embeddings.create(
        model=EMB_MODEL,
        input=texts,
    )

    vecs = [item.embedding for item in resp.data]

    if len(vecs) != len(texts):
        raise ValueError(f"Embedding count mismatch: inputs={len(texts)} outputs={len(vecs)}")

    arr = np.asarray(vecs, dtype=np.float32)

    # Safety checks (helpful for debugging model switches)
    if arr.ndim != 2 or arr.shape[0] != len(texts):
        raise ValueError(f"Unexpected embedding array shape: {arr.shape}")
    if EMB_DIM and arr.shape[1] != EMB_DIM:
        raise ValueError(f"Embedding dim mismatch: expected {EMB_DIM}, got {arr.shape[1]}")

    return arr

embedding_func = EmbeddingFunc(
    embedding_dim=EMB_DIM,
    max_token_size=EMB_MAXTOK,
    func=_embed_texts,
)
