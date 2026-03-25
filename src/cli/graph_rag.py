# src/cli/graph_rag.py
import os
import json
import zlib
import base64
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set

import numpy as np

try:
    import networkx as nx
except Exception as e:
    raise RuntimeError(
        "networkx is required. Install it:\n"
        "  pip install networkx\n"
    ) from e

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = lambda *a, **k: None

from src.core.openai_utils import create_openai_client


# ------------------------------ utils ------------------------------

def env_str(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v if (v is not None and v != "") else default

def env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    try:
        return int(v) if v is not None else default
    except Exception:
        return default

def maybe_dump(obj, name: str, dump_dir: str):
    if not dump_dir:
        return
    d = Path(dump_dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def decode_matrix(matrix_field) -> np.ndarray:
    if isinstance(matrix_field, str):
        raw = base64.b64decode(matrix_field)
        try:
            raw = zlib.decompress(raw)
        except Exception:
            pass
        arr = np.frombuffer(raw, dtype=np.float32)
        if arr.size == 0:
            raise RuntimeError("Decoded matrix has zero length.")
        return arr
    elif isinstance(matrix_field, list):
        return np.array(matrix_field, dtype=np.float32)
    else:
        raise RuntimeError("Unsupported matrix format in vdb_chunks.json")

def load_vdb(workdir: str) -> Tuple[np.ndarray, List[str], Dict[str, Dict]]:
    vdb_path = Path(workdir) / "vdb_chunks.json"
    kv_path = Path(workdir) / "kv_store_text_chunks.json"

    if not vdb_path.exists():
        raise FileNotFoundError(f"Missing {vdb_path}")
    if not kv_path.exists():
        raise FileNotFoundError(f"Missing {kv_path}")

    with vdb_path.open("r", encoding="utf-8") as f:
        vdb = json.load(f)
    with kv_path.open("r", encoding="utf-8") as f:
        kv_raw = json.load(f)

    kv: Dict[str, Dict] = {}
    if isinstance(kv_raw, dict) and "data" in kv_raw:
        for row in kv_raw["data"]:
            cid = row.get("_id") or row.get("chunk_id") or row.get("id")
            if cid:
                kv[cid] = row
    elif isinstance(kv_raw, dict):
        kv = kv_raw
    elif isinstance(kv_raw, list):
        for row in kv_raw:
            cid = row.get("_id") or row.get("chunk_id") or row.get("id")
            if cid:
                kv[cid] = row
    else:
        raise RuntimeError("Unexpected schema for kv_store_text_chunks.json")

    data = vdb.get("data", [])
    chunk_ids = []
    for row in data:
        cid = row.get("__id__") or row.get("id") or row.get("_id")
        if not cid:
            cid = row.get("chunk_id")
        if cid:
            chunk_ids.append(cid)
    if len(chunk_ids) == 0:
        chunk_ids = list(kv.keys())

    matrix_field = vdb.get("matrix")
    if matrix_field is None:
        raise RuntimeError("vdb_chunks.json has no 'matrix' field.")
    embs = decode_matrix(matrix_field)

    if embs.ndim == 1:
        dim = int(vdb.get("embedding_dim", 3072))
        if embs.size % dim != 0:
            raise RuntimeError(
                f"Flat matrix length {embs.size} not divisible by dim {dim}"
            )
        n = embs.size // dim
        embs = embs.reshape(n, dim)

    if embs.shape[0] != len(chunk_ids):
        n = min(embs.shape[0], len(chunk_ids))
        embs = embs[:n]
        chunk_ids = chunk_ids[:n]

    return embs.astype(np.float32), chunk_ids, kv


def cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-8)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-8)
    return a_norm @ b_norm.T

def embed_query_openai(text: str, ensure_dim: int) -> np.ndarray:
    model = env_str("EMBED_MODEL", "text-embedding-3-large")
    client = create_openai_client()
    resp = client.embeddings.create(model=model, input=text)
    vec = np.array(resp.data[0].embedding, dtype=np.float32)
    if vec.shape[0] != ensure_dim:
        if vec.shape[0] < ensure_dim:
            pad = np.zeros((ensure_dim - vec.shape[0],), dtype=np.float32)
            vec = np.concatenate([vec, pad], axis=0)
        else:
            vec = vec[:ensure_dim]
    return vec

# ------------------------------ graph helpers ------------------------------

def load_graph(graphml_path: str):
    if not graphml_path:
        return None
    p = Path(graphml_path)
    if not p.exists():
        raise FileNotFoundError(f"GraphML not found: {graphml_path}")
    return nx.read_graphml(p)

def expand_with_graph(
    seed_chunk_ids: List[str],
    g,
    hops: int = 1,
    max_neighbors: int = 4,
) -> Set[str]:
    """
    Given seed chunk ids, walk the graph up to 'hops' steps and collect other chunk node ids.
    If chunk ids aren't present as nodes, returns empty set (won't crash).
    """
    if g is None:
        return set()
    acc: Set[str] = set()
    for cid in seed_chunk_ids:
        if cid not in g:
            continue
        frontier = {cid}
        seen = {cid}
        for _ in range(hops):
            nxt = set()
            for u in frontier:
                # neighbors limited
                nbrs = list(g.neighbors(u))[:max_neighbors]
                nxt.update(nbrs)
            frontier = {v for v in nxt if v not in seen}
            seen.update(frontier)
        # keep only nodes that look like chunk ids (heuristic)
        acc.update([n for n in seen if str(n).startswith("chunk-")])
    acc.difference_update(seed_chunk_ids)
    return acc

