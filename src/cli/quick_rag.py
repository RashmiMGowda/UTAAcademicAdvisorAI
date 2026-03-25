# -*- coding: utf-8 -*-
"""
quick_rag.py
Minimal, dependable CLI over your LightRAG/Nano-VectorDB JSON artifacts.

Features:
- Reads embeddings from rag_storage/vdb_chunks.json (supports 'matrix' base64 blob or per-item 'vector')
- Reads text chunks from rag_storage/kv_store_text_chunks.json
- Embeds the query with OpenAI (model dim is inferred from index)
- Cosine similarity retrieval with optional literal-phrase boosting
- Prints RAW snippets and (optionally) an LLM-grounded summary strictly from those snippets
- Loads .env so you don't have to set env vars manually

Usage:
  python -m src.cli.quick_rag --inspect
  python -m src.cli.quick_rag -q "your question" -k 30 --raw-only
  python -m src.cli.quick_rag -q "your question" -k 40 --contains "road diet" "4u-2t" --snippet-chars 900 --with-summary
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path
from typing import Tuple, List, Dict

import numpy as np

from src.core.openai_utils import create_openai_client, load_env

load_env()


# ------------------------
# Utility helpers
# ------------------------

def _b64_to_npfloat32(b64: str) -> np.ndarray:
    """Decode base64 -> float32 array."""
    raw = base64.b64decode(b64)
    arr = np.frombuffer(raw, dtype=np.float32)
    return arr

def _as_np(x) -> np.ndarray:
    return np.array(x, dtype=np.float32)

def _cosine_sim(q: np.ndarray, M: np.ndarray) -> np.ndarray:
    # q: (D,), M: (N,D)
    qn = q / (np.linalg.norm(q) + 1e-9)
    Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    return Mn @ qn

def _shorten(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return " ".join(s.split())
    return " ".join((s[:max_chars] + " ...").split())

def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _get_env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


# ------------------------
# Load index files
# ------------------------

def load_vdb(vdb_path: Path) -> Tuple[np.ndarray, List[str], List[str], List[str]]:
    """
    Returns:
      embs: (N,D) float32
      chunk_ids: [N]
      contents:  [N]
      file_paths:[N]
    Supports:
      - top-level "matrix" (base64 float32 x N*D)
      - per-record "vector" (list[float] or base64)
    """
    vdb = _read_json(vdb_path)
    dim = vdb.get("embedding_dim")
    data = vdb.get("data", [])

    # Case A: fast path with 'matrix'
    matrix_b64 = vdb.get("matrix")
    if matrix_b64:
        vecs = _b64_to_npfloat32(matrix_b64)
        if dim is None:
            raise RuntimeError("vdb has 'matrix' but no 'embedding_dim'.")
        if vecs.size % dim != 0:
            raise RuntimeError("matrix size not divisible by embedding_dim.")
        N = vecs.size // dim
        embs = vecs.reshape(N, dim)
        chunk_ids, contents, file_paths = [], [], []
        for row in data:
            chunk_ids.append(row.get("__id__", ""))
            contents.append(row.get("content", ""))
            file_paths.append(row.get("file_path", ""))
        if len(chunk_ids) != N:
            # If counts mismatch, fall back to building from per-item vector
            # (Some LightRAG exports can have different 'data' len)
            # Try per-item vector path instead:
            matrix_b64 = None  # force fallback
        else:
            return embs, chunk_ids, contents, file_paths

    # Case B: per-item 'vector'
    chunk_ids, contents, file_paths, rows = [], [], [], []
    for row in data:
        cid = row.get("__id__", "")
        txt = row.get("content", "")
        fp = row.get("file_path", "")
        vec = row.get("vector", None)
        if vec is None:
            continue
        if isinstance(vec, str):
            vec = _b64_to_npfloat32(vec)
        else:
            vec = _as_np(vec)
        rows.append(vec)
        chunk_ids.append(cid)
        contents.append(txt)
        file_paths.append(fp)

    if not rows:
        raise RuntimeError("No numeric vectors found in vdb_chunks.json")

    embs = np.vstack(rows).astype(np.float32)
    if dim is not None and embs.shape[1] != dim:
        # Warn but continue
        print(f"[warn] embedding_dim in file={dim}, detected={embs.shape[1]}", file=sys.stderr)
    return embs, chunk_ids, contents, file_paths


def load_kv(kv_path: Path) -> Dict[str, Dict]:
    return _read_json(kv_path)


# ------------------------
# OpenAI helpers
# ------------------------

def openai_client():
    return create_openai_client()


def embed_query_openai(text: str, expected_dim: int) -> np.ndarray:
    client = openai_client()
    model = _get_env("EMBED_MODEL", "text-embedding-3-large")
    resp = client.embeddings.create(model=model, input=text)
    vec = np.array(resp.data[0].embedding, dtype=np.float32)
    if vec.shape[0] != expected_dim:
        raise RuntimeError(
            f"Embedding dim {vec.shape[0]} != index dim {expected_dim}. "
            f"Set EMBED_MODEL in .env to match your index (likely 'text-embedding-3-large' for 3072)."
        )
    return vec


def summarize_with_llm(question: str, raw_blocks: List[str]) -> str:
    """
    Grounded summary strictly from the provided raw blocks.
    We explicitly instruct the model to answer only using the given context.
    """
    client = openai_client()
    model = _get_env("LLM_MODEL", "gpt-4o-mini")

    sys_msg = (
        "You are a careful analyst. Answer ONLY from the provided context blocks. "
        "If the context does not contain the answer, say 'Not found in the provided context.' "
        "When possible, quote short phrases and list the chunk IDs you relied on."
    )
    context_text = ""
    for i, blk in enumerate(raw_blocks, 1):
        context_text += f"[Block {i}]\n{blk}\n\n"

    user_msg = (
        f"Question:\n{question}\n\n"
        f"Context blocks (quoted excerpts from the corpus; do NOT use outside knowledge):\n{context_text}\n"
        "Answer using only the text above."
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": sys_msg},
                  {"role": "user", "content": user_msg}],
        temperature=0.0,
    )
    return resp.choices[0].message.content.strip()


# ------------------------
# Main CLI
# ------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--question", type=str, default="")
    ap.add_argument("--rag-dir", type=str, default=_get_env("WORKING_DIR", "./rag_storage"))
    ap.add_argument("-k", "--topk", type=int, default=int(_get_env("TOP_K", "10")))
    ap.add_argument("--raw-only", action="store_true", help="print only raw context")
    ap.add_argument("--with-summary", action="store_true", help="also ask LLM to summarize strictly from raw context")
    ap.add_argument("--contains", nargs="*", default=[], help="literal phrases to boost/require in ranking")
    ap.add_argument("--snippet-chars", type=int, default=int(_get_env("RAW_SNIPPET_CHARS", "360")),
                    help="chars to show per snippet in RAW context")
    ap.add_argument("--inspect", action="store_true")
    args = ap.parse_args()

    rag_dir = Path(args.rag_dir)
    vdb_path = rag_dir / "vdb_chunks.json"
    kv_path = rag_dir / "kv_store_text_chunks.json"

    if args.inspect:
        print("Inspecting:")
        print(f"  VDB: {vdb_path}")
        print(f"  KV : {kv_path}\n")
        vdb = _read_json(vdb_path)
        keys = list(vdb.keys())
        print(f"VDB is a DICT with {len(keys)} keys. Sample keys: {keys[:3]}")
        data = vdb.get("data", [])
        print(f" - 'data' length: {len(data)}, first 'data' keys: {list(data[0].keys()) if data else []}")
        if vdb.get("matrix"):
            try:
                # Try decode just to confirm
                vecs = _b64_to_npfloat32(vdb["matrix"])
                dim = vdb.get("embedding_dim", "(unknown)")
                N = vecs.size // (dim if isinstance(dim, int) else 1)
                print(f"\n[detect] using top-level 'matrix' (decoded). Detected ~{N} vectors. Emb dim={dim}")
            except Exception:
                print("\n[detect] 'matrix' present but could not decode (ok if you use per-item 'vector').")
        else:
            has_numeric = any(isinstance(row.get("vector", None), list) for row in data)
            if has_numeric:
                print("\nDetected per-item numeric vectors.")
            else:
                print("\nNo numeric vectors detected at per-item level.")
        kv = load_kv(kv_path)
        print(f"\nKV has {len(kv)} chunk entries.")
        any_item = next(iter(kv.values())) if kv else {}
        print(f"Sample KV keys: {list(any_item.keys()) if any_item else []}")
        if any_item:
            print(f" - file_path: {any_item.get('file_path','')}")
            print(f" - content preview: {_shorten(any_item.get('content',''), 300)}")
        return

    if not args.question:
        print("Provide a question with -q/--question, or use --inspect.")
        sys.exit(1)

    # Load index
    embs, chunk_ids, contents, file_paths = load_vdb(vdb_path)  # (N,D)
    # Embed query
    qvec = embed_query_openai(args.question, embs.shape[1])     # (D,)
    sims = _cosine_sim(qvec, embs)                              # (N,)

    # Optional literal-phrase boost
    phrases = [p.lower() for p in (args.contains or []) if p.strip()]
    if phrases:
        bonus = np.zeros_like(sims, dtype=np.float32)
        for i, txt in enumerate(contents):
            low = txt.lower()
            hits = sum(1 for p in phrases if p in low)
            if hits:
                bonus[i] = 0.06 * hits   # gentle nudge per phrase
        sims = sims + bonus

    # Rank and take topK
    order = np.argsort(-sims)
    topk = max(1, args.topk)
    idxs = order[:topk]

    # Build RAW block list
    SN = max(120, args.snippet_chars)  # guard against tiny values
    raw_blocks: List[str] = []
    for rank, i in enumerate(idxs, 1):
        snippet = _shorten(contents[i], SN)
        raw_blocks.append(
            f"{rank}. score={sims[i]:.4f}  id={chunk_ids[i]}  file={file_paths[i]}\n    {snippet}"
        )

    print("\n--- RAW CONTEXT ---")
    if raw_blocks:
        print("\n".join(raw_blocks))
    else:
        print("(no matches)")

    if args.raw_only:
        return

    # Build a second pass with slightly longer text for summary (helps capture full sentences)
    # We don’t dump the entire chunk (token safety), but give the LLM enough to answer.
    # If you want full text, just pass a very large --snippet-chars (e.g., 4000).
    long_SN = max(SN, 900)
    summary_blocks = []
    for i in idxs:
        summary_blocks.append(
            f"ChunkID={chunk_ids[i]} | File={file_paths[i]}\n{_shorten(contents[i], long_SN)}"
        )

    if args.with_summary:
        print("\n\n--- SUMMARY ---")
        try:
            answer = summarize_with_llm(args.question, summary_blocks)
            print(answer or "Not found in the provided context.")
        except Exception as e:
            print(f"(summary error) {e}")
            print("Not found in the provided context.")


if __name__ == "__main__":
    main()