# ------------------------------ print / summarize ------------------------------

def print_raw(hits: List[Tuple[float, str]], kv: Dict[str, Dict]):
    max_chars = env_int("RAW_SNIPPET_CHARS", 360)
    print("\n--- RAW CONTEXT ---")
    for rank, (score, cid) in enumerate(hits, start=1):
        row = kv.get(cid, {})
        snippet = (row.get("content") or "").strip().replace("\n", " ")
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars].rstrip() + " ..."
        file_path = row.get("file_path") or row.get("full_doc_id") or "unknown"
        print(
            f" {rank}. score={score:.4f}  id={cid}  file={file_path}\n"
            f"    {snippet}\n"
        )

def summarize(question: str, hits: List[Tuple[float, str]], kv: Dict[str, Dict]) -> str:
    model = env_str("LLM_MODEL", "gpt-4o-mini")
    client = create_openai_client()

    max_ctx = 8
    ctx = []
    for (score, cid) in hits[:max_ctx]:
        row = kv.get(cid, {})
        file_path = row.get("file_path") or row.get("full_doc_id") or "unknown"
        text = (row.get("content") or "").strip()
        ctx.append(f"[{cid} | {file_path} | score={score:.3f}]\n{text}")
    ctx_text = "\n\n---\n\n".join(ctx)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a precise research assistant. Answer ONLY from the provided context. "
                "Quote short phrases as needed and cite chunk ids. If not present, say 'Not found in the provided context.'"
            ),
        },
        {"role": "user", "content": f"Question: {question}\n\nContext:\n{ctx_text}\n\nAnswer:"},
    ]
    resp = client.chat.completions.create(model=model, messages=messages, temperature=0.2)
    return resp.choices[0].message.content.strip()

# ------------------------------ main ------------------------------

def main():
    load_dotenv(override=False)

    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--question", type=str, required=True)
    parser.add_argument("-k", "--topk", type=int, default=env_int("TOP_K", 10))
    parser.add_argument("--workdir", type=str, default=env_str("WORKING_DIR", "./rag_storage"))
    parser.add_argument("--with-summary", action="store_true")
    parser.add_argument("--graphml", type=str, default=str(Path(env_str("WORKING_DIR", "./rag_storage")) / "graph_chunk_entity_relation.graphml"))
    parser.add_argument("--hops", type=int, default=1)
    parser.add_argument("--graph-max-neighbors", type=int, default=4)
    parser.add_argument("--graph-weight", type=float, default=0.3, help="0..1; blend weight for graph-boosted scores")
    parser.add_argument("--dump-dir", type=str, default=env_str("DUMP_DIR", ""), help="Directory to write optional debug dumps; empty = no files")

    args = parser.parse_args()

    t0 = time.time()
    embs, chunk_ids, kv = load_vdb(args.workdir)

    # seed retrieve
    qvec = embed_query_openai(args.question, embs.shape[1]).reshape(1, -1)
    sims = cosine_sim(embs, qvec).reshape(-1)
    idx = np.argsort(-sims)[:args.topk]
    seed_hits = [(float(sims[i]), chunk_ids[i]) for i in idx]

    # optional graph expansion
    g = None
    try:
        g = load_graph(args.graphml) if args.graphml else None
    except Exception:
        g = None  # stay robust

    extra_ids = expand_with_graph([cid for _, cid in seed_hits], g, hops=args.hops, max_neighbors=args.graph_max_neighbors)

    # blend graph neighbors with a modest boost; rank by blended score
    id2score = {cid: s for (s, cid) in seed_hits}
    for cid in extra_ids:
        # If the neighbor wasn't in top-k, give it a fraction of the min seed score
        base = min(s for s, _ in seed_hits) if seed_hits else 0.0
        id2score[cid] = max(id2score.get(cid, 0.0), base * args.graph_weight)

    final = sorted(id2score.items(), key=lambda x: -x[1])[:args.topk]
    hits = [(score, cid) for cid, score in final]

    maybe_dump(
        {
            "question": args.question,
            "graph_used": bool(g),
            "extra_neighbors": list(extra_ids),
            "hits": [{"chunk_id": cid, "score": sc} for (sc, cid) in hits],
        },
        "graph_rag_debug.json",
        args.dump_dir,
    )

    print_raw(hits, kv)

    if args.with_summary:
        print("\n--- SUMMARY ---")
        try:
            summary = summarize(args.question, hits, kv)
        except Exception as e:
            summary = f"(summary failed: {e})"
        print(summary)

    dt = time.time() - t0
    print(f"\n[done in {dt:.2f}s]")


if __name__ == "__main__":
    main()
